# -*- coding: utf-8 -*-
"""API Serializers"""
from collections import OrderedDict

from django.db.models import CharField
from django.contrib.auth.models import User
from rest_framework.serializers import (
    CurrentUserDefault, DateTimeField, IntegerField,
    ModelSerializer, SerializerMethodField, ValidationError)
from sortedm2m.fields import SortedManyToManyField

from . import fields
from .drf_fields import (
    CurrentHistoryField, HistoricalObjectField, HistoryField,
    MPTTRelationField, OptionalCharField, OptionalIntegerField,
    PrimaryKeyRelatedField, TranslatedTextField)
from .history import Changeset
from .models import (
    Browser, Feature, Maturity, Section, Specification, Support, Version)
from .validators import VersionAndStatusValidator


def omit_some(source_list, *omitted):
    """Return a list with some items omitted"""
    for item in omitted:
        assert item in source_list, '%r not in %r' % (item, source_list)
    return [x for x in source_list if x not in omitted]


#
# "Regular" Serializers
#
class WriteRestrictedMixin(object):

    def get_fields(self):
        """Add read_only flag for write-restricted fields"""
        fields = super(WriteRestrictedMixin, self).get_fields()
        view = self.context.get('view', None)

        if view and view.action in ('list', 'create'):
            update_only_fields = getattr(self.Meta, 'update_only_fields', [])
            for field_name in update_only_fields:
                fields[field_name].read_only = True

        if view and view.action in ('update', 'partial_update'):
            write_once_fields = getattr(self.Meta, 'write_once_fields', [])
            for field_name in write_once_fields:
                fields[field_name].read_only = True

        return fields


class FieldMapMixin(object):
    """Automatically handle fields used by this project"""
    serializer_field_mapping = ModelSerializer.serializer_field_mapping
    serializer_field_mapping[fields.TranslatedField] = TranslatedTextField
    serializer_field_mapping[CharField] = OptionalCharField
    serializer_field_mapping[SortedManyToManyField] = PrimaryKeyRelatedField
    serializer_related_field = PrimaryKeyRelatedField

    def build_standard_field(self, field_name, model_field):
        field_class, field_kwargs = super(
            FieldMapMixin, self).build_standard_field(
                field_name, model_field)
        if isinstance(model_field, fields.TranslatedField):
            if not (model_field.blank or model_field.null):
                field_kwargs['required'] = True
            if model_field.allow_canonical:
                field_kwargs['allow_canonical'] = True
        return field_class, field_kwargs


class HistoricalModelSerializer(
        WriteRestrictedMixin, FieldMapMixin, ModelSerializer):
    """Model serializer with history manager"""

    def build_property_field(self, field_name, model_class):
        """Handle history field.

        The history field is a list of PKs for all the history records.
        """
        assert field_name == 'history'
        field_kwargs = {'many': True, 'read_only': True}
        return HistoryField, field_kwargs

    def build_unknown_field(self, field_name, model_class):
        """Handle history_current field.

        history_current returns the PK of the most recent history record.
        It is treated as read-only unless it is an update view.
        """
        assert field_name == 'history_current'
        view = self.context.get('view', None)
        read_only = view and view.action in ('list', 'create')
        field_args = {'read_only': read_only}
        return CurrentHistoryField, field_args

    def to_internal_value(self, data):
        """If history_current in data, load historical data into instance"""
        if data and 'history_current' in data:
            history_id = int(data['history_current'])
            current_history = self.instance.history.all()[0]
            if current_history.history_id != history_id:
                try:
                    historical = self.instance.history.get(
                        history_id=history_id).instance
                except self.instance.history.model.DoesNotExist:
                    err = 'Invalid history ID for this object'
                    raise ValidationError({'history_current': [err]})
                else:
                    for field in historical._meta.fields:
                        attname = field.attname
                        hist_value = getattr(historical, attname)
                        data[attname] = hist_value
        return super(HistoricalModelSerializer, self).to_internal_value(data)


class BrowserSerializer(HistoricalModelSerializer):
    """Browser Serializer"""

    def update(self, instance, validated_data):
        versions = validated_data.pop('versions', None)
        instance = super(BrowserSerializer, self).update(
            instance, validated_data)

        if versions:
            v_pks = [v.pk for v in versions]
            current_order = instance.get_version_order()
            if v_pks != current_order:
                instance.set_version_order(v_pks)
        return instance

    class Meta:
        model = Browser
        fields = (
            'id', 'slug', 'name', 'note', 'history', 'history_current',
            'versions')
        update_only_fields = (
            'history', 'history_current', 'versions')
        write_once_fields = ('slug',)


class FeatureSerializer(HistoricalModelSerializer):
    """Feature Serializer"""

    children = MPTTRelationField(many=True, read_only=True)

    class Meta:
        model = Feature
        fields = (
            'id', 'slug', 'mdn_uri', 'experimental', 'standardized',
            'stable', 'obsolete', 'name',
            'sections', 'supports', 'parent', 'children',
            'history_current', 'history')
        read_only_fields = ('supports',)


