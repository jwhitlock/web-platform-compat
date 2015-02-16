# -*- coding: utf-8 -*-

from django.contrib.auth.models import User
from rest_framework.mixins import UpdateModelMixin
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.renderers import BrowsableAPIRenderer
from rest_framework.viewsets import ModelViewSet as BaseModelViewSet
from rest_framework.viewsets import ReadOnlyModelViewSet as BaseROModelViewSet

from drf_cached_instances.mixins import CachedViewMixin as BaseCacheViewMixin

from .cache import Cache
from .history import Changeset
from .mixins import PartialPutMixin
from .models import (
    Browser, Feature, Maturity, Section, Specification, Support, Version)
from .parsers import JsonApiParser
from .renderers import JsonApiRenderer, JsonApiTemplateHTMLRenderer
from .serializers import (
    BrowserSerializer, FeatureSerializer, MaturitySerializer,
    SectionSerializer, SpecificationSerializer, SupportSerializer,
    VersionSerializer,
    ChangesetSerializer, UserSerializer,
    HistoricalBrowserSerializer, HistoricalFeatureSerializer,
    HistoricalMaturitySerializer, HistoricalSectionSerializer,
    HistoricalSpecificationSerializer, HistoricalSupportSerializer,
    HistoricalVersionSerializer,
    ViewFeatureListSerializer, ViewFeatureSerializer)


#
# Base classes
#

class CachedViewMixin(BaseCacheViewMixin):
    cache_class = Cache


class ModelViewSet(PartialPutMixin, CachedViewMixin, BaseModelViewSet):
    renderer_classes = (JsonApiRenderer, BrowsableAPIRenderer)
    parser_classes = (JsonApiParser, FormParser, MultiPartParser)

    def pre_save(self, obj):
        """Delay cache refresh if requested by changeset middleware"""
        if getattr(self.request, 'delay_cache', False):
            obj._delay_cache = True


class ReadOnlyModelViewSet(BaseROModelViewSet):
    renderer_classes = (JsonApiRenderer, BrowsableAPIRenderer)


#
# 'Regular' viewsets
#

class BrowserViewSet(ModelViewSet):
    model = Browser
    queryset = Browser.objects.order_by('id')
    serializer_class = BrowserSerializer
    filter_fields = ('slug',)


class FeatureViewSet(ModelViewSet):
    model = Feature
    serializer_class = FeatureSerializer
    filter_fields = ('slug', 'parent')

    def filter_queryset(self, queryset):
        qs = super(FeatureViewSet, self).filter_queryset(queryset)
        if 'parent' in self.request.QUERY_PARAMS:
            filter_value = self.request.QUERY_PARAMS['parent']
            if not filter_value:
                qs = qs.filter(parent=None)
        return qs


class MaturityViewSet(ModelViewSet):
    model = Maturity
    serializer_class = MaturitySerializer
    filter_fields = ('slug',)


class SectionViewSet(ModelViewSet):
    model = Section
    serializer_class = SectionSerializer


class SpecificationViewSet(ModelViewSet):
    model = Specification
    queryset = Specification.objects.order_by('id')
    serializer_class = SpecificationSerializer
    filter_fields = ('slug', 'mdn_key')


class SupportViewSet(ModelViewSet):
    model = Support
    serializer_class = SupportSerializer
    filter_fields = ('version', 'feature')


class VersionViewSet(ModelViewSet):
    queryset = Version.objects.order_by('id')
    model = Version
    serializer_class = VersionSerializer
    filter_fields = ('browser', 'browser__slug', 'version', 'status')


#
# Change control viewsets
#

class ChangesetViewSet(ModelViewSet):
    model = Changeset
    serializer_class = ChangesetSerializer


class UserViewSet(ModelViewSet):
    model = User
    serializer_class = UserSerializer
    filter_fields = ('username',)


#
# Historical object viewsets
#

class HistoricalBrowserViewSet(ReadOnlyModelViewSet):
    model = Browser.history.model
    serializer_class = HistoricalBrowserSerializer
    filter_fields = ('id', 'slug')


class HistoricalFeatureViewSet(ReadOnlyModelViewSet):
    model = Feature.history.model
    serializer_class = HistoricalFeatureSerializer
    filter_fields = ('id', 'slug')


class HistoricalMaturityViewSet(ReadOnlyModelViewSet):
    model = Maturity.history.model
    serializer_class = HistoricalMaturitySerializer
    filter_fields = ('id', 'slug')


class HistoricalSectionViewSet(ReadOnlyModelViewSet):
    model = Section.history.model
    serializer_class = HistoricalSectionSerializer
    filter_fields = ('id',)


class HistoricalSpecificationViewSet(ReadOnlyModelViewSet):
    model = Specification.history.model
    serializer_class = HistoricalSpecificationSerializer
    filter_fields = ('id', 'slug', 'mdn_key')


class HistoricalSupportViewSet(ReadOnlyModelViewSet):
    model = Support.history.model
    serializer_class = HistoricalSupportSerializer
    filter_fields = ('id',)


class HistoricalVersionViewSet(ReadOnlyModelViewSet):
    model = Version.history.model
    serializer_class = HistoricalVersionSerializer
    filter_fields = ('id',)


#
# Views
#

class ViewFeaturesViewSet(
        PartialPutMixin, CachedViewMixin, UpdateModelMixin,
        ReadOnlyModelViewSet):
    model = Feature
    serializer_class = ViewFeatureSerializer
    filter_fields = ('slug',)
    parser_classes = (JsonApiParser, FormParser, MultiPartParser)
    renderer_classes = (
        JsonApiRenderer, BrowsableAPIRenderer, JsonApiTemplateHTMLRenderer)
    template_name = 'webplatformcompat/feature.basic.jinja2'

    def get_serializer_class(self):
        """Return the list serializer when needed."""
        if self.action == 'list':
            return ViewFeatureListSerializer
        else:
            return super(ViewFeaturesViewSet, self).get_serializer_class()
