# -*- coding: utf-8 -*-
"""
API Serializers
"""

from django.db.models import CharField
from django.contrib.auth.models import User
from rest_framework.serializers import (
    DateField, DateTimeField, IntegerField, ModelSerializer,
    PrimaryKeyRelatedField, SerializerMethodField, ValidationError)

from . import fields
from .drf_fields import (
    CurrentHistoryField, HistoricalObjectField, HistoryField,
    MPTTRelationField, OptionalCharField, TranslatedTextField)
from .models import Browser, Feature, Maturity, Specification, Support, Version


#
# "Regular" Serializers
#

class WriteRestrictedOptions(ModelSerializer._options_class):
    def __init__(self, meta):
        super(WriteRestrictedOptions, self).__init__(meta)
        self.update_only_fields = getattr(meta, 'update_only_fields', ())
        self.write_once_fields = getattr(meta, 'write_once_fields', ())


class WriteRestrictedMixin(object):
    _options_class = WriteRestrictedOptions

    def get_fields(self):
        '''Add read_only flag for write-restricted fields'''
        fields = super(WriteRestrictedMixin, self).get_fields()
        view = self.context.get('view', None)

        if view and view.action in ('list', 'create'):
            update_only_fields = getattr(self.opts, 'update_only_fields', [])
            for field_name in update_only_fields:
                fields[field_name].read_only = True

        if view and view.action in ('update', 'partial_update'):
            write_once_fields = getattr(self.opts, 'write_once_fields', [])
            for field_name in write_once_fields:
                fields[field_name].read_only = True

        return fields


class FieldMapMixin(object):
    """Automatically handle fields used by this project"""
    field_mapping = ModelSerializer.field_mapping
    field_mapping[fields.TranslatedField] = TranslatedTextField
    field_mapping[CharField] = OptionalCharField

    def get_field(self, model_field):
        field = super(FieldMapMixin, self).get_field(model_field)
        if isinstance(field, TranslatedTextField):
            field.allow_canonical = model_field.allow_canonical
        return field


class HistoricalModelSerializer(
        WriteRestrictedMixin, FieldMapMixin, ModelSerializer):
    """Model serializer with history manager"""

    def get_default_fields(self):
        """Add history and history_current to default fields"""
        fields = super(HistoricalModelSerializer, self).get_default_fields()

        cls = self.opts.model
        view_name = "historical%s-detail" % cls.__name__.lower()

        assert 'history' in self.opts.fields
        assert 'history' not in fields
        fields['history'] = HistoryField(view_name=view_name)

        assert 'history_current' in self.opts.fields
        assert 'history_current' not in fields
        view = self.context.get('view', None)
        read_only = view and view.action in ('list', 'create')
        fields['history_current'] = CurrentHistoryField(
            view_name=view_name, read_only=read_only)

        return fields

    def from_native(self, data, files=None):
        """If history_current in data, load historical data into instance"""
        if data and 'history_current' in data:
            history_id = int(data['history_current'])
            current_history = self.object.history.all()[0]
            if current_history.history_id != history_id:
                try:
                    historical = self.object.history.get(
                        history_id=history_id).instance
                except self.object.history.model.DoesNotExist:
                    pass
                else:
                    for field in historical._meta.fields:
                        attname = field.attname
                        hist_value = getattr(historical, attname)
                        setattr(self.object, attname, hist_value)
        return super(HistoricalModelSerializer, self).from_native(data, files)

    def validate_history_current(self, attrs, source):
        value = attrs.get(source)
        if value and self.object:
            if value.history_object.pk != self.object.id:
                raise ValidationError(
                    'history is for a different object')
        return attrs


class BrowserSerializer(HistoricalModelSerializer):
    """Browser Serializer"""

    def save_object(self, obj, **kwargs):
        if 'versions' in getattr(obj, '_related_data', {}):
            versions = obj._related_data.pop('versions')
        else:
            versions = None

        super(BrowserSerializer, self).save_object(obj, **kwargs)

        if versions:
            v_pks = [v.pk for v in versions]
            current_order = obj.get_version_order()
            if v_pks != current_order:
                obj.set_version_order(v_pks)

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

    children = MPTTRelationField(many=True, source='children')

    class Meta:
        model = Feature
        fields = (
            'id', 'slug', 'mdn_path', 'experimental', 'standardized',
            'stable', 'obsolete', 'name',
            'parent', 'children', 'supports', 'history_current', 'history')
        read_only_fields = ('supports',)


class MaturitySerializer(HistoricalModelSerializer):
    """Specification Maturity Serializer"""

    class Meta:
        model = Maturity
        fields = (
            'id', 'key', 'name', 'history_current', 'history')


class SpecificationSerializer(HistoricalModelSerializer):
    """Specification Serializer"""

    class Meta:
        model = Specification
        fields = (
            'id', 'key', 'name', 'uri', 'maturity',
            'history_current', 'history')