class MaturitySerializer(HistoricalModelSerializer):
    """Specification Maturity Serializer"""

    class Meta:
        model = Maturity
        fields = (
            'id', 'slug', 'name', 'specifications',
            'history_current', 'history')
        read_only_fields = ('specifications',)


class SectionSerializer(HistoricalModelSerializer):
    """Specification Section Serializer"""

    class Meta:
        model = Section
        fields = (
            'id', 'number', 'name', 'subpath', 'note', 'specification',
            'features', 'history_current', 'history')
        extra_kwargs = {
            'features': {
                'default': []
            }
        }


class SpecificationSerializer(HistoricalModelSerializer):
    """Specification Serializer"""

    def update(self, instance, validated_data):
        sections = validated_data.pop('sections', None)
        instance = super(SpecificationSerializer, self).update(
            instance, validated_data)

        if sections:
            s_pks = [s.pk for s in sections]
            current_order = instance.get_section_order()
            if s_pks != current_order:
                instance.set_section_order(s_pks)

        return instance

    class Meta:
        model = Specification
        fields = (
            'id', 'slug', 'mdn_key', 'name', 'uri', 'maturity', 'sections',
            'history_current', 'history')
        extra_kwargs = {
            'sections': {
                'default': []
            }
        }


class SupportSerializer(HistoricalModelSerializer):
    """Support Serializer"""

    class Meta:
        model = Support
        fields = (
            'id', 'version', 'feature', 'support', 'prefix',
            'prefix_mandatory', 'alternate_name', 'alternate_mandatory',
            'requires_config', 'default_config', 'protected', 'note',
            'history_current', 'history')


class VersionSerializer(HistoricalModelSerializer):
    """Browser Version Serializer"""

    order = IntegerField(read_only=True, source='_order')

    class Meta:
        model = Version
        fields = (
            'id', 'browser', 'version', 'release_day', 'retirement_day',
            'status', 'release_notes_uri', 'note', 'order',
            'supports', 'history', 'history_current')
        extra_kwargs = {
            'version': {
                'allow_blank': False
            }
        }
        read_only_fields = ('supports',)
        write_once_fields = ('version',)
        validators = [VersionAndStatusValidator()]


#
# Change control object serializers
#

class ChangesetSerializer(ModelSerializer):
    """Changeset Serializer"""

    target_resource_type = OptionalCharField(required=False)
    target_resource_id = OptionalIntegerField(required=False)

    class Meta:
        model = Changeset
        fields = (
            'id', 'created', 'modified', 'closed', 'target_resource_type',
            'target_resource_id', 'user',
            'historical_browsers', 'historical_features',
            'historical_maturities', 'historical_sections',
            'historical_specifications', 'historical_supports',
            'historical_versions')
        update_only_fields = (
            'user', 'target_resource_type', 'target_resource_id')
        read_only_fields = (
            'id', 'created', 'modified',
            'historical_browsers', 'historical_features',
            'historical_maturities', 'historical_sections',
            'historical_specifications', 'historical_supports',
            'historical_versions')
        extra_kwargs = {
            'user': {
                'default': CurrentUserDefault()
            }
        }


class UserSerializer(ModelSerializer):
    """User Serializer"""

    created = DateTimeField(source='date_joined', read_only=True)
    agreement = SerializerMethodField()
    permissions = SerializerMethodField()

    def get_agreement(self, obj):
        """What version of the contribution terms did the user agree to?

        Placeholder for when we have a license agreement.
        """
        return 0

    def get_permissions(self, obj):
        """Return names of django.contrib.auth Groups

        Can not be used with a writable view, since django.contrib.auth User
        doesn't have this method.  Will need updating or a proxy class.
        """
        assert hasattr(obj, 'group_names'), "Expecting cached User object"
        return obj.group_names

    class Meta:
        model = User
        fields = (
            'id', 'username', 'created', 'agreement', 'permissions',
            'changesets')
        read_only_fields = ('username', 'changesets')


#
# Historical object serializers
#


class ArchiveMixin(object):
    def get_fields(self):
        """Historical models don't quite follow Django model conventions."""
        fields = super(ArchiveMixin, self).get_fields()

        # Archived link fields are to-one relations
        for link_field in getattr(self.Meta, 'archive_link_fields', []):
            field = fields[link_field]
            field.source = (field.source or link_field) + '_id'

        return fields


class HistoricalObjectSerializer(ModelSerializer):
    """Common serializer attributes for Historical models"""

    id = IntegerField(source="history_id")
    date = DateTimeField(source="history_date")
    event = SerializerMethodField()
    changeset = PrimaryKeyRelatedField(
        source="history_changeset", read_only=True)

    EVENT_CHOICES = {
        '+': 'created',
        '~': 'changed',
        '-': 'deleted',
    }

    def get_event(self, obj):
        return self.EVENT_CHOICES[obj.history_type]

    def get_archive(self, obj):
        serializer = self.ArchivedObject(obj)
        data = serializer.data
        data['id'] = str(data['id'])
        data['links'] = OrderedDict()

        # Archived link fields are to-one relations
        for field in getattr(serializer.Meta, 'archive_link_fields', []):
            del data[field]
            value = getattr(obj, field + '_id')
            if value is not None:
                value = str(value)
            data['links'][field] = value

        # Archived cached links fields are a list of primary keys
        for field in getattr(
                serializer.Meta, 'archive_cached_links_fields', []):
            value = getattr(obj, field)
            value = [str(x) for x in value]
            data['links'][field] = value
        data['links']['history_current'] = str(obj.history_id)

        return data

    class Meta:
        fields = ('id', 'date', 'event', 'changeset')


