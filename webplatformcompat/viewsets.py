# -*- coding: utf-8 -*-

from django.contrib.auth.models import User
from django.http import Http404
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
    HistoricalVersionSerializer)
from .view_serializers import (
    ViewFeatureListSerializer, ViewFeatureSerializer)


#
# Base classes
#

class CachedViewMixin(BaseCacheViewMixin):
    cache_class = Cache

    def perform_create(self, serializer):
        kwargs = {}
        if getattr(self.request, 'delay_cache', False):
            kwargs['_delay_cache'] = True
        serializer.save(**kwargs)

    def perform_update(self, serializer):
        kwargs = {}
        if getattr(self.request, 'delay_cache', False):
            kwargs['_delay_cache'] = True
        serializer.save(**kwargs)

    def perform_destroy(self, instance):
        if getattr(self.request, 'delay_cache', False):
            instance._delay_cache = True
        instance.delete()


class ModelViewSet(PartialPutMixin, CachedViewMixin, BaseModelViewSet):
    renderer_classes = (JsonApiRenderer, BrowsableAPIRenderer)
    parser_classes = (JsonApiParser, FormParser, MultiPartParser)


class ReadOnlyModelViewSet(BaseROModelViewSet):
    renderer_classes = (JsonApiRenderer, BrowsableAPIRenderer)


class UpdateOnlyModelViewSet(
        PartialPutMixin, CachedViewMixin, UpdateModelMixin,
        ReadOnlyModelViewSet):
    renderer_classes = (JsonApiRenderer, BrowsableAPIRenderer)
    parser_classes = (JsonApiParser, FormParser, MultiPartParser)


#
# 'Regular' viewsets
#

class BrowserViewSet(ModelViewSet):
    queryset = Browser.objects.order_by('id')
    serializer_class = BrowserSerializer
    filter_fields = ('slug',)


class FeatureViewSet(ModelViewSet):
    queryset = Feature.objects.order_by('id')
    serializer_class = FeatureSerializer
    filter_fields = ('slug', 'parent')

    def filter_queryset(self, queryset):
        qs = super(FeatureViewSet, self).filter_queryset(queryset)
        if 'parent' in self.request.query_params:
            filter_value = self.request.query_params['parent']
            if not filter_value:
                qs = qs.filter(parent=None)
        return qs


class MaturityViewSet(ModelViewSet):
    queryset = Maturity.objects.order_by('id')
    serializer_class = MaturitySerializer
    filter_fields = ('slug',)


class SectionViewSet(ModelViewSet):
    queryset = Section.objects.order_by('id')
    serializer_class = SectionSerializer


class SpecificationViewSet(ModelViewSet):
    queryset = Specification.objects.order_by('id')
    serializer_class = SpecificationSerializer
    filter_fields = ('slug', 'mdn_key')


class SupportViewSet(ModelViewSet):
    queryset = Support.objects.order_by('id')
    serializer_class = SupportSerializer
    filter_fields = ('version', 'feature')


class VersionViewSet(ModelViewSet):
    queryset = Version.objects.order_by('id')
    serializer_class = VersionSerializer
    filter_fields = ('browser', 'browser__slug', 'version', 'status')


#
# Change control viewsets
#

class ChangesetViewSet(ModelViewSet):
    queryset = Changeset.objects.order_by('id')
    serializer_class = ChangesetSerializer


class UserViewSet(CachedViewMixin, ReadOnlyModelViewSet):
    queryset = User.objects.order_by('id')
    serializer_class = UserSerializer
    filter_fields = ('username',)


#
# Historical object viewsets
#

class HistoricalBrowserViewSet(ReadOnlyModelViewSet):
    queryset = Browser.history.model.objects.order_by('id')
    serializer_class = HistoricalBrowserSerializer
    filter_fields = ('id', 'slug')


class HistoricalFeatureViewSet(ReadOnlyModelViewSet):
    queryset = Feature.history.model.objects.order_by('id')
    serializer_class = HistoricalFeatureSerializer
    filter_fields = ('id', 'slug')


class HistoricalMaturityViewSet(ReadOnlyModelViewSet):
    queryset = Maturity.history.model.objects.order_by('id')
    serializer_class = HistoricalMaturitySerializer
    filter_fields = ('id', 'slug')


class HistoricalSectionViewSet(ReadOnlyModelViewSet):
    queryset = Section.history.model.objects.order_by('id')
    serializer_class = HistoricalSectionSerializer
    filter_fields = ('id',)


class HistoricalSpecificationViewSet(ReadOnlyModelViewSet):
    queryset = Specification.history.model.objects.order_by('id')
    serializer_class = HistoricalSpecificationSerializer
    filter_fields = ('id', 'slug', 'mdn_key')


class HistoricalSupportViewSet(ReadOnlyModelViewSet):
    queryset = Support.history.model.objects.order_by('id')
    serializer_class = HistoricalSupportSerializer
    filter_fields = ('id',)


class HistoricalVersionViewSet(ReadOnlyModelViewSet):
    queryset = Version.history.model.objects.order_by('id')
    serializer_class = HistoricalVersionSerializer
    filter_fields = ('id',)


#
# Views
#

class ViewFeaturesViewSet(UpdateOnlyModelViewSet):
    queryset = Feature.objects.order_by('id')
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

    def get_object_or_404(self, queryset, *filter_args, **filter_kwargs):
        """The feature can be accessed by primary key or by feature slug."""
        pk_or_slug = filter_kwargs['pk']
        try:
            pk = int(pk_or_slug)
        except ValueError:
            try:
                pk = Feature.objects.only('pk').get(slug=pk_or_slug).pk
            except queryset.model.DoesNotExist:
                raise Http404(
                    'No %s matches the given query.' % queryset.model)
        return super(ViewFeaturesViewSet, self).get_object_or_404(
            queryset, pk=pk)
