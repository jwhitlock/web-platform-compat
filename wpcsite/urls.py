from django.conf.urls import patterns, include, url
from django.contrib import admin

from webplatformcompat.urls import webplatformcompat_urlpatterns

urlpatterns = patterns(
    '',
    url(r'^accounts/', include('allauth.urls')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'', include(webplatformcompat_urlpatterns)),
)
