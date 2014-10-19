# -*- coding: utf-8 -*-

try:  # pragma: no cover
    from collections import OrderedDict
except ImportError:  # pragma: no cover
    # py26 doesn't have OrderedDict
    OrderedDict = dict
assert OrderedDict

from django.contrib.auth.models import User
from rest_framework.renderers import BrowsableAPIRenderer
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.viewsets import ModelViewSet as BaseModelViewSet
from rest_framework.viewsets import ReadOnlyModelViewSet as BaseROModelViewSet
from rest_framework.viewsets import ViewSet

from drf_cached_reads.mixins import CachedViewMixin as BaseCacheViewMixin

from .cache import Cache
from .mixins import PartialPutMixin
from .models import Browser, Feature, Maturity, Specification, Support, Version
from .parsers import JsonApiParser
from .renderers import JsonApiRenderer
from .serializers import (
    BrowserSerializer, FeatureSerializer, MaturitySerializer,
    SpecificationSerializer, SupportSerializer, VersionSerializer,
    HistoricalBrowserSerializer, HistoricalFeatureSerializer,
    HistoricalMaturitySerializer, HistoricalSpecificationSerializer,
    HistoricalSupportSerializer, HistoricalVersionSerializer,
    UserSerializer)


#
# Base classes
#

class CachedViewMixin(BaseCacheViewMixin):
    cache_class = Cache


class ModelViewSet(PartialPutMixin, CachedViewMixin, BaseModelViewSet):
    renderer_classes = (JsonApiRenderer, BrowsableAPIRenderer)
    parser_classes = (JsonApiParser, FormParser, MultiPartParser)


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
    filter_fields = ('key',)


class SpecificationViewSet(ModelViewSet):
    model = Specification
    serializer_class = SpecificationSerializer
    filter_fields = ('key',)


class SupportViewSet(ModelViewSet):
    model = Support
    serializer_class = SupportSerializer
    filter_fields = ('version', 'feature')


class VersionViewSet(ModelViewSet):
    model = Version
    serializer_class = VersionSerializer
    filter_fields = ('browser', 'browser__slug', 'version', 'status')


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
    filter_fields = ('id', 'key')


class HistoricalSpecificationViewSet(ReadOnlyModelViewSet):
    model = Specification.history.model
    serializer_class = HistoricalSpecificationSerializer
    filter_fields = ('id', 'key')


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

