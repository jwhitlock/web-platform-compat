# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils.encoding import python_2_unicode_compatible
from mptt.models import MPTTModel, TreeForeignKey
from simple_history import register
from simple_history.models import HistoricalRecords

from .fields import TranslatedField, SecureURLField


@python_2_unicode_compatible
class Browser(models.Model):
    '''A browser or other web client'''
    slug = models.SlugField(
        help_text="Unique, human-friendly slug.",
        unique=True)
    icon = SecureURLField(
        help_text="Representative image for browser.",
        blank=True)
    name = TranslatedField(
        help_text="Branding name of browser, client, or platform.")
    note = TranslatedField(
        help_text="Extended information about browser, client, or platform.",
        blank=True, null=True)
    history = HistoricalRecords()

    def __str__(self):
        return self.slug


@python_2_unicode_compatible
class Version(models.Model):
    '''A version of a browser'''
    STATUS_CHOICES = [(k, k) for k in (
        'unknown',
        'current',
        'future',
        'retired',
        'beta',
        'retired beta',
    )]

    browser = models.ForeignKey(Browser, related_name='versions')
    version = models.CharField(
        help_text="Version string.",
        blank=True, max_length=20)
    release_day = models.DateField(
        help_text="Day of release to public, ISO 8601 format.",
        blank=True, null=True)
    retirement_day = models.DateField(
        help_text="Day this version stopped being supported, ISO 8601 format.",
        blank=True, null=True)
    status = models.CharField(
        max_length=15, choices=STATUS_CHOICES, default='unknown')
    release_notes_uri = TranslatedField(
        help_text="URI of release notes.",
        blank=True, null=True)
    note = TranslatedField(
        help_text="Notes about this version.",
        blank=True, null=True)
    history = HistoricalRecords()

    def __str__(self):
        return "{0} {1}".format(self.browser, self.version)

    class Meta:
        order_with_respect_to = 'browser'


@python_2_unicode_compatible
class Feature(MPTTModel):
    '''A web technology'''

    slug = models.SlugField(
        help_text="Unique, human-friendly slug.",
        unique=True)
    mdn_path = models.CharField(
        help_text=(
            "The path to the page on MDN that this feature was first"
            " scraped from.  May be used in UX or for debugging import"
            " scripts."),
        blank=True, max_length=255)
    experimental = models.BooleanField(
        help_text=(
            "True if a feature is considered experimental, such as being"
            " non-standard or part of an non-ratified spec."),
        default=False)
    standardized = models.BooleanField(
        help_text=(
            "True if a feature is described in a standards-track spec,"
            " regardless of the spec’s maturity."),
        default=True)
    stable = models.BooleanField(
        help_text=(
            "True if a feature is considered suitable for production"
            " websites."),
        default=True)
    obsolete = models.BooleanField(
        help_text=(
            "True if a feature should not be used in new development."),
        default=False)
    name = TranslatedField(
        help_text="Feature name, in canonical or localized form.",
        allow_canonical=True)
    parent = TreeForeignKey(
        'self', help_text="Feature set that contains this feature",
        null=True, blank=True, related_name='children')

    def __str__(self):
        return self.slug

# Must be done after class declaration due to coordination with MPTT
# https://github.com/treyhunner/django-simple-history/issues/87
register(Feature)


@python_2_unicode_compatible
class Support(models.Model):
    '''Does a browser version support a feature?'''

    SUPPORT_CHOICES = [(k, k) for k in (
        'yes',
        'no',
        'partial',
        'unknown',
        'never'
    )]

    version = models.ForeignKey(Version, related_name='supports')
    feature = models.ForeignKey(Feature, related_name='supports')
    support = models.CharField(
        help_text="Does the browser version support this feature?",
        max_length=10, choices=SUPPORT_CHOICES, default='yes')
    prefix = models.CharField(
        help_text="Prefix to apply to the feature name.",
        max_length=20, blank=True)
    prefix_mandatory = models.BooleanField(
        help_text="Is the prefix required?", default=False)
    alternate_name = models.CharField(
        help_text="Alternate name for this feature.",
        max_length=50, blank=True)
    alternate_mandatory = models.BooleanField(
        help_text="Is the alternate name required?", default=False)
    requires_config = models.CharField(
        help_text="A configuration string to enable the feature.",
        max_length=100, blank=True)
    default_config = models.CharField(
        help_text="The configuration string in the shipping browser.",
        max_length=100, blank=True)
    protected = models.BooleanField(
        help_text=(
            "True if feature requires additional steps to enable in order to"
            " protect the user's security or privacy."),
        default=False)
    note = TranslatedField(
        help_text="Short note on support, designed for inline display.",
        null=True, blank=True)
    footnote = TranslatedField(
        help_text=(
            "Long note on support, designed for display after a compatiblity"
            " table, in MDN wiki format."),
        null=True, blank=True)
    history = HistoricalRecords()

    def __str__(self):
        return (
            "%s support for feature %s is %s" %
            (self.version, self.feature, self.support))


#
# Cache invalidation signals
#

cached_model_names = (
    'Browser', 'Feature', 'Version', 'User', 'HistoricalBrowser')


@receiver(post_save, dispatch_uid='post_save_update_cache')
def post_save_update_cache(sender, instance, created, raw, **kwargs):
    if raw:
        return
    name = sender.__name__
    if name in cached_model_names:
        from .tasks import update_cache_for_instance
        update_cache_for_instance(name, instance.pk, instance)


@receiver(post_delete, dispatch_uid='post_delete_update_cache')
def post_delete_update_cache(sender, instance, **kwargs):
    name = sender.__name__
    if name in cached_model_names:
        from .tasks import update_cache_for_instance
        update_cache_for_instance(name, instance.pk, instance)
