"""Admin interface for mdn app."""
from django.contrib import admin

from .models import Issue, FeaturePage, PageMeta, TranslatedContent


class IssueAdmin(admin.ModelAdmin):
    readonly_fields = ('page', 'content')


class FeaturePageAdmin(admin.ModelAdmin):
    readonly_fields = ('feature',)


class ContentAdmin(admin.ModelAdmin):
    readonly_fields = ('page',)


admin.site.register(Issue, IssueAdmin)
admin.site.register(FeaturePage, FeaturePageAdmin)
admin.site.register(PageMeta, ContentAdmin)
admin.site.register(TranslatedContent, ContentAdmin)