class ViewFeaturesViewSet(ViewSet):
    '''Return a view for FeatureSets

    TODO: Return real data
    '''
    renderer_classes = (JsonApiRenderer, BrowsableAPIRenderer)
    permission_classes = (AllowAny,)

    def get_renderer_context(self):
        context = super(ViewFeaturesViewSet, self).get_renderer_context()
        context['jsonapi'] = {'direct': True}
        return context

    def list(self, request, *args, **kwargs):
        url = reverse(
            'viewfeatures-detail', request=request,
            kwargs={'pk': 'html-element-address'})
        feature_sets = {
            'view-features': OrderedDict((
                ('html-element-address', url),
            ))
        }
        return Response(feature_sets)

    def retrieve(self, request, *args, **kwargs):
        a = "https://browsersupports.org/api/v1"
        feature_set = OrderedDict((
            ("features", OrderedDict((
                ("id", "816"),
                ("mdn_path", "en-US/docs/Web/HTML/Element/address"),
                ("slug", "html-element-address"),
                ("experimental", False),
                ("standardized", True),
                ("stable", True),
                ("obsolete", False),
                ("name", "address"),
                ("links", OrderedDict((
                    ("sections", ["746", "421", "70"]),
                    ("supports", []),
                    ("parent", "800"),
                    ("children", ["191"]),
                    ("history_current", "216"),
                    ("history", ["216"])))),
            ))),
            ("linked", OrderedDict((
                ("features", [
                    OrderedDict((
                        ("id", "191"),
                        ("slug", "html-address"),
                        ("experimental", False),
                        ("standardized", True),
                        ("stable", True),
                        ("obsolete", False),
                        ("name", {"en": "Basic support"}),
                        ("links", OrderedDict((
                            ("sections", []),
                            ("supports", [
                                "358", "359", "360", "361", "362", "363",
                                "364", "365", "366", "367", "368"]),
                            ("parent", "816"),
                            ("children", []),
                            ("history_current", "395"),
                            ("history", ["395"]),
                        ))),
                    )),
                ]),
                ("sections", [
                    OrderedDict((
                        ("id", "746"),
                        ("name", {"en": "The address element"}),
                        ("subpath",
                         {"en": "sections.html#the-address-element"}),
                        ("notes", None),
                        ("links", OrderedDict((
                            ("specification", "273"),
                            ("features", []),
                            ("features", ["816"]),
                        ))),
                    )),
                    OrderedDict((
                        ("id", "421"),
                        ("name", {"en": "The address element"}),
                        ("subpath",
                         {"en": "sections.html#the-address-element"}),
                        ("notes", None),
                        ("links", OrderedDict((
                            ("specification", "114"),
                            ("features", ["816"]),
                        ))),
                    )),
                    OrderedDict((
                        ("id", "70"),
                        ("name", {"en": "The ADDRESS element"}),
                        ("subpath", {"en": "struct/global.html#h-7.5.6"}),
                        ("notes", None),
                        ("links", OrderedDict((
                            ("specification", "576"),
                            ("features", ["816"]),
                        ))),
                    )),
                ]),
                ("specifications", [
                    OrderedDict((
                        ("id", "62"),
                        ("key", "HTML WHATWG"),
                        ("name", {"en": "WHATWG HTML Living Standard"}),
                        ("uri", {
                            "en": (
                                "http://www.whatwg.org/specs/web-apps/"
                                "current-work/multipage/"),
                        }),
                        ("links", OrderedDict((
                            ("sections", ["745", "746", "747"]),
                            ("maturity", "23"),
                        ))),
                    )),
                    OrderedDict((
                        ("id", "114"),
                        ("key", "HTML5 W3C"),
                        ("name", {"en": "HTML5"}),
                        ("uri", {"en": "http://www.w3.org/TR/html5/"}),
                        ("links", OrderedDict((
                            ("sections", ["420", "421", "422"]),
                            ("maturity", "52"),
                        ))),
                    )),
                    OrderedDict((
                        ("id", "576"),
                        ("key", "HTML4.01"),
                        ("name", {"en": "HTML 4.01 Specification"}),
                        ("uri", {"en": "http://www.w3.org/TR/html401/"}),
                        ("links", OrderedDict((
                            ("sections", ["69", "70", "71"]),
                            ("maturity", "49"),
                        ))),
                    )),
                ]),
                ("maturities", [
                    OrderedDict((
                        ("id", "23"),
                        ("key", "Living"),
                        ("name", {"en": "Living Standard"}),
                        ("links", {"specifications": ["62"]}),
                    )),
                    OrderedDict((
                        ("id", "49"),
                        ("key", "REC"),
                        ("name", OrderedDict((
                            ("en", "Recommendation"),
                            ("jp", "勧告"),
                        ))),
                        ("links", {
                            "specifications": [
                                "84", "85", "272", "273", "274", "576"]
                        }),
                    )),
                    OrderedDict((
                        ("id", "52"),
                        ("key", "CR"),
                        ("name", OrderedDict((
                            ("en", "Candidate Recommendation"),
                            ("ja", "勧告候補"),
                        ))),
                        ("links", {
                            "specifications": ["83", "113", "114", "115"],
                        }),
                    )),
                ]),
                ("supports", [
                    OrderedDict((
                        ("id", "358"),
                        ("support", "yes"),
                        ("prefix", None),
                        ("prefix_mandatory", False),
                        ("alternate_name", None),
                        ("alternate_name_mandatory", False),
                        ("requires_config", None),
                        ("default_config", None),
                        ("protected", False),
                        ("note", None),
                        ("footnote", None),
                        ("links", OrderedDict((
                            ("version", "758"),
                            ("feature", "191"),
                            ("history_current", "3567"),
                            ("history", ["3567"]),
                        ))),
                    )),
                    OrderedDict((
                        ("id", "359"),
                        ("support", "yes"),
                        ("prefix", None),
                        ("prefix_mandatory", False),
                        ("alternate_name", None),
                        ("alternate_name_mandatory", False),
                        ("requires_config", None),
                        ("default_config", None),
                        ("protected", False),
                        ("note", None),
                        ("footnote", None),
                        ("links", OrderedDict((
                            ("version", "759"),
                            ("feature", "191"),
                            ("history_current", "3568"),
                            ("history", ["3568"]),
                        ))),
                    )),
                    OrderedDict((
                        ("id", "360"),
                        ("support", "yes"),
                        ("prefix", None),
                        ("prefix_mandatory", False),
                        ("alternate_name", None),
                        ("alternate_name_mandatory", False),
                        ("requires_config", None),
                        ("default_config", None),
                        ("protected", False),
                        ("note", None),
                        ("footnote", None),
                        ("links", OrderedDict((
                            ("version", "760"),
                            ("feature", "191"),
                            ("history_current", "3569"),
                            ("history", ["3569"]),
                        ))),
                    )),
                    OrderedDict((
                        ("id", "361"),
                        ("support", "yes"),
                        ("prefix", None),
                        ("prefix_mandatory", False),
                        ("alternate_name", None),
                        ("alternate_name_mandatory", False),
                        ("requires_config", None),
                        ("default_config", None),
                        ("protected", False),
                        ("note", None),
                        ("footnote", None),
                        ("links", OrderedDict((
                            ("version", "761"),
                            ("feature", "191"),
                            ("history_current", "3570"),
                            ("history", ["3570"]),
                        ))),
                    )),
                    OrderedDict((
                        ("id", "362"),
                        ("support", "yes"),
                        ("prefix", None),
                        ("prefix_mandatory", False),
                        ("alternate_name", None),
                        ("alternate_name_mandatory", False),
                        ("requires_config", None),
                        ("default_config", None),
                        ("protected", False),
                        ("note", None),
                        ("footnote", None),
                        ("links", OrderedDict((
                            ("version", "762"),
                            ("feature", "191"),
                            ("history_current", "3571"),
                            ("history", ["3571"]),
                        ))),
                    )),
                    OrderedDict((
                        ("id", "362"),
                        ("support", "yes"),
                        ("prefix", None),
                        ("prefix_mandatory", False),
                        ("alternate_name", None),
                        ("alternate_name_mandatory", False),
                        ("requires_config", None),
                        ("default_config", None),
                        ("protected", False),
                        ("note", None),
                        ("footnote", None),
                        ("links", OrderedDict((
                            ("version", "762"),
                            ("feature", "191"),
                            ("history_current", "3571"),
                            ("history", ["3571"]),
                        ))),
                    )),
                    OrderedDict((
                        ("id", "362"),
                        ("support", "yes"),
                        ("prefix", None),
                        ("prefix_mandatory", False),
                        ("alternate_name", None),
                        ("alternate_name_mandatory", False),
                        ("requires_config", None),
                        ("default_config", None),
                        ("protected", False),
                        ("note", None),
                        ("footnote", None),
                        ("links", OrderedDict((
                            ("version", "762"),
                            ("feature", "191"),
                            ("history_current", "3571"),
                            ("history", ["3571"]),
                        ))),
                    )),
                    OrderedDict((
                        ("id", "363"),
                        ("support", "yes"),
                        ("prefix", None),
                        ("prefix_mandatory", False),
                        ("alternate_name", None),
                        ("alternate_name_mandatory", False),
                        ("requires_config", None),
                        ("default_config", None),
                        ("protected", False),
                        ("note", None),
                        ("footnote", None),
                        ("links", OrderedDict((
                            ("version", "763"),
                            ("feature", "191"),
                            ("history_current", "3572"),
                            ("history", ["3572"]),
                        ))),
                    )),
                    OrderedDict((
                        ("id", "364"),
                        ("support", "yes"),
                        ("prefix", None),
                        ("prefix_mandatory", False),
                        ("alternate_name", None),
                        ("alternate_name_mandatory", False),
                        ("requires_config", None),
                        ("default_config", None),
                        ("protected", False),
                        ("note", None),
                        ("footnote", None),
                        ("links", OrderedDict((
                            ("version", "764"),
                            ("feature", "191"),
                            ("history_current", "3573"),
                            ("history", ["3573"]),
                        ))),
                    )),
                    OrderedDict((
                        ("id", "365"),
                        ("support", "yes"),
                        ("prefix", None),
                        ("prefix_mandatory", False),
                        ("alternate_name", None),
                        ("alternate_name_mandatory", False),
                        ("requires_config", None),
                        ("default_config", None),
                        ("protected", False),
                        ("note", None),
                        ("footnote", None),
                        ("links", OrderedDict((
                            ("version", "765"),
                            ("feature", "191"),
                            ("history_current", "3574"),
                            ("history", ["3574"]),
                        ))),
                    )),
                    OrderedDict((
                        ("id", "366"),
                        ("support", "yes"),
                        ("prefix", None),
                        ("prefix_mandatory", False),
                        ("alternate_name", None),
                        ("alternate_name_mandatory", False),
                        ("requires_config", None),
                        ("default_config", None),
                        ("protected", False),
                        ("note", None),
                        ("footnote", None),
                        ("links", OrderedDict((
                            ("version", "766"),
                            ("feature", "191"),
                            ("history_current", "3575"),
                            ("history", ["3575"]),
                        ))),
                    )),
                    OrderedDict((
                        ("id", "367"),
                        ("support", "yes"),
                        ("prefix", None),
                        ("prefix_mandatory", False),
                        ("alternate_name", None),
                        ("alternate_name_mandatory", False),
                        ("requires_config", None),
                        ("default_config", None),
                        ("protected", False),
                        ("note", None),
                        ("footnote", None),
                        ("links", OrderedDict((
                            ("version", "767"),
                            ("feature", "191"),
                            ("history_current", "3576"),
                            ("history", ["3576"]),
                        ))),
                    )),
                    OrderedDict((
                        ("id", "368"),
                        ("support", "yes"),
                        ("prefix", None),
                        ("prefix_mandatory", False),
                        ("alternate_name", None),
                        ("alternate_name_mandatory", False),
                        ("requires_config", None),
                        ("default_config", None),
                        ("protected", False),
                        ("note", None),
                        ("footnote", None),
                        ("links", OrderedDict((
                            ("version", "768"),
                            ("feature", "191"),
                            ("history_current", "3577"),
                            ("history", ["3577"]),
                        ))),
                    )),
                ]),
                ("versions", [
                    OrderedDict((
                        ("id", "758"),
                        ("version", None),
                        ("release_day", None),
                        ("retirement_day", None),
                        ("status", "current"),
                        ("release_notes_uri", None),
                        ("note", None),
                        ("links", OrderedDict((
                            ("browser", "1"),
                            ("supports",
                             ["158", "258", "358", "458"]),
                            ("history_current", "1567"),
                            ("history", ["1567"]),
                        ))),
                    )), OrderedDict((
                        ("id", "759"),
                        ("version", "1.0"),
                        ("release_day", "2004-12-09"),
                        ("retirement_day", "2005-02-24"),
                        ("status", "retired"),
                        ("release_notes_uri", None),
                        ("note", None),
                        ("links", OrderedDict((
                            ("browser", "2"),
                            ("supports",
                             ["159", "259", "359", "459"]),
                            ("history_current", "1568"),
                            ("history", ["1568"]),
                        ))),
                    )), OrderedDict((
                        ("id", "760"),
                        ("version", "1.0"),
                        ("release_day", "1995-08-16"),
                        ("retirement_day", None),
                        ("status", "retired"),
                        ("release_notes_uri", None),
                        ("note", None),
                        ("links", OrderedDict((
                            ("browser", "3"),
                            ("supports",
                             ["160", "260", "360", "460"]),
                            ("history_current", "1569"),
                            ("history", ["1569"]),
                        ))),
                    )), OrderedDict((
                        ("id", "761"),
                        ("version", "5.12"),
                        ("release_day", "2001-06-27"),
                        ("retirement_day", None),
                        ("status", "retired"),
                        ("release_notes_uri", None),
                        ("note", None),
                        ("links", OrderedDict((
                            ("browser", "4"),
                            ("supports",
                             ["161", "261", "361", "461"]),
                            ("history_current", "1570"),
                            ("history", ["1570"]),
                        ))),
                    )), OrderedDict((
                        ("id", "762"),
                        ("version", "1.0"),
                        ("release_day", "2003-06-23"),
                        ("retirement_day", None),
                        ("status", "retired"),
                        ("release_notes_uri", None),
                        ("note", None),
                        ("links", OrderedDict((
                            ("browser", "5"),
                            ("supports",
                             ["162", "262", "362", "462"]),
                            ("history_current", "1571"),
                            ("history", ["1571"]),
                        ))),
                    )), OrderedDict((
                        ("id", "763"),
                        ("version", None),
                        ("release_day", None),
                        ("retirement_day", None),
                        ("status", "current"),
                        ("release_notes_uri", None),
                        ("note", None),
                        ("links", OrderedDict((
                            ("browser", "6"),
                            ("supports",
                             ["163", "263", "363", "463"]),
                            ("history_current", "1572"),
                            ("history", ["1572"]),
                        ))),
                    )), OrderedDict((
                        ("id", "764"),
                        ("version", "1.0"),
                        ("release_day", None),
                        ("retirement_day", None),
                        ("status", "retired"),
                        ("release_notes_uri", None),
                        ("note", "Uses Gecko 1.7"),
                        ("links", OrderedDict((
                            ("browser", "7"),
                            ("supports",
                             ["164", "264", "364", "464"]),
                            ("history_current", "1574"),
                            ("history", ["1574"]),
                        ))),
                    )), OrderedDict((
                        ("id", "765"),
                        ("version", None),
                        ("release_day", None),
                        ("retirement_day", None),
                        ("status", "current"),
                        ("release_notes_uri", None),
                        ("note", None),
                        ("links", OrderedDict((
                            ("browser", "8"),
                            ("supports",
                             ["165", "265", "365", "465"]),
                            ("history_current", "1575"),
                            ("history", ["1575"]),
                        ))),
                    )), OrderedDict((
                        ("id", "766"),
                        ("version", None),
                        ("release_day", None),
                        ("retirement_day", None),
                        ("status", "current"),
                        ("release_notes_uri", None),
                        ("note", None),
                        ("links", OrderedDict((
                            ("browser", "11"),
                            ("supports",
                             ["166", "266", "366", "466"]),
                            ("history_current", "1576"),
                            ("history", ["1576"]),
                        ))),
                    )), OrderedDict((
                        ("id", "767"),
                        ("version", None),
                        ("release_day", None),
                        ("retirement_day", None),
                        ("status", "current"),
                        ("release_notes_uri", None),
                        ("note", None),
                        ("links", OrderedDict((
                            ("browser", "9"),
                            ("supports",
                             ["167", "267", "367", "467"]),
                            ("history_current", "1577"),
                            ("history", ["1577"]),
                        ))),
                    )), OrderedDict((
                        ("id", "768"),
                        ("version", None),
                        ("release_day", None),
                        ("retirement_day", None),
                        ("status", "current"),
                        ("release_notes_uri", None),
                        ("note", None),
                        ("links", OrderedDict((
                            ("browser", "10"),
                            ("supports",
                             ["168", "268", "368", "468"]),
                            ("history_current", "1578"),
                            ("history", ["1578"]),
                        ))),
                    )),
                ]),
                ("browsers", [
                    OrderedDict((
                        ("id", "1"),
                        ("slug", "chrome"),
                        ("name", OrderedDict((
                            ("en", "Chrome"),
                        ))),
                        ("note", None),
                        ("links", OrderedDict((
                            ("versions", ["123", "758"]),
                            ("history_current", "1001"),
                            ("history", ["1001"]),
                        ))),
                    )), OrderedDict((
                        ("id", "2"),
                        ("slug", "firefox"),
                        ("name", OrderedDict((
                            ("en", "Firefox"),
                        ))),
                        ("note", OrderedDict((
                            ("en", "Uses Gecko for its web browser engine."),
                        ))),
                        ("links", OrderedDict((
                            ("versions", ["124", "759"]),
                            ("history_current", "1002"),
                            ("history", ["1002"]),
                        ))),
                    )), OrderedDict((
                        ("id", "3"),
                        ("slug", "ie"),
                        ("name", OrderedDict((
                            ("en", "Internet Explorer"),
                        ))),
                        ("note", None),
                        ("links", OrderedDict((
                            ("versions", ["125", "167", "178", "760"]),
                            ("history_current", "1003"),
                            ("history", ["1003"]),
                        ))),
                    )), OrderedDict((
                        ("id", "4"),
                        ("slug", "opera"),
                        ("name", OrderedDict((
                            ("en", "Opera"),
                        ))),
                        ("note", None),
                        ("links", OrderedDict((
                            ("versions", ["126", "761"]),
                            ("history_current", "1004"),
                            ("history", ["1004"]),
                        ))),
                    )), OrderedDict((
                        ("id", "5"),
                        ("slug", "safari"),
                        ("name", OrderedDict((
                            ("en", "Safari"),
                        ))),
                        ("note", OrderedDict((
                            ("en", "Uses Webkit for its web browser engine."),
                        ))),
                        ("links", OrderedDict((
                            ("versions", ["127", "762"]),
                            ("history_current", "1005"),
                            ("history", ["1005"]),
                        ))),
                    )), OrderedDict((
                        ("id", "6"),
                        ("slug", "android"),
                        ("name", OrderedDict((
                            ("en", "Android"),
                        ))),
                        ("note", None),
                        ("links", OrderedDict((
                            ("versions", ["128", "763"]),
                            ("history_current", "1006"),
                            ("history", ["1006"]),
                        ))),
                    )), OrderedDict((
                        ("id", "7"),
                        ("slug", "firefox-mobile"),
                        ("name", OrderedDict((
                            ("en", "Firefox Mobile"),
                        ))),
                        ("note", OrderedDict((
                            ("en", "Uses Gecko for its web browser engine."),
                        ))),
                        ("links", OrderedDict((
                            ("versions", ["129", "764"]),
                            ("history_current", "1007"),
                            ("history", ["1007"]),
                        ))),
                    )), OrderedDict((
                        ("id", "8"),
                        ("slug", "ie-phone"),
                        ("name", OrderedDict((
                            ("en", "IE Phone"),
                        ))),
                        ("note", None),
                        ("links", OrderedDict((
                            ("versions", ["130", "765"]),
                            ("history_current", "1008"),
                            ("history", ["1008"]),
                        ))),
                    )), OrderedDict((
                        ("id", "9"),
                        ("slug", "opera-mobile"),
                        ("name", OrderedDict((
                            ("en", "Opera Mobile"),
                        ))),
                        ("note", None),
                        ("links", OrderedDict((
                            ("versions", ["131", "767"]),
                            ("history_current", "1009"),
                            ("history", ["1009"]),
                        ))),
                    )), OrderedDict((
                        ("id", "10"),
                        ("slug", "safari-mobile"),
                        ("name", OrderedDict((
                            ("en", "Safari Mobile"),
                        ))),
                        ("note", None),
                        ("links", OrderedDict((
                            ("versions", ["132", "768"]),
                            ("history_current", "1010"),
                            ("history", ["1010"]),
                        ))),
                    )), OrderedDict((
                        ("id", "11"),
                        ("slug", "opera-mini"),
                        ("name", OrderedDict((
                            ("en", "Opera Mini"),
                        ))),
                        ("note", None),
                        ("links", OrderedDict((
                            ("versions", ["131", "766"]),
                            ("history_current", "1019"),
                            ("history", ["1019"]),
                        ))),
                    )),
                ]),
            ))),
            ("links", OrderedDict((
                ("feature.features", OrderedDict((
                    ("href", a + "/features/{feature.features}"),
                    ("type", "features"),
                ))),
                ("features.sections", OrderedDict((
                    ("href", a + "sections/{features.sections}"),
                    ("type", "specfication-sections"),
                ))),
                ("features.parent", OrderedDict((
                    ("href", a + "/features/{features.parent}"),
                    ("type", "features"),
                ))),
                ("features.children", OrderedDict((
                    ("href", a + "/features/{features.children}"),
                    ("type", "features"),
                ))),
                ("features.history_current", OrderedDict((
                    ("href",
                     a + "/historical-features/{features.history_current}"),
                    ("type", "historical-features"),
                ))),
                ("features.history", OrderedDict((
                    ("href", a + "/historical-features/{features.history}"),
                    ("type", "historical-features"),
                ))),
                ("browsers.versions", OrderedDict((
                    ("href", a + "/versions/{browsers.versions}"),
                    ("type", "versions"),
                ))),
                ("browsers.history_current", OrderedDict((
                    ("href",
                     a + "/historical-browsers/{browsers.history_current}"),
                    ("type", "historical-browsers"),
                ))),
                ("browsers.history", OrderedDict((
                    ("href", a + "/historical-browsers/{browsers.history}"),
                    ("type", "historical-browsers"),
                ))),
                ("versions.browser", OrderedDict((
                    ("href", a + "/browsers/{versions.browser}"),
                    ("type", "browsers"),
                ))),
                ("versions.supports", OrderedDict((
                    ("href", a + "/supports/{versions.features}"),
                    ("type", "supports"),
                ))),
                ("versions.history_current", OrderedDict((
                    ("href",
                     a + "/historical-versions/{versions.history_current}"),
                    ("type", "historical-versions"),
                ))),
                ("versions.history", OrderedDict((
                    ("href", a + "/historical-versions/{versions.history}"),
                    ("type", "historical-versions"),
                ))),
                ("supports.version", OrderedDict((
                    ("href", a + "/versions/{supports.version}"),
                    ("type", "versions"),
                ))),
                ("supports.feature", OrderedDict((
                    ("href", a + "/browsers/{supports.feature}"),
                    ("type", "features"),
                ))),
                ("supports.history_current", OrderedDict((
                    ("href",
                     a + "/historical-supports/{supports.history_current}"),
                    ("type", "historical-supports"),
                ))),
                ("supports.history", OrderedDict((
                    ("href", a + "/historical-supports/{supports.history}"),
                    ("type", "historical-supports"),
                ))),
                ("specifications.sections", OrderedDict((
                    ("href", a + "/sections/{specifications.sections}"),
                    ("type", "sections"),
                ))),
                ("specifications.maturity", OrderedDict((
                    ("href", a + "/maturities/{specifications.maturity}"),
                    ("type", "maturities"),
                ))),
                ("sections.specification", OrderedDict((
                    ("href", a + "/specifications/{sections.specification}"),
                    ("type", "specifications"),
                ))),
                ("sections.features", OrderedDict((
                    ("href", a + "/sections/{sections.features}"),
                    ("type", "features"),
                ))),
                ("maturities.specifications", OrderedDict((
                    ("href",
                     a + "/specifications/{maturities.specifications}"),
                    ("type", "specifications"),
                ))),
            ))),
            ("meta", OrderedDict((
                ("compat-table", OrderedDict((
                    ("tabs", [
                        OrderedDict((
                            ("name", OrderedDict((
                                ("en", "Desktop"),
                            ))),
                            ("browsers", ["1", "2", "3", "4", "5"]),
                        )),
                        OrderedDict((
                            ("name", OrderedDict((
                                ("en", "Mobile"),
                            ))),
                            ("browsers", ["6", "7", "8", "11", "9", "10"]),
                        )),
                    ]),
                    ("supports", OrderedDict((
                        ("191", OrderedDict((
                            ("1", ["358"]),
                            ("2", ["359"]),
                            ("3", ["360"]),
                            ("4", ["361"]),
                            ("5", ["362"]),
                            ("6", ["363"]),
                            ("7", ["364"]),
                            ("8", ["365"]),
                            ("11", ["366"]),
                            ("9", ["367"]),
                            ("10", ["368"]),
                        ))),
                    ))),
                ))),
            ))),
        ))
        return Response(feature_set)
