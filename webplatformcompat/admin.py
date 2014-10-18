from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import Browser, Feature, Maturity, Support, Version


class BrowserAdmin(SimpleHistoryAdmin):
    pass


class FeatureAdmin(SimpleHistoryAdmin):
    pass


class MaturityAdmin(SimpleHistoryAdmin):
    pass


class SupportAdmin(SimpleHistoryAdmin):
    raw_id_fields = ('version', 'feature')


class VersionAdmin(SimpleHistoryAdmin):
    raw_id_fields = ('browser',)


admin.site.register(Browser, BrowserAdmin)
admin.site.register(Feature, FeatureAdmin)
admin.site.register(Maturity, MaturityAdmin)
admin.site.register(Support, SupportAdmin)
admin.site.register(Version, VersionAdmin)
