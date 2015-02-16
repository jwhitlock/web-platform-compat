# -*- coding: utf-8 -*-
"""API Serializers"""

from collections import OrderedDict
from itertools import chain
from json import dumps

from django.db.models import CharField
from django.conf import settings
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from drf_cached_instances.models import CachedQueryset
from rest_framework.reverse import reverse
from rest_framework.serializers import (
    DateField, DateTimeField, IntegerField, ModelSerializer,
    NestedValidationError, PrimaryKeyRelatedField, SerializerMethodField,
    ValidationError)

from tools.resources import Collection, CollectionChangeset
from . import fields
from .cache import Cache
from .drf_fields import (
    AutoUserField, CurrentHistoryField, HistoricalObjectField, HistoryField,
    MPTTRelationField, OptionalCharField, OptionalIntegerField,
    TranslatedTextField)
from .history import Changeset
from .models import (
    Browser, Feature, Maturity, Section, Specification, Support, Version)


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
        """Add read_only flag for write-restricted fields"""
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


class SectionSerializer(HistoricalModelSerializer):
    """Specification Section Serializer"""

    class Meta:
        model = Section
        fields = (
            'id', 'number', 'name', 'subpath', 'note', 'specification',
            'features', 'history_current', 'history')


class SpecificationSerializer(HistoricalModelSerializer):
    """Specification Serializer"""

    def save_object(self, obj, **kwargs):
        if 'sections' in getattr(obj, '_related_data', {}):
            sections = obj._related_data.pop('sections')
        else:
            sections = None

        super(SpecificationSerializer, self).save_object(obj, **kwargs)

        if sections:
            s_pks = [s.pk for s in sections]
            current_order = obj.get_section_order()
            if s_pks != current_order:
                obj.set_section_order(s_pks)

    class Meta:
        model = Specification
        fields = (
            'id', 'slug', 'mdn_key', 'name', 'uri', 'maturity', 'sections',
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


#
# Change control object serializers
#

class ChangesetSerializer(ModelSerializer):
    """Changeset Serializer"""

    user = AutoUserField()
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
        self.archive_cached_links_fields = getattr(
            meta, 'archive_cached_links_fields', [])


class HistoricalObjectSerializer(ModelSerializer):
    """Common serializer attributes for Historical models"""
    _options_class = HistoricalOptions

    id = IntegerField(source="history_id")
    date = DateTimeField(source="history_date")
    event = SerializerMethodField('get_event')
    changeset = PrimaryKeyRelatedField(source="history_changeset")

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

        # Archived link fields are to-one relations
        for field in self.opts.archive_link_fields:
            del data[field]
            value = getattr(obj, field + '_id')
            if value is not None:
                value = str(value)
            data['links'][field] = value

        # Archived cached links fields are a list of primary keys
        for field in self.opts.archive_cached_links_fields:
            value = getattr(obj, field)
            value = [str(x) for x in value]
            data['links'][field] = value
        data['links']['history_current'] = str(obj.history_id)

        return data

    class Meta:
        fields = ('id', 'date', 'event', 'changeset')


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
            exclude = (
                'history_current', 'history', 'sections', 'supports',
                'children')

    feature = HistoricalObjectField()
    features = SerializerMethodField('get_archive')

    class Meta(HistoricalObjectSerializer.Meta):
        model = Feature.history.model
        fields = HistoricalObjectSerializer.Meta.fields + (
            'feature', 'features')
        archive_link_fields = ('parent',)
        archive_cached_links_fields = ('sections',)


class HistoricalMaturitySerializer(HistoricalObjectSerializer):

    class ArchivedObject(MaturitySerializer):
        class Meta(MaturitySerializer.Meta):
            exclude = ('specifications', 'history_current', 'history')

    maturity = HistoricalObjectField()
    maturities = SerializerMethodField('get_archive')

    class Meta(HistoricalObjectSerializer.Meta):
        model = Maturity.history.model
        fields = HistoricalObjectSerializer.Meta.fields + (
            'maturity', 'maturities')


class HistoricalSectionSerializer(HistoricalObjectSerializer):

    class ArchivedObject(SectionSerializer):
        class Meta(SectionSerializer.Meta):
            exclude = ('features', 'history_current', 'history')

    section = HistoricalObjectField()
    sections = SerializerMethodField('get_archive')

    class Meta(HistoricalObjectSerializer.Meta):
        model = Section.history.model
        fields = HistoricalObjectSerializer.Meta.fields + (
            'section', 'sections')
        archive_link_fields = ('specification',)


class HistoricalSpecificationSerializer(HistoricalObjectSerializer):

    class ArchivedObject(SpecificationSerializer):
        class Meta(SpecificationSerializer.Meta):
            exclude = ('sections', 'history_current', 'history')

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


#
# View serializers
#

class ViewFeatureListSerializer(ModelSerializer):

    url = SerializerMethodField('get_url')

    def get_url(self, obj):
        return reverse(
            'viewfeatures-detail', kwargs={'pk': obj.id},
            request=self.context['request'])

    class Meta:
        model = Feature
        fields = (
            'url', 'id', 'slug', 'mdn_uri', 'experimental', 'standardized',
            'stable', 'obsolete', 'name')


class DjangoResourceClient(object):
    """Implement tools.client.Client using Django native functions"""
    cls_by_name = {
        'features': (Feature, FeatureSerializer),
        'supports': (Support, SupportSerializer),
        'maturities': (Maturity, MaturitySerializer),
        'specifications': (Specification, SpecificationSerializer),
        'sections': (Section, SectionSerializer),
        'browsers': (Browser, BrowserSerializer),
        'versions': (Version, VersionSerializer),
    }

    def url(self, resource_type, resource_id=None):
        if resource_type == 'maturities':
            singular = 'maturity'
        else:
            singular = resource_type[:-1]
        if resource_id:
            return reverse(
                singular + '-detail', kwargs={'pk': resource_id})
        else:
            return reverse(singular + '-list')

    def open_changeset(self):
        pass

    def close_changeset(self):
        pass

    def update(self, resource_type, resource_id, resource):
        model_cls, serializer_cls = self.cls_by_name[resource_type]
        instance = model_cls.objects.get(id=resource_id)
        data = resource.copy()
        links = data.pop('links', {})
        data.update(links)
        serializer = serializer_cls(instance=instance, data=data)
        assert serializer.is_valid()
        serializer.save()

    def create(self, resource_type, resource):
        model_cls, serializer_cls = self.cls_by_name[resource_type]
        data = resource.copy()
        links = data.pop('links', {})
        data.update(links)
        serializer = serializer_cls(data=data)
        assert serializer.is_valid()
        obj = serializer.save()
        return {'id': obj.id}

    def delete(self, resource_type, resource_id):
        raise NotImplementedError("delete not implemented for safety")


class FeatureExtra(object):
    """Handle new and updated data in a view_feature update"""
    # Map resource collection names to Model and Serializer classes
    cls_by_name = {
        'features': (Feature, FeatureSerializer),
        'supports': (Support, SupportSerializer),
        'maturities': (Maturity, MaturitySerializer),
        'specifications': (Specification, SpecificationSerializer),
        'sections': (Section, SectionSerializer),
        'browsers': (Browser, BrowserSerializer),
        'versions': (Version, VersionSerializer),
    }

    def __init__(self, all_data, feature, context):
        self.all_data = all_data
        self.feature = feature
        self.context = context

    def is_valid(self):
        """Validate the linked data"""
        self.errors = {}
        self._process_data()
        self._validate_changes()
        return not self.errors

    def load_resource(self, resource_cls, data):
        """Load a resource, stringifying IDs"""
        rdata = {}
        wlinks = getattr(resource_cls, '_writeable_link_fields', {})
        rlinks = getattr(resource_cls, '_readonly_link_fields', {})
        link_names = set(['id'] + list(wlinks.keys()) + list(rlinks.keys()))
        for key, value in data.items():
            if key in link_names:
                if isinstance(value, list):
                    raw_ids = value
                    unlist = False
                else:
                    raw_ids = [value]
                    unlist = True
                ids = [str(i) for i in raw_ids]
                if unlist:
                    rdata[key] = ids[0]
                else:
                    rdata[key] = ids
            else:
                rdata[key] = value
        return resource_cls(**rdata)

    def _process_data(self):
        """Load the linked data and compare to current data."""
        assert not hasattr(self, 'changes')
        assert hasattr(self, 'errors')
        r_by_t = Collection.resource_by_type

        # Create and load collection of new data
        new_collection = Collection()
        new_extra = self.all_data['_view_extra']
        for rtype, items in new_extra.items():
            resource_cls = r_by_t.get(rtype)
            if resource_cls:
                for seq, json_api_item in enumerate(items):
                    item = json_api_item.copy()
                    links = item.pop('links', {})
                    item.update(links)
                    resource = self.load_resource(resource_cls, item)
                    resource._seq = seq
                    new_collection.add(resource)

        # Create native representation of current feature data
        current_collection = Collection(DjangoResourceClient())
        feature_serializer = ViewFeatureSerializer(context=self.context)
        current_feature = feature_serializer.to_native(self.feature)
        current_extra = current_feature.pop('_view_extra')
        del current_extra['meta']

        # Load feature into new and current collection
        current_feature_resource = self.load_resource(
            r_by_t['features'], current_feature)
        current_collection.add(current_feature_resource)
        current_feature.update(self.feature._in_extra)
        current_feature['id'] = str(current_feature['id'])
        resource_feature = self.load_resource(
            r_by_t['features'], current_feature)
        resource_feature._seq = None
        new_collection.add(resource_feature)

        # Populate collection of current data
        for rtype, items in current_extra.items():
            resource_cls = r_by_t.get(rtype)
            assert resource
            for item in items:
                resource = self.load_resource(resource_cls, item)
                current_collection.add(resource)

        # Add existing items not explicit in PUT content
        # This avoids 'delete' changes
        new_items = new_collection.get_all_by_data_id()
        for data_id, item in current_collection.get_all_by_data_id().items():
            if data_id not in new_items:
                resource = r_by_t[item._resource_type]()
                resource.from_json_api(item.to_json_api())
                resource._seq = None
                new_collection.add(resource)

        # Add existing items used in new collection to current collection
        # This avoids incorrect 'new' changes
        existing_items = current_collection.get_all_by_data_id()
        for data_id, item in new_collection.get_all_by_data_id().items():
            if item.id:
                item_id = item.id.id
                int_id = None
                existing_item = existing_items.get(data_id)
                try:
                    int_id = int(item_id)
                except ValueError:
                    pass
                if int_id and (existing_item is None):
                    rtype = item._resource_type
                    resource_cls = r_by_t[rtype]
                    model_cls, serializer_cls = self.cls_by_name[rtype]
                    obj = model_cls.objects.get(id=int_id)
                    serializer = serializer_cls()
                    data = serializer.to_native(obj)
                    resource = self.load_resource(resource_cls, data)
                    current_collection.add(resource)

        # Load the diff
        self.changeset = CollectionChangeset(
            current_collection, new_collection)
        assert not self.changeset.changes.get('deleted')

    def add_error(self, resource_type, seq, error_dict):
        """Add a validation error for a linked resource."""
        self.errors.setdefault(
            resource_type, {}).setdefault(seq, {}).update(error_dict)

    def _validate_changes(self):
        """Validate the changes.

        Validation includes:
        - Field validation of properties
        - Disallow adding features outside of the target feature's subtree
        - Disallow additions of maturities

        Validation of links is not attempted, since most validation errors
        will be relations to new resources.  This may miss links to
        "existing" resources that aren't in the database, but those will
        be DoesNotExist exceptions in _process_data.
        """
        assert hasattr(self, 'changeset')
        assert hasattr(self, 'errors')
        assert not self.errors

        new_collection = self.changeset.new_collection
        resource_feature = new_collection.get('features', str(self.feature.id))

        # Validate with DRF serializers
        for data_id, item in new_collection.get_all_by_data_id().items():
            rtype = item._resource_type
            model_cls, serializer_cls = self.cls_by_name[rtype]
            seq = getattr(item, '_seq')
            if seq is None:
                continue

            # Does the ID imply an existing instance?
            int_id = None
            instance = None
            assert item.id
            item_id = item.id.id
            try:
                int_id = int(item_id)
            except ValueError:
                pass
            else:
                instance = model_cls.objects.get(id=int_id)

            # Validate the data with DRF serializer
            data = item.to_json_api()[rtype]
            links = data.pop('links', {})
            data.update(links)
            serializer = serializer_cls(instance=instance, data=data)
            if not serializer.is_valid():
                errors = {}
                # Discard errors in link fields, for now
                for fieldname, error in serializer.errors.items():
                    if fieldname not in links:
                        errors[fieldname] = error
                if errors:
                    self.add_error(rtype, seq, errors)

        # Validate that features are in the feature tree
        target_id = resource_feature.id.id
        for feature in new_collection.get_resources('features'):
            if feature.id.id == target_id:
                continue

            f = feature
            while (f and f.parent is not None and
                    f.parent.id != target_id):
                f = new_collection.get('features', f.parent.id)

            if f is None or f.parent.id is None:
                error = (
                    "Feature must be a descendant of feature %s." % target_id)
                self.add_error('features', feature._seq, {'parent': error})

        # Validate that "expert" objects are not added
        expert_resources = set((
            'maturities', 'specifications', 'versions', 'browsers'))
        add_error = (
            'Resource can not be created as part of this update. Create'
            ' first, and try again.')
        for item in self.changeset.changes['new'].values():
            if item._resource_type in expert_resources:
                self.add_error(
                    item._resource_type, item._seq, {'id': add_error})

        # Validate that "expert" objects are not changed
        omit_err = 'Field was omitted, but should be set to %s'
        change_err = (
            'Field can not be changed from %s to %s as part of this update.'
            ' Update the resource by itself, and try again.')
        for item in self.changeset.changes['changed'].values():
            if item._resource_type in expert_resources:
                rtype = item._resource_type
                new_json = dict(item.to_json_api()[rtype])
                new_json.update(new_json.pop('links', {}))
                orig_json = dict(item._original.to_json_api()[rtype])
                orig_json.update(orig_json.pop('links', {}))
                for key, value in orig_json.items():
                    if key not in new_json:
                        err = omit_err % dumps(value)
                        self.add_error(rtype, item._seq, {key: err})
                    elif value != new_json[key]:
                        err = change_err % (dumps(value), dumps(new_json[key]))
                        self.add_error(rtype, item._seq, {key: err})

    def save(self, **kwargs):
        """Commit changes to linked data"""
        self.changeset.change_original_collection()


class ViewFeatureExtraSerializer(ModelSerializer):
    """Linked resources and metadata for ViewFeatureSerializer."""

    class ViewBrowserSerializer(BrowserSerializer):
        class Meta(BrowserSerializer.Meta):
            fields = [
                x for x in BrowserSerializer.Meta.fields if x != 'versions']

    class ViewMaturitySerializer(MaturitySerializer):
        class Meta(MaturitySerializer.Meta):
            fields = [
                x for x in MaturitySerializer.Meta.fields
                if x != 'specifications']

    class ViewSectionSerializer(SectionSerializer):
        class Meta(SectionSerializer.Meta):
            fields = [
                x for x in SectionSerializer.Meta.fields if x != 'features']

    class ViewSpecificationSerializer(SpecificationSerializer):
        class Meta(SpecificationSerializer.Meta):
            fields = [
                x for x in SpecificationSerializer.Meta.fields
                if x != 'sections']

    class ViewVersionSerializer(VersionSerializer):
        class Meta(VersionSerializer.Meta):
            fields = [
                x for x in VersionSerializer.Meta.fields if x != 'supports']
            read_only_fields = [
                x for x in VersionSerializer.Meta.read_only_fields
                if x != 'supports']

    browsers = ViewBrowserSerializer(source='all_browsers', many=True)
    features = FeatureSerializer(source='child_features', many=True)
    maturities = ViewMaturitySerializer(source='all_maturities', many=True)
    sections = ViewSectionSerializer(source='all_sections', many=True)
    specifications = ViewSpecificationSerializer(source='all_specs', many=True)
    supports = SupportSerializer(source='all_supports', many=True)
    versions = ViewVersionSerializer(source='all_versions', many=True)
    meta = SerializerMethodField('get_meta')

    def add_sources(self, obj):
        """Add the sources used by the serializer fields."""
        page = self.context['request'].GET.get('page', 1)
        per_page = settings.PAGINATE_VIEW_FEATURE
        if isinstance(obj, Feature):
            # It's a real Feature, not a cached proxy Feature
            obj.descendant_count = obj.get_descendant_count()
            descendant_pks = obj.get_descendants().values_list('pk', flat=True)
        elif obj.descendant_count <= per_page:
            # The cached PK list is enough to populate descendant_pks
            descendant_pks = obj.descendants.values_list('id', flat=True)
        else:
            # Load the real object to get the full list of descendants
            real_obj = Feature.objects.get(id=obj.id)
            descendant_pks = real_obj.get_descendants().values_list(
                'pk', flat=True)
        descendants = CachedQueryset(
            Cache(), Feature.objects.all(), descendant_pks)
        obj.paginated_child_features = Paginator(descendants, per_page)
        obj.page_child_features = obj.paginated_child_features.page(page)
        obj.child_features = obj.page_child_features.object_list

        # Load the remaining related instances
        section_pks = set(obj.sections.values_list('id', flat=True))
        support_pks = set(obj.supports.values_list('id', flat=True))
        for feature in obj.child_features:
            section_pks.update(feature.sections.values_list('id', flat=True))
            support_pks.update(feature.supports.values_list('id', flat=True))

        obj.all_sections = list(CachedQueryset(
            Cache(), Section.objects.all(), sorted(section_pks)))
        obj.all_supports = list(CachedQueryset(
            Cache(), Support.objects.all(), sorted(support_pks)))

        specification_pks = set()
        for section in obj.all_sections:
            specification_pks.add(section.specification.pk)
        obj.all_specs = list(CachedQueryset(
            Cache(), Specification.objects.all(), sorted(specification_pks)))

        maturity_pks = set()
        for specification in obj.all_specs:
            maturity_pks.add(specification.maturity.pk)
        obj.all_maturities = list(CachedQueryset(
            Cache(), Maturity.objects.all(), sorted(maturity_pks)))

        version_pks = set()
        for support in obj.all_supports:
            version_pks.add(support.version.pk)
        obj.all_versions = list(CachedQueryset(
            Cache(), Version.objects.all(), sorted(version_pks)))

        browser_pks = set()
        for version in obj.all_versions:
            browser_pks.add(version.browser.pk)
        obj.all_browsers = list(CachedQueryset(
            Cache(), Browser.objects.all(), sorted(browser_pks)))

    def to_native(self, obj):
        """Add addditonal data for the ViewFeatureSerializer.

        For most features, all the related data is cachable, and no database
        reads are required with a warm cache.

        For some features, such as the root node for CSS, the subtree is huge,
        and the descendant feature PKs won't fit in the cache.  In these
        cases, a couple of database reads are required to get the
        descendant feature PKs, which are then paginated to reduce the huge
        amount of related data.
        """
        # Load the paginated descendant features
        if obj is None:
            # This happens when OPTIONS is called from browsable API
            return None
        self.add_sources(obj)
        ret = super(ViewFeatureExtraSerializer, self).to_native(obj)
        return ret

    def find_languages(self, obj):
        """Find languages used in feature view."""
        languages = set()

        def add_langs(item):
            if hasattr(item, 'keys'):  # pragma: nocover
                languages.update(item.keys())

        for browser in obj.all_browsers:
            add_langs(browser.name)
            add_langs(browser.note)

        for feature in chain([obj], obj.child_features):
            add_langs(feature.mdn_uri)
            add_langs(feature.name)

        for maturity in obj.all_maturities:
            add_langs(maturity.name)

        for section in obj.all_sections:
            add_langs(section.number)
            add_langs(section.name)
            add_langs(section.subpath)
            add_langs(section.note)

        for spec in obj.all_specs:
            add_langs(spec.name)
            add_langs(spec.uri)

        for support in obj.all_supports:
            add_langs(support.note)
            add_langs(support.footnote)

        for version in obj.all_versions:
            add_langs(version.release_notes_uri)
            add_langs(version.note)

        if 'zxx' in languages:
            # No linguistic content
            languages.remove('zxx')
        if 'en' in languages:
            languages.remove('en')
            return ['en'] + sorted(languages)
        else:
            return sorted(languages)

    def significant_changes(self, obj):
        """Determine what versions are important for support changes.

        A version is important if it is the first version with support
        information, or it changes support from the previous version.
        """
        # Create lookup of ID/PK -> instances
        browsers = {}
        for browser in obj.all_browsers:
            # Cache version order
            browser.version_ids = browser.versions.values_list('id', flat=True)
            browsers[browser.id] = browser
        versions = dict(
            [(version.id, version) for version in obj.all_versions])
        features = dict(
            [(feature.id, feature) for feature in obj.child_features])
        features[obj.id] = obj

        # Create index of supported browser / version / features
        supported = []
        for support in obj.all_supports:
            version = versions[support.version.pk]
            browser = browsers[version.browser.pk]
            version_order = browser.version_ids.index(version.id)
            feature = features[support.feature.pk]
            support_attrs = (
                support.support,
                support.prefix,
                support.prefix_mandatory,
                support.alternate_name,
                support.alternate_mandatory,
                support.requires_config,
                support.default_config,
                support.protected,
                repr(support.note),
                repr(support.footnote),
            )
            supported.append((
                feature.id, browser.id, version_order, version.id,
                support.id, support_attrs))
        supported.sort()

        # Identify significant browser / version / supports by feature
        sig_features = {}
        last_f_id = None
        last_b_id = None
        last_support = None
        for f_id, b_id, _, v_id, s_id, support in supported:
            if last_f_id != f_id:
                last_support = None
                last_f_id = f_id
            if last_b_id != b_id:
                last_support = None
                last_b_id = b_id

            if last_support != support:
                sig_feature = sig_features.setdefault(f_id, {})
                sig_browser = sig_feature.setdefault(str(b_id), [])
                sig_browser.append(str(s_id))
                last_support = support

        # Order significant features
        significant_changes = OrderedDict()
        for f_id in chain([obj.id], [f.id for f in obj.child_features]):
            significant_changes[str(f_id)] = sig_features.get(f_id, {})

        return significant_changes

    def browser_tabs(self, obj):
        """Section and order the browser tabs.

        TODO: Move this logic into the database, API
        """
        known_browsers = dict((
            ('chrome', ('Desktop Browsers', 1)),
            ('firefox', ('Desktop Browsers', 2)),
            ('internet_explorer', ('Desktop Browsers', 3)),
            ('opera', ('Desktop Browsers', 4)),
            ('safari', ('Desktop Browsers', 5)),
            ('android', ('Mobile Browsers', 6)),
            ('chrome_for_android', ('Mobile Browsers', 7)),
            ('chrome_mobile', ('Mobile Browsers', 8)),
            ('firefox_mobile', ('Mobile Browsers', 9)),
            ('ie_mobile', ('Mobile Browsers', 10)),
            ('opera_mini', ('Mobile Browsers', 11)),
            ('opera_mobile', ('Mobile Browsers', 12)),
            ('safari_mobile', ('Mobile Browsers', 13)),
            ('blackberry', ('Mobile Browsers', 14)),
            ('firefox_os', ('Non-Browser Environments', 15)),
        ))
        next_other = 16
        sections = [
            'Desktop Browsers', 'Mobile Browsers', 'Non-Browser Environments']
        raw_tabs = dict((section, []) for section in sections)

        for browser in obj.all_browsers:
            try:
                section, order = known_browsers[browser.slug]
            except KeyError:
                section, order = ('Non-Browser Environments', next_other)
                next_other += 1
            raw_tabs[section].append((order, browser.id))

        tabs = []
        for section in sections:
            browsers = raw_tabs[section]
            if browsers:
                browsers.sort()
                tabs.append(OrderedDict((
                    ('name', {'en': section}),
                    ('browsers', [str(pk) for _, pk in browsers]),
                )))
        return tabs

    def pagination(self, obj):
        """Determine pagination for large feature trees."""
        pagination = {
            'previous': None,
            'next': None,
            'count': obj.descendant_count
        }
        url_kwargs = {'pk': obj.id}
        if self.context['format']:
            url_kwargs['format'] = self.context['format']
        request = self.context['request']
        url = reverse(
            'viewfeatures-detail', kwargs=url_kwargs, request=request)
        if obj.page_child_features.has_previous():
            pagination['previous'] = (
                url + '?page=' +
                str(obj.page_child_features.previous_page_number()))
        if obj.page_child_features.has_next():
            pagination['next'] = (
                url + '?page=' +
                str(obj.page_child_features.next_page_number()))
        return {'linked.features': pagination}

    def ordered_footnotes(self, obj, sig_features, tabs):
        """Gather footnotes from significant features."""
        supports = dict(
            [(str(support.id), support) for support in obj.all_supports])
        footnotes = []
        for browsers in sig_features.values():
            for section in tabs:
                for browser in section['browsers']:
                    sig_supports = browsers.get(browser, [])
                    for sig_support_pk in sig_supports:
                        support = supports[sig_support_pk]
                        if support.footnote:
                            footnotes.append(sig_support_pk)
        return OrderedDict((note, i) for i, note in enumerate(footnotes, 1))

    def get_meta(self, obj):
        """Assemble the metadata for the feature view."""
        significant_changes = self.significant_changes(obj)
        browser_tabs = self.browser_tabs(obj)
        pagination = self.pagination(obj)
        languages = self.find_languages(obj)
        footnotes = self.ordered_footnotes(
            obj, significant_changes, browser_tabs)
        meta = OrderedDict((
            ('compat_table', OrderedDict((
                ('supports', significant_changes),
                ('tabs', browser_tabs),
                ('pagination', pagination),
                ('languages', languages),
                ('footnotes', footnotes),
            ))),))
        return meta

    def field_from_native(self, data, files, field_name, reverted_data):
        """Deserialize objects in the "linked" field of JSON API

        This acts a bit like a nested Serializer, but because JSON-API doesn't
        use nested representions, we have to do some gymnastics to fit in
        Django REST Framework.

        Return will be a FeatureExtra instance that will update the
        database with new and updated linked data when .save() is called.

        Some validation errors can be detected at this point, which will raise
        a NestedValidationError.  Other objects won't be validated until
        related objects are saved, which may cause validation errors.
        """
        linked = data.get(field_name, {})
        if linked:
            # Add existing related data to target Feature
            self.object = self.parent.object
            assert self.object
            self.add_sources(self.object)
            self.object._in_extra = self.parent._in_extra

            # Validate the linked data
            extra = FeatureExtra(data, self.object, self.context)
            if extra.is_valid():
                # Parent serializer will call extra.save()
                reverted_data[field_name] = extra
            else:
                assert extra.errors
                raise NestedValidationError(extra.errors)

    class Meta:
        model = Feature
        fields = (
            'browsers', 'versions', 'supports', 'maturities',
            'specifications', 'sections', 'features', 'meta')


class ViewFeatureSerializer(FeatureSerializer):
    """Feature Serializer, plus related data and MDN browser compat logic"""

    _view_extra = ViewFeatureExtraSerializer(source='*')

    class Meta(FeatureSerializer.Meta):
        fields = FeatureSerializer.Meta.fields + ('_view_extra',)

    def restore_object(self, attrs, instance=None):
        """Restore feature, and convert _view_extra"""
        obj = super(ViewFeatureSerializer, self).restore_object(
            attrs, instance)
        return obj

    def restore_fields(self, data, files):
        self._in_extra = {
            'sections': data.pop('sections', []),
            'supports': data.pop('supports', []),
            'children': data.pop('children', []),
        }
        return super(ViewFeatureSerializer, self).restore_fields(data, files)

    def save(self, *args, **kwargs):
        """Save the feature plus linked elements.

        The save is done using DRF conventions; the _view_extra field is set
        to an object (FeatureExtra) that will same linked elements.  The only
        wrinkle is that the changeset should not be auto-closed by any saved
        items.
        """
        changeset = self.context['request'].changeset
        if changeset.id:
            # Already in an open changeset - client will close
            close_changeset = False
        else:
            close_changeset = True
            assert not changeset.user_id
            changeset.user = self.context['request'].user
            changeset.save()

        ret = super(ViewFeatureSerializer, self).save(*args, **kwargs)

        if close_changeset:
            changeset.closed = True
            changeset.save()
        return ret
