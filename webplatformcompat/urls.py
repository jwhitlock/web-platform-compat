from django.conf.urls import include, patterns, url
from django.views.generic.base import RedirectView
from mdn.urls import mdn_urlpatterns
from webplatformcompat.routers import router

from .views import RequestView, ViewFeature


webplatformcompat_urlpatterns = patterns(
    '',
    url(r'^$', RequestView.as_view(
        template_name='webplatformcompat/home.html'),
        name='home'),
    url(r'^about/', RequestView.as_view(
        template_name='webplatformcompat/about.html'),
        name='about'),
    url(r'^browse/', RequestView.as_view(
        template_name='webplatformcompat/browse.html'),
        name='browse'),
    url(r'^api-auth/', include('rest_framework.urls',
        namespace='rest_framework')),
    url(r'^api/$', RedirectView.as_view(url='/api/v1/', permanent=False),
        name='api_root'),
    url(r'^api/v1/', include(router.urls, namespace='v1')),
    url(r'^importer$', RedirectView.as_view(
        url='/importer/', permanent=False)),
    url(r'^importer/', include(mdn_urlpatterns)),
    url(r'^view_feature/(?P<feature_id>\d+)(.html)?$', ViewFeature.as_view(
        template_name='webplatformcompat/feature-js.html'),
        name='view_feature'),
)
