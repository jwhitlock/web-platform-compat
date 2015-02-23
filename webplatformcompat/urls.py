from django.conf.urls import include, patterns, url
from django.views.generic.base import RedirectView
from mdn.urls import mdn_urlpatterns
from webplatformcompat.routers import router

from .views import RequestView, ViewFeature


webplatformcompat_urlpatterns = patterns(
    '',
    url(r'^$', RequestView.as_view(
        template_name='webplatformcompat/home.jinja2'),
        name='home'),
    url(r'^about/', RequestView.as_view(
        template_name='webplatformcompat/about.jinja2'),
        name='about'),
    url(r'^accounts/profile/$', RequestView.as_view(
        template_name='webplatformcompat/profile.jinja2'),
        name='account_profile'),
    url(r'^browse/', RequestView.as_view(
        template_name='webplatformcompat/browse.jinja2'),
        name='browse'),
    url(r'^api-auth/', include('rest_framework.urls',
        namespace='rest_framework')),
    url(r'^api/$', RedirectView.as_view(url='/api/v1/', permanent=False),
        name='api_root'),
    url(r'^api/v1/', include(router.urls)),
    url(r'^importer$', RedirectView.as_view(
        url='/importer/', permanent=False)),
    url(r'^importer/', include(mdn_urlpatterns)),
    url(r'^view_feature/(?P<feature_id>\d+)(.html)?$', ViewFeature.as_view(
        template_name='webplatformcompat/feature.js.jinja2'),
        name='view_feature'),
)
