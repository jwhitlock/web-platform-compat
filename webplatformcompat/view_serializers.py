# -*- coding: utf-8 -*-
"""API Serializers"""

from collections import OrderedDict
from itertools import chain
from json import dumps

from django.conf import settings
from django.core.paginator import Paginator
from drf_cached_instances.models import CachedQueryset
from rest_framework.reverse import reverse
from rest_framework.serializers import (
    ModelSerializer, PrimaryKeyRelatedField, SerializerMethodField,
    ValidationError)
from rest_framework.utils.serializer_helpers import ReturnDict

from tools.resources import Collection, CollectionChangeset
from .cache import Cache
from .models import (
    Browser, Feature, Maturity, Section, Specification, Support, Version)
from .serializers import (
    BrowserSerializer, FieldMapMixin, FeatureSerializer, MaturitySerializer,
    SectionSerializer, SpecificationSerializer, SupportSerializer,
    VersionSerializer, omit_some)


class ViewBrowserSerializer(BrowserSerializer):
    class Meta(BrowserSerializer.Meta):
        fields = omit_some(BrowserSerializer.Meta.fields, 'versions')


class ViewMaturitySerializer(MaturitySerializer):
    class Meta(MaturitySerializer.Meta):
        fields = omit_some(MaturitySerializer.Meta.fields, 'specifications')


class ViewSectionSerializer(SectionSerializer):
    class Meta(SectionSerializer.Meta):
        fields = omit_some(SectionSerializer.Meta.fields, 'features')


class ViewSpecificationSerializer(SpecificationSerializer):
    class Meta(SpecificationSerializer.Meta):
        fields = omit_some(SpecificationSerializer.Meta.fields, 'sections')


class ViewVersionSerializer(VersionSerializer):
    class Meta(VersionSerializer.Meta):
        fields = omit_some(VersionSerializer.Meta.fields, 'supports')
        read_only_fields = omit_some(
            VersionSerializer.Meta.read_only_fields, 'supports')


# Map resource names to model, view serializer classes
view_cls_by_name = {
    'features': (Feature, FeatureSerializer),
    'supports': (Support, SupportSerializer),
    'maturities': (Maturity, ViewMaturitySerializer),
    'specifications': (Specification, ViewSpecificationSerializer),
    'sections': (Section, ViewSectionSerializer),
    'browsers': (Browser, ViewBrowserSerializer),
    'versions': (Version, ViewVersionSerializer),
}


class ViewFeatureListSerializer(FieldMapMixin, ModelSerializer):
    """Get list of features"""
    url = SerializerMethodField()

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
    namespace = 'v1'

    def url(self, resource_type, resource_id=None):
        """Use Django reverse to determine URL."""
        if resource_type == 'maturities':
            singular = 'maturity'
        else:
            singular = resource_type[:-1]
        if resource_id:
            return reverse(
                self.namespace + ':' + singular + '-detail',
                kwargs={'pk': resource_id})
        else:
            return reverse(self.namespace + ':' + singular + '-list')

    def open_changeset(self):
        """Skip opening changesets (opened at the request/view level)."""
        pass

    def close_changeset(self):
        """Skip closing changesets (closed at the request/view level)."""
        pass

    def update(self, resource_type, resource_id, resource):
        model_cls, serializer_cls = view_cls_by_name[resource_type]
        instance = model_cls.objects.get(id=resource_id)
        data = resource.copy()
        links = data.pop('links', {})
        data.update(links)
        serializer = serializer_cls(instance=instance, data=data)
        assert serializer.is_valid(), serializer.errors
        serializer.save()

    def create(self, resource_type, resource):
        model_cls, serializer_cls = view_cls_by_name[resource_type]
        data = resource.copy()
        links = data.pop('links', {})
        data.update(links)
        serializer = serializer_cls(data=data)
        assert serializer.is_valid(), serializer.errors
        obj = serializer.save()
        return {'id': obj.id}

    def delete(self, resource_type, resource_id):
        raise NotImplementedError("delete not implemented for safety")


