# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from django.db.models.signals import post_delete, post_save, m2m_changed
from django.dispatch import receiver
from django.utils.encoding import python_2_unicode_compatible
from django.utils.timezone import now
from django_extensions.db.fields.json import JSONField
from mptt.models import MPTTModel, TreeForeignKey
from simple_history.models import HistoricalRecords as BaseHistoricalRecords
from sortedm2m.fields import SortedManyToManyField

from .fields import TranslatedField


def register(
        model, app=None, manager_name='history', records_class=None,
        **records_config):
    """
    Create historical model for `model` and attach history manager to `model`.

    Variant of simple_history.register that allows override of records class
    """
    from simple_history import models
    if model._meta.db_table not in models.registered_models:
        records_class = records_class or HistoricalRecords
        records = records_class(**records_config)
        records.manager_name = manager_name
        records.module = app and ("%s.models" % app) or model.__module__
        records.add_extra_methods(model)
        records.finalize(model)
        models.registered_models[model._meta.db_table] = model
    else:
        pass  # pragma: nocover


class HistoricalRecords(BaseHistoricalRecords):
    '''simplehistory.HistoricalRecords with modifications

    Can easily add additional fields
    '''
    additional_fields = {}

    def copy_fields(self, model):
        '''Add additional_fields to the historic model'''
        fields = super(HistoricalRecords, self).copy_fields(model)
        for name, field in self.additional_fields.items():
            assert name not in fields
            assert hasattr(self, 'get_%s_value' % name)
            fields[name] = field
        return fields

    def create_historical_record(self, instance, type):
        '''Add extra data when creating the historic record'''
        history_date = getattr(instance, '_history_date', now())
        history_user = self.get_history_user(instance)
        manager = getattr(instance, self.manager_name)
        attrs = {}
        for field in instance._meta.fields:
            attrs[field.attname] = getattr(instance, field.attname)

        # New code - add additional data
        for field_name in self.additional_fields:
            loader = getattr(self, 'get_%s_value' % field_name)
            value = loader(instance, type)
            attrs[field_name] = value

        manager.create(history_date=history_date, history_type=type,
                       history_user=history_user, **attrs)


@python_2_unicode_compatible
class Browser(models.Model):
    '''A browser or other web client'''
    slug = models.SlugField(
        help_text="Unique, human-friendly slug.",
        unique=True)
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
    sections = SortedManyToManyField('Section', related_name='features')

    def __str__(self):
        return self.slug


class HistoricalFeatureRecords(HistoricalRecords):

    additional_fields = {
        'sections':  JSONField(default=[])
    }

    def get_sections_value(self, instance, mtype):
        new_section_data = (
            hasattr(instance, '_m2m_data') and
            instance._m2m_data.get('sections') is not None)
        if new_section_data:
            section_pks = [s.pk for s in instance._m2m_data['sections']]
        else:
            section_pks = list(
                instance.sections.values_list('pk', flat=True))
        return section_pks


# Must be done after class declaration due to coordination with MPTT
# https://github.com/treyhunner/django-simple-history/issues/87
register(Feature, records_class=HistoricalFeatureRecords)


@receiver(
    m2m_changed, sender=Feature.sections.through,
    dispatch_uid='m2m_changed_feature_section')
def feature_sections_changed_update_order(
        sender, instance, action, reverse, model, pk_set, **kwargs):
    '''Maintain feature.section_order'''
    if action not in ('post_add', 'post_remove', 'post_clear'):
        # post_clear is not handled, because clear is called in
        # django.db.models.fields.related.ReverseManyRelatedObjects.__set__
        # before setting the new order
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
        update_cache_for_instance('Feature', feature.pk, feature)
    for section in sections:
        update_cache_for_instance('Section', section.pk, section)


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

    class Meta:
        unique_together = (('version', 'feature'),)

    def __str__(self):
        return (
            "%s support for feature %s is %s" %
            (self.version, self.feature, self.support))


class HistoricalMaturityRecords(HistoricalRecords):
    def get_meta_options(self, model):
        meta_fields = super(
            HistoricalMaturityRecords, self).get_meta_options(model)
        meta_fields['verbose_name_plural'] = 'historical_maturities'
        return meta_fields


@python_2_unicode_compatible
class Maturity(models.Model):
    '''Maturity of a specification document'''
    slug = models.SlugField(
        help_text=(
            "Unique, human-friendly slug, sourced from the KumaScript macro"
            " Spec2"),
        unique=True)
    name = TranslatedField(
        help_text="Name of maturity")
    history = HistoricalMaturityRecords()

    class Meta:
        verbose_name_plural = 'maturities'

    def __str__(self):
        return self.slug


@python_2_unicode_compatible
class Specification(models.Model):
    '''A Specification document'''
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

    history = HistoricalRecords()

    def __str__(self):
        return self.slug


@python_2_unicode_compatible
class Section(models.Model):
    '''A section of a specification document'''
    specification = models.ForeignKey('Specification', related_name='sections')
    number = models.CharField(
        help_text="Section number",
        max_length=10, blank=True)
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
    history = HistoricalRecords()

    class Meta:
        order_with_respect_to = 'specification'

    def __str__(self):
        if self.name and self.name.get('en'):
            return self.name['en']
        else:
            return '<unnamed>'


#
# Cache invalidation signals
#

cached_model_names = (
    'Browser', 'Feature', 'Maturity', 'Section', 'Specification', 'Support',
    'Version', 'User', 'HistoricalBrowser')


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