class SupportSerializer(HistoricalModelSerializer):
    """Support Serializer"""

    class Meta:
        model = Support
        fields = (
            'id', 'version', 'feature', 'support', 'prefix',
            'prefix_mandatory', 'alternate_name', 'alternate_mandatory',
            'requires_config', 'default_config', 'protected', 'note',
            'footnote', 'history_current', 'history')


class VersionSerializer(HistoricalModelSerializer):
    """Browser Version Serializer"""

    order = IntegerField(read_only=True, source='_order')

    class Meta:
        model = Version
        fields = (
            'id', 'browser', 'version', 'release_day', 'retirement_day',
            'status', 'release_notes_uri', 'note', 'order',
            'supports', 'history', 'history_current')
        read_only_fields = ('supports',)


class UserSerializer(ModelSerializer):
    """User Serializer"""

    created = DateField(source='date_joined', read_only=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'created')


#
# Historical object serializers
#
class HistoricalOptions(ModelSerializer._options_class):
    def __init__(self, meta):
        super(HistoricalOptions, self).__init__(meta)
        self.archive_link_fields = getattr(meta, 'archive_link_fields', [])


class HistoricalObjectSerializer(ModelSerializer):
    '''Common serializer attributes for Historical models'''
    _options_class = HistoricalOptions

    id = IntegerField(source="history_id")
    date = DateTimeField(source="history_date")
    event = SerializerMethodField('get_event')
    user = PrimaryKeyRelatedField(source="history_user")

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

        data['links'] = type(data)()  # Use dict-like type of serializer.data
        for field in self.opts.archive_link_fields:
            del data[field]
            value = getattr(obj, field + '_id')
            if value is not None:
                value = str(value)
            data['links'][field] = value
        data['links']['history_current'] = str(obj.history_id)

        return data

    class Meta:
        fields = ('id', 'date', 'event', 'user')


class HistoricalBrowserSerializer(HistoricalObjectSerializer):

    class ArchivedObject(BrowserSerializer):
        class Meta(BrowserSerializer.Meta):
            exclude = ('history_current', 'history', 'versions')

    browser = HistoricalObjectField()
    browsers = SerializerMethodField('get_archive')

    class Meta(HistoricalObjectSerializer.Meta):
        model = Browser.history.model
        fields = HistoricalObjectSerializer.Meta.fields + (
            'browser', 'browsers')


class HistoricalFeatureSerializer(HistoricalObjectSerializer):

    class ArchivedObject(FeatureSerializer):
        class Meta(FeatureSerializer.Meta):
            exclude = ('history_current', 'history', 'supports', 'children')

    feature = HistoricalObjectField()
    features = SerializerMethodField('get_archive')

    class Meta(HistoricalObjectSerializer.Meta):
        model = Feature.history.model
        fields = HistoricalObjectSerializer.Meta.fields + (
            'feature', 'features')
        archive_link_fields = ('parent',)


class HistoricalMaturitySerializer(HistoricalObjectSerializer):

    class ArchivedObject(MaturitySerializer):
        class Meta(MaturitySerializer.Meta):
            exclude = ('history_current', 'history')

    maturity = HistoricalObjectField()
    maturities = SerializerMethodField('get_archive')

    class Meta(HistoricalObjectSerializer.Meta):
        model = Maturity.history.model
        fields = HistoricalObjectSerializer.Meta.fields + (
            'maturity', 'maturities')


class HistoricalSpecificationSerializer(HistoricalObjectSerializer):

    class ArchivedObject(SpecificationSerializer):
        class Meta(SpecificationSerializer.Meta):
            exclude = ('history_current', 'history')

    specification = HistoricalObjectField()
    specifications = SerializerMethodField('get_archive')

    class Meta(HistoricalObjectSerializer.Meta):
        model = Specification.history.model
        fields = HistoricalObjectSerializer.Meta.fields + (
            'specification', 'specifications')
        archive_link_fields = ('maturity',)


class HistoricalSupportSerializer(HistoricalObjectSerializer):

    class ArchivedObject(SupportSerializer):
        class Meta(SupportSerializer.Meta):
            exclude = ('history_current', 'history')

    support = HistoricalObjectField()
    supports = SerializerMethodField('get_archive')

    class Meta(HistoricalObjectSerializer.Meta):
        model = Support.history.model
        fields = HistoricalObjectSerializer.Meta.fields + (
            'support', 'supports')
        archive_link_fields = ('version', 'feature')


class HistoricalVersionSerializer(HistoricalObjectSerializer):

    class ArchivedObject(VersionSerializer):
        class Meta(VersionSerializer.Meta):
            exclude = ('supports', 'history_current', 'history')

    version = HistoricalObjectField()
    versions = SerializerMethodField('get_archive')

    class Meta(HistoricalObjectSerializer.Meta):
        model = Version.history.model
        fields = HistoricalObjectSerializer.Meta.fields + (
            'version', 'versions')
        archive_link_fields = ('browser',)