class FeatureExtra(object):
    """Handle new and updated data in a view_feature update"""
    def __init__(self, data, feature, context):
        self.data = data
        self.feature = feature
        self.context = context

    def is_valid(self):
        """Validate the linked data"""
        self.errors = {}
        self._process_data()
        self._validate_changes()
        return not self.errors

    def load_resource(self, resource_cls, data):
        """Load a resource, converting data to look like wire data

        Conversions:
        - Stringify IDs (5 -> "5")
        - Convert Date to ISO 8601 (2015-02-17)
        """
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
                ids = []
                for i in raw_ids:
                    if i is None:
                        ids.append(None)
                    else:
                        ids.append(str(i))
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
        for rtype, items in self.data.items():
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
        current_feature = feature_serializer.to_representation(self.feature)
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
            resource_cls = r_by_t[rtype]
            for item in items:
                resource = self.load_resource(resource_cls, item)
                current_collection.add(resource)

        # Add existing items not explicit in PUT content
        # This avoids 'delete' changes
        new_items = new_collection.get_all_by_data_id()
        for data_id, item in current_collection.get_all_by_data_id().items():
            if data_id not in new_items:
                rtype = item._resource_type
                resource = r_by_t[rtype]()
                json_api_rep = item.to_json_api()
                json_api_rep[rtype]["id"] = item.id.id
                resource.from_json_api(json_api_rep)
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
                    model_cls, serializer_cls = view_cls_by_name[rtype]
                    obj = model_cls.objects.get(id=int_id)
                    serializer = serializer_cls()
                    data = serializer.to_representation(obj)
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
            model_cls, serializer_cls = view_cls_by_name[rtype]
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
                    if value != new_json.get(key, "(missing)"):
                        err = change_err % (dumps(value), dumps(new_json[key]))
                        self.add_error(rtype, item._seq, {key: err})

    def save(self, **kwargs):
        """Commit changes to linked data"""
        self.changeset.change_original_collection()

        # Adding sub-features will change the MPTT tree through direct SQL.
        # Load the new tree data from the database before parent serializer
        # overwrites it with old values.
        tree_attrs = ['lft', 'rght', 'tree_id', 'level', 'parent']
        db_feature = Feature.objects.only(*tree_attrs).get(id=self.feature.id)
        for attr in tree_attrs:
            setattr(self.feature, attr, getattr(db_feature, attr))


