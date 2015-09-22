# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import models
from django.db.models.signals import post_delete, post_save, m2m_changed
from django.dispatch import receiver
from django.utils.encoding import python_2_unicode_compatible
from django_extensions.db.fields.json import JSONField
from mptt.models import MPTTModel, TreeForeignKey
from sortedm2m.fields import SortedManyToManyField

from .fields import TranslatedField
from .history import register, HistoricalRecords
from .validators import VersionAndStatusValidator


class CachingManager(models.Manager):
    def create(self, **kwargs):
        """Add the _delay_cache value to the object before saving"""
        delay_cache = kwargs.pop('_delay_cache', False)
        obj = self.model(**kwargs)
        self._for_write = True
        obj._delay_cache = delay_cache
        obj.save(force_insert=True, using=self.db)
        return obj

#
# "Regular" (non-historical) models
#


@python_2_unicode_compatible
class Browser(models.Model):
    """A browser or other web client"""
    slug = models.SlugField(
        help_text="Unique, human-friendly slug.",
        unique=True)
    name = TranslatedField(
        help_text="Branding name of browser, client, or platform.")
    note = TranslatedField(
        help_text="Extended information about browser, client, or platform.",
        blank=True, null=True)
    objects = CachingManager()
    history = HistoricalRecords()

    def __str__(self):
        return self.slug


@python_2_unicode_compatible
class Feature(MPTTModel):
    """A web technology"""

    slug = models.SlugField(
        help_text="Unique, human-friendly slug.",
        unique=True)
    mdn_uri = TranslatedField(
        help_text='The URI of the MDN page that documents this feature.',
        blank=True, null=True)
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
    sections = SortedManyToManyField(
        'Section', related_name='features', blank=True)
    objects = CachingManager()
    # history = HistoricalFeatureRecords()  # Registered below

    def __str__(self):
        return self.slug


@python_2_unicode_compatible
class Maturity(models.Model):
    """Maturity of a specification document"""
    slug = models.SlugField(
        help_text=(
            "Unique, human-friendly slug, sourced from the KumaScript macro"
            " Spec2"),
        unique=True)
    name = TranslatedField(
        help_text="Name of maturity")
    objects = CachingManager()
    # history = HistoricalMaturityRecords()  # Registered below

    class Meta:
        verbose_name_plural = 'maturities'

    def __str__(self):
        return self.slug


@python_2_unicode_compatible
class Section(models.Model):
    """A section of a specification document"""
    specification = models.ForeignKey('Specification', related_name='sections')
    number = TranslatedField(
        help_text="Section number",
        blank=True)
    name = TranslatedField(
        help_text="Name of section, without section number")
    subpath = TranslatedField(
        help_text=(
            "A subpage (possible with an #anchor) to get to the subsection"
            " in the specification."),
        blank=True)
    note = TranslatedField(
        help_text="Notes for this section",
        blank=True)
    objects = CachingManager()
    history = HistoricalRecords()

    class Meta:
        order_with_respect_to = 'specification'

    def __str__(self):
        if self.name and self.name.get('en'):
            return self.name['en']
        else:
            return '<unnamed>'


@python_2_unicode_compatible
class Specification(models.Model):
    """A Specification document"""
    maturity = models.ForeignKey('Maturity', related_name='specifications')
    slug = models.SlugField(
        help_text="Unique, human-friendly slug",
        unique=True)
    mdn_key = models.CharField(
        help_text="Key used in the KumaScript macro SpecName",
        max_length=30, blank=True)
    name = TranslatedField(
        help_text="Name of specification")
    uri = TranslatedField(
        help_text="Specification URI, without subpath and anchor")
    objects = CachingManager()
    history = HistoricalRecords()

    def __str__(self):
        return self.slug


@python_2_unicode_compatible
class Support(models.Model):
    """Does a browser version support a feature?"""

    SUPPORT_CHOICES = [(k, k) for k in (
        'yes',
        'no',
        'partial',
        'unknown',
    )]

    version = models.ForeignKey('Version', related_name='supports')
    feature = models.ForeignKey('Feature', related_name='supports')
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
        help_text="Notes for this support",
        null=True, blank=True)
    objects = CachingManager()
    history = HistoricalRecords()

    class Meta:
        unique_together = (('version', 'feature'),)

    def __str__(self):
        return (
            "%s support for feature %s is %s" %
            (self.version, self.feature, self.support))


