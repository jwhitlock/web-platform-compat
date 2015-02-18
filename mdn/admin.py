"""Admin interface for mdn app."""
from django.contrib import admin

from .models import FeaturePage, PageMeta, TranslatedContent

admin.site.register(FeaturePage)
admin.site.register(PageMeta)
admin.site.register(TranslatedContent)
