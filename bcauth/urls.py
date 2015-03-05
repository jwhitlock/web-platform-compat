"""URLs for bcauth."""
from django.conf.urls import patterns, url
from django.views.generic.base import RedirectView

from webplatformcompat.views import RequestView

bcauth_urlpatterns = patterns(
    'bcauth.views',
    url(r'^accounts/$', RedirectView.as_view(
        url='/accounts/profile/', permanent=False)),
    url(r'^accounts/profile/$', RequestView.as_view(
        template_name='account/profile.jinja2'),
        name='account_profile'),
)