@python_2_unicode_compatible
class Version(models.Model):
    """A version of a browser"""
    STATUS_CHOICES = [(k, k) for k in (
        'unknown',
        'current',
        'future',
        'retired',
        'beta',
        'retired beta',
    )]

    browser = models.ForeignKey('Browser', related_name='versions')
    version = models.CharField(
        help_text="Version string.",
        max_length=20)
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
    objects = CachingManager()
    history = HistoricalRecords()

    def __str__(self):
        return "{0} {1}".format(self.browser, self.version)

    def clean(self):
        super(Version, self).clean()
        VersionAndStatusValidator()(self)

    class Meta:
        order_with_respect_to = 'browser'


#
# Customized historical models and registration
#

class HistoricalFeatureRecords(HistoricalRecords):
    additional_fields = {
        'sections': JSONField(default=[])
    }

    def get_sections_value(self, instance, mtype):
        section_pks = list(
            instance.sections.values_list('pk', flat=True))
        return section_pks


class HistoricalMaturityRecords(HistoricalRecords):
    def get_meta_options(self, model):
        meta_fields = super(
            HistoricalMaturityRecords, self).get_meta_options(model)
        meta_fields['verbose_name_plural'] = 'historical_maturities'
        return meta_fields


register(Feature, records_class=HistoricalFeatureRecords)
register(Maturity, records_class=HistoricalMaturityRecords)


#
# Cache invalidation signals
#

cached_model_names = (
    'Browser', 'Feature', 'Maturity', 'Section', 'Specification',
    'Support', 'Version', 'User')


@receiver(
    m2m_changed, sender=Feature.sections.through,
    dispatch_uid='m2m_changed_feature_section')
def feature_sections_changed_update_order(
        sender, instance, action, reverse, model, pk_set, **kwargs):
    """Maintain feature.section_order"""
    if action not in ('post_add', 'post_remove', 'post_clear'):
        # post_clear is not handled, because clear is called in
        # django.db.models.fields.related.ReverseManyRelatedObjects.__set__
        # before setting the new order
        return
    if getattr(instance, '_delay_cache', False):
        return

    if model == Section:
        assert type(instance) == Feature
        features = [instance]
        if pk_set:
            sections = list(Section.objects.filter(pk__in=pk_set))
        else:
            sections = []
    else:
        if pk_set:
            features = list(Feature.objects.filter(pk__in=pk_set))
        else:
            features = []
        sections = [instance]

    from .tasks import update_cache_for_instance
    for feature in features:
        update_cache_for_instance('Feature', feature.pk, feature, False)
    for section in sections:
        update_cache_for_instance('Section', section.pk, section, False)


@receiver(post_delete, dispatch_uid='post_delete_update_cache')
def post_delete_update_cache(sender, instance, **kwargs):
    name = sender.__name__
    if name in cached_model_names:
        delay_cache = getattr(instance, '_delay_cache', False)
        if not delay_cache:
            from .tasks import update_cache_for_instance
            update_cache_for_instance(name, instance.pk, instance, False)


@receiver(post_save, dispatch_uid='post_save_update_cache')
def post_save_update_cache(sender, instance, created, raw, **kwargs):
    if raw:
        return
    name = sender.__name__
    if name in cached_model_names:
        delay_cache = getattr(instance, '_delay_cache', False)
        if not delay_cache:
            from .tasks import update_cache_for_instance
            update_cache_for_instance(name, instance.pk, instance, False)


#
# New user signals
#
@receiver(
    post_save, sender=settings.AUTH_USER_MODEL,
    dispatch_uid='add_user_to_change_resource_group')
def add_user_to_change_resource_group(
        signal, sender, instance, created, raw, **kwargs):
    if created and not raw:
        from django.contrib.auth.models import Group
        instance.groups.add(Group.objects.get(name='change-resource'))
        post_save_update_cache(sender, instance, created, raw, **kwargs)