class HistoricalBrowserSerializer(HistoricalObjectSerializer):

    class ArchivedObject(ArchiveMixin, BrowserSerializer):
        class Meta(BrowserSerializer.Meta):
            fields = omit_some(
                BrowserSerializer.Meta.fields,
                'history_current', 'history', 'versions')

    browser = HistoricalObjectField()
    browsers = SerializerMethodField('get_archive')

    class Meta(HistoricalObjectSerializer.Meta):
        model = Browser.history.model
        fields = HistoricalObjectSerializer.Meta.fields + (
            'browser', 'browsers')


class HistoricalFeatureSerializer(HistoricalObjectSerializer):

    class ArchivedObject(ArchiveMixin, FeatureSerializer):
        class Meta(FeatureSerializer.Meta):
            fields = omit_some(
                FeatureSerializer.Meta.fields,
                'history_current', 'history', 'sections', 'supports',
                'children')
            read_only_fields = omit_some(
                FeatureSerializer.Meta.read_only_fields, 'supports')
            archive_link_fields = ('parent',)
            archive_cached_links_fields = ('sections',)

    feature = HistoricalObjectField()
    features = SerializerMethodField('get_archive')

    class Meta(HistoricalObjectSerializer.Meta):
        model = Feature.history.model
        fields = HistoricalObjectSerializer.Meta.fields + (
            'feature', 'features')


class HistoricalMaturitySerializer(HistoricalObjectSerializer):

    class ArchivedObject(ArchiveMixin, MaturitySerializer):
        class Meta(MaturitySerializer.Meta):
            fields = omit_some(
                MaturitySerializer.Meta.fields,
                'specifications', 'history_current', 'history')

    maturity = HistoricalObjectField()
    maturities = SerializerMethodField('get_archive')

    class Meta(HistoricalObjectSerializer.Meta):
        model = Maturity.history.model
        fields = HistoricalObjectSerializer.Meta.fields + (
            'maturity', 'maturities')


class HistoricalSectionSerializer(HistoricalObjectSerializer):

    class ArchivedObject(ArchiveMixin, SectionSerializer):
        class Meta(SectionSerializer.Meta):
            fields = omit_some(
                SectionSerializer.Meta.fields,
                'features', 'history_current', 'history')
            archive_link_fields = ('specification',)

    section = HistoricalObjectField()
    sections = SerializerMethodField('get_archive')

    class Meta(HistoricalObjectSerializer.Meta):
        model = Section.history.model
        fields = HistoricalObjectSerializer.Meta.fields + (
            'section', 'sections')


class HistoricalSpecificationSerializer(HistoricalObjectSerializer):

    class ArchivedObject(ArchiveMixin, SpecificationSerializer):
        class Meta(SpecificationSerializer.Meta):
            fields = omit_some(
                SpecificationSerializer.Meta.fields,
                'sections', 'history_current', 'history')
            archive_link_fields = ('maturity',)

    specification = HistoricalObjectField()
    specifications = SerializerMethodField('get_archive')

    class Meta(HistoricalObjectSerializer.Meta):
        model = Specification.history.model
        fields = HistoricalObjectSerializer.Meta.fields + (
            'specification', 'specifications')


class HistoricalSupportSerializer(HistoricalObjectSerializer):

    class ArchivedObject(ArchiveMixin, SupportSerializer):
        class Meta(SupportSerializer.Meta):
            fields = omit_some(
                SupportSerializer.Meta.fields, 'history_current', 'history')
            archive_link_fields = ('version', 'feature')

    support = HistoricalObjectField()
    supports = SerializerMethodField('get_archive')

    class Meta(HistoricalObjectSerializer.Meta):
        model = Support.history.model
        fields = HistoricalObjectSerializer.Meta.fields + (
            'support', 'supports')


class HistoricalVersionSerializer(HistoricalObjectSerializer):

    class ArchivedObject(ArchiveMixin, VersionSerializer):
        class Meta(VersionSerializer.Meta):
            fields = omit_some(
                VersionSerializer.Meta.fields,
                'supports', 'history_current', 'history')
            read_only_fields = omit_some(
                VersionSerializer.Meta.read_only_fields, 'supports')
            archive_link_fields = ('browser',)

    version = HistoricalObjectField()
    versions = SerializerMethodField('get_archive')

    class Meta(HistoricalObjectSerializer.Meta):
        model = Version.history.model
        fields = HistoricalObjectSerializer.Meta.fields + (
            'version', 'versions')