class ViewFeatureExtraSerializer(ModelSerializer):
    """Linked resources and metadata for ViewFeatureSerializer."""
    browsers = ViewBrowserSerializer(source='all_browsers', many=True)
    features = FeatureSerializer(source='child_features', many=True)
    maturities = ViewMaturitySerializer(source='all_maturities', many=True)
    sections = ViewSectionSerializer(source='all_sections', many=True)
    specifications = ViewSpecificationSerializer(source='all_specs', many=True)
    supports = SupportSerializer(source='all_supports', many=True)
    versions = ViewVersionSerializer(source='all_versions', many=True)
    meta = SerializerMethodField()

    def add_sources(self, obj):
        """Add the sources used by the serializer fields."""
        page = self.context['request'].GET.get('page', 1)
        per_page = settings.PAGINATE_VIEW_FEATURE
        if self.context['include_child_pages']:
            # Paginate the full descendant tree
            child_queryset = self.get_all_descendants(obj, per_page)
            paginated_child_features = Paginator(child_queryset, per_page)
            obj.page_child_features = paginated_child_features.page(page)
            obj.child_features = obj.page_child_features.object_list
        else:
            # Jut the row-level descendants, but un-paginated
            child_queryset = self.get_row_descendants(obj)
            obj.child_features = list(child_queryset.all())

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

    def get_all_descendants(self, obj, per_page):
        """Return a CachedQueryset of all the descendants

        This includes row features that model rows in the MDN table,
        and page features that model sub-pages on MDN, which may have
        row and subpage features of their own.
        """
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
        return CachedQueryset(
            Cache(), Feature.objects.all(), descendant_pks)

    def get_row_descendants(self, obj):
        """Return a CachedQueryset of just the row descendants

        This includes row features, and subfeatures of rows that are also
        row features.

        See http://bit.ly/1MUSEFL for one example of spliting a large table
        into a hierarchy of features.
        """
        row_descendant_pks = obj.row_descendants.values_list('id', flat=True)
        return CachedQueryset(
            Cache(), Feature.objects.all(), row_descendant_pks)

    def to_representation(self, obj):
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
        ret = super(ViewFeatureExtraSerializer, self).to_representation(obj)
        return ReturnDict(ret, serializer=self)

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
                sig_feature = sig_features.setdefault(f_id, OrderedDict())
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
            ('chrome_desktop', ('Desktop Browsers', 1)),
            ('edge', ('Desktop Browsers', 2)),
            ('firefox_desktop', ('Desktop Browsers', 3)),
            ('ie_desktop', ('Desktop Browsers', 4)),
            ('opera_desktop', ('Desktop Browsers', 5)),
            ('safari_desktop', ('Desktop Browsers', 6)),
            ('android', ('Mobile Browsers', 10)),
            ('android_webview', ('Mobile Browsers', 11)),
            ('blackberry', ('Mobile Browsers', 12)),
            ('chrome_for_android', ('Mobile Browsers', 13)),
            ('firefox_android', ('Mobile Browsers', 14)),
            ('ie_mobile', ('Mobile Browsers', 15)),
            ('opera_mini', ('Mobile Browsers', 16)),
            ('opera_mobile', ('Mobile Browsers', 17)),
            ('safari_ios', ('Mobile Browsers', 18)),
            ('firefox_os', ('Non-Browser Environments', 20)),
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
        """
        Determine pagination for large feature trees.

        If page children are not included (the default), then no pagination is
        used, but the pagination object remains to make client logic easier.
        """
        pagination = OrderedDict((
            ('previous', None),
            ('next', None),
        ))
        if self.context['include_child_pages']:
            # When full descendant list, use pagination
            # The list can get huge when asking for root features like web-css
            pagination['count'] = obj.descendant_count
            url_kwargs = {'pk': obj.id}
            if self.context['format']:
                url_kwargs['format'] = self.context['format']
            request = self.context['request']
            url = reverse(
                'viewfeatures-detail', kwargs=url_kwargs, request=request)
            if obj.page_child_features.has_previous():
                page = obj.page_child_features.previous_page_number()
                pagination['previous'] = (
                    "%s?child_pages=1&page=%s" % (url, page))
            if obj.page_child_features.has_next():
                page = obj.page_child_features.next_page_number()
                pagination['next'] = (
                    "%s?child_pages=1&page=%s" % (url, page))
        else:
            # Don't paginate results. The client probabaly wants to generate a
            # complete table, so pagination would get in the way.
            pagination['count'] = len(obj.child_features)
        return {'linked.features': pagination}

    def ordered_notes(self, obj, sig_features, tabs):
        """Gather notes from significant features."""
        supports = dict(
            [(str(support.id), support) for support in obj.all_supports])
        notes = []
        for browsers in sig_features.values():
            for section in tabs:
                for browser in section['browsers']:
                    sig_supports = browsers.get(browser, [])
                    for sig_support_pk in sig_supports:
                        support = supports[sig_support_pk]
                        if support.note:
                            notes.append(sig_support_pk)
        return OrderedDict((note, i) for i, note in enumerate(notes, 1))

    def get_meta(self, obj):
        """Assemble the metadata for the feature view."""
        significant_changes = self.significant_changes(obj)
        browser_tabs = self.browser_tabs(obj)
        include_child_pages = self.context['include_child_pages']
        pagination = self.pagination(obj)
        languages = self.find_languages(obj)
        notes = self.ordered_notes(
            obj, significant_changes, browser_tabs)
        meta = OrderedDict((
            ('compat_table', OrderedDict((
                ('supports', significant_changes),
                ('tabs', browser_tabs),
                ('child_pages', include_child_pages),
                ('pagination', pagination),
                ('languages', languages),
                ('notes', notes),
            ))),))
        return meta

    def to_internal_value(self, data):
        self.instance = self.parent.instance
        assert self.instance
        self.add_sources(self.instance)
        self.instance._in_extra = self.parent._in_extra

        extra = FeatureExtra(data, self.instance, self.context)
        if extra.is_valid():
            return {'_view_extra': extra}
        else:
            assert extra.errors
            raise ValidationError(extra.errors)

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

    def to_internal_value(self, data):
        self._in_extra = {}
        if '_view_extra' in data:
            for link_name in ('sections', 'supports', 'children'):
                if link_name in data:
                    self._in_extra[link_name] = data.pop(link_name)
        return super(ViewFeatureSerializer, self).to_internal_value(data)

    def save(self, *args, **kwargs):
        """Save the feature plus linked elements.

        The save is done using DRF conventions; the _view_extra field is set
        to an object (FeatureExtra) that will same linked elements.
        """
        ret = super(ViewFeatureSerializer, self).save(*args, **kwargs)
        if hasattr(ret, '_view_extra'):
            ret._view_extra.save(*args, **kwargs)
        return ret


class ViewFeatureRowChildrenSerializer(ViewFeatureSerializer):
    """Adjust serializer when page children are omitted."""
    children = PrimaryKeyRelatedField(
        many=True, queryset=Feature.objects.all(), source='row_children')
