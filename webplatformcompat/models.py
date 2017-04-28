# -*- coding: utf-8 -*-
"""API database models.

Additional models (Changeset, historical models) are defined in history.py.
"""

from __future__ import unicode_literals

from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.functional import cached_property
from django_extensions.db.fields.json import JSONField
from mptt.managers import TreeManager
from mptt.models import MPTTModel, TreeForeignKey

from .fields import TranslatedField
from .history import register, HistoricalRecords
from .validators import VersionAndStatusValidator


class CachingManagerMixin(object):
    def delay_create(self, **kwargs):
        """Add the _delay_cache value to the object before saving."""
        delay_cache = kwargs.pop('_delay_cache', False)
        obj = self.model(**kwargs)
        self._for_write = True
        obj._delay_cache = delay_cache
        obj.save(force_insert=True, using=self.db)
        return obj


class CachingManager(models.Manager, CachingManagerMixin):
    # Django magic prevents a standard override of create
    create = CachingManagerMixin.delay_create


class CachingTreeManager(TreeManager, CachingManagerMixin):
    # Django magic prevents a standard override of create
    create = CachingManagerMixin.delay_create


class HistoryMixin(object):
    @property
    def current_history_id(self):
        """Return the current history ID, used in many views."""
        return getattr(self, 'history').only('history_id').latest().history_id


#
# "Regular" (non-historical) models
#


@python_2_unicode_compatible
class Browser(HistoryMixin, models.Model):
    """A browser or other web client."""

    slug = models.SlugField(
        help_text='Unique, human-friendly slug.',
        unique=True)
    name = TranslatedField(
        help_text='Branding name of browser, client, or platform.')
    note = TranslatedField(
        help_text='Extended information about browser, client, or platform.',
        blank=True, null=True)
    objects = CachingManager()
    # history = HistoricalRecords()  # Registered below

    def __str__(self):
        return self.slug


@python_2_unicode_compatible
class Feature(HistoryMixin, MPTTModel):
    """A web technology."""

    slug = models.SlugField(
        help_text='Unique, human-friendly slug.',
        unique=True)
    mdn_uri = TranslatedField(
        help_text='The URI of the MDN page that documents this feature.',
        blank=True, null=True)
    experimental = models.BooleanField(
        help_text=(
            'True if a feature is considered experimental, such as being'
            ' non-standard or part of an non-ratified spec.'),
        default=False)
    standardized = models.BooleanField(
        help_text=(
            'True if a feature is described in a standards-track spec,'
            ' regardless of the spec’s maturity.'),
        default=True)
    stable = models.BooleanField(
        help_text=(
            'True if a feature is considered suitable for production'
            ' websites.'),
        default=True)
    obsolete = models.BooleanField(
        help_text=(
            'True if a feature should not be used in new development.'),
        default=False)
    name = TranslatedField(
        help_text='Feature name, in canonical or localized form.',
        allow_canonical=True)
    parent = TreeForeignKey(
        'self', help_text='Feature set that contains this feature',
        null=True, blank=True, related_name='children')
    objects = CachingTreeManager()
    # history = HistoricalFeatureRecords()  # Registered below

    def __str__(self):
        return self.slug

    def set_children_order(self, children):
        """Set the child features in the given order.

        django-mptt doesn't have a function to do this, and uses direct SQL
        to change the tree, so a lot of reloading is required to get it right.
        """
        # Verify that all children are present
        current_children = list(self.get_children())
        current_set = set([child.pk for child in current_children])
        new_set = set([child.pk for child in children])
        assert current_set == new_set, 'Can not add/remove child features.'

        # Set order, refreshing as we go
        prev_child = None
        moved = False
        for pos, next_child in enumerate(children):
            if current_children[pos].pk != next_child.pk:
                if moved:
                    prev_child.refresh_from_db()
                    next_child.refresh_from_db()
                if prev_child is None:
                    next_child.move_to(self, 'first-child')
                else:
                    next_child.move_to(prev_child, 'right')
                current_children = list(self.get_children())
                moved = True
            prev_child = next_child

    @cached_property
    def row_descendant_pks(self):
        """Get the ordered primary keys for descendants representing rows."""
        pks = []
        for child in self.get_children():
            if not child.mdn_uri:
                pks.append(child.pk)
                pks.extend(child.row_descendant_pks)
        return pks

    @cached_property
    def descendant_pks(self):
        """Get the ordered primary keys for descendants."""
        return list(self.get_descendants().values_list('pk', flat=True))

    @cached_property
    def descendant_count(self):
        """Get the count of all descendants."""
        return self.get_descendant_count()

    @cached_property
    def row_children(self):
        return [child for child in self.get_children() if not child.mdn_uri]

    @cached_property
    def row_children_pks(self):
        """Get the ordered primary keys for children representing rows."""
        return [
            child_pk for child_pk, is_page in self._child_pks_and_is_page
            if not is_page]

    @cached_property
    def page_children_pks(self):
        """Get the ordered primary keys for children representing rows."""
        return [
            child_pk for child_pk, is_page in self._child_pks_and_is_page
            if is_page]

    @cached_property
    def _child_pks_and_is_page(self):
        """Get the ordered primary keys and if the child is a page feature."""
        pk_and_is_page = []
        for child in self.get_children().only('pk', 'mdn_uri'):
            pk_and_is_page.append((child.pk, bool(child.mdn_uri)))
        return pk_and_is_page


@python_2_unicode_compatible
class Maturity(HistoryMixin, models.Model):
    """Maturity of a specification document."""

    slug = models.SlugField(
        help_text=(
            'Unique, human-friendly slug, sourced from the KumaScript macro'
            ' Spec2'),
        unique=True)
    name = TranslatedField(
        help_text='Name of maturity')
    objects = CachingManager()
    # history = HistoricalMaturityRecords()  # Registered below

    class Meta:
        verbose_name_plural = 'maturities'

    def __str__(self):
        return self.slug


@python_2_unicode_compatible
class Reference(HistoryMixin, models.Model):
    """The reference of a feature to a section of a specification."""

    feature = models.ForeignKey('Feature', related_name='references')
    section = models.ForeignKey('Section', related_name='references')
    note = TranslatedField(
        help_text='Notes for this section',
        blank=True)
    objects = CachingManager()
    history = HistoricalRecords()

    class Meta:
        order_with_respect_to = 'feature'
        unique_together = (('feature', 'section'),)

    def __str__(self):
        return 'feature {} refers to section {}'.format(
            self.feature_id, self.section_id)


@python_2_unicode_compatible
class Section(HistoryMixin, models.Model):
    """A section of a specification document."""

    specification = models.ForeignKey('Specification', related_name='sections')
    number = TranslatedField(
        help_text='Section number',
        blank=True)
    name = TranslatedField(
        help_text='Name of section, without section number')
    # TODO Remove the line behold and uncomment the lines down this,
    # once the PR is merged
    # name = TranslatedField(
    #    help_text='Name of section, without section number', blank=True)
    subpath = TranslatedField(
        help_text=(
            'A subpage (possible with an #anchor) to get to the subsection'
            ' in the specification.'),
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
class Specification(HistoryMixin, models.Model):
    """A Specification document."""

    maturity = models.ForeignKey('Maturity', related_name='specifications')
    slug = models.SlugField(
        help_text='Unique, human-friendly slug',
        unique=True)
    mdn_key = models.CharField(
        help_text='Key used in the KumaScript macro SpecName',
        max_length=30, blank=True)
    name = TranslatedField(
        help_text='Name of specification')
    uri = TranslatedField(
        help_text='Specification URI, without subpath and anchor')
    objects = CachingManager()
    # history = HistoricalRecords()  # Registered below

    def __str__(self):
        return self.slug


@python_2_unicode_compatible
class Support(HistoryMixin, models.Model):
    """Detail the support of a browser version for a feature."""

    SUPPORT_CHOICES = [(k, k) for k in (
        'yes',
        'no',
        'partial',
        'unknown',
    )]

    version = models.ForeignKey('Version', related_name='supports')
    feature = models.ForeignKey('Feature', related_name='supports')
    support = models.CharField(
        help_text='Does the browser version support this feature?',
        max_length=10, choices=SUPPORT_CHOICES, default='yes')
    prefix = models.CharField(
        help_text='Prefix to apply to the feature name.',
        max_length=20, blank=True)
    prefix_mandatory = models.BooleanField(
        help_text='Is the prefix required?', default=False)
    alternate_name = models.CharField(
        help_text='Alternate name for this feature.',
        max_length=50, blank=True)
    alternate_mandatory = models.BooleanField(
        help_text='Is the alternate name required?', default=False)
    requires_config = models.CharField(
        help_text='A configuration string to enable the feature.',
        max_length=100, blank=True)
    default_config = models.CharField(
        help_text='The configuration string in the shipping browser.',
        max_length=100, blank=True)
    protected = models.BooleanField(
        help_text=(
            'True if feature requires additional steps to enable in order to'
            ' protect the user\'s security or privacy.'),
        default=False)
    note = TranslatedField(
        help_text='Notes for this support',
        null=True, blank=True)
    objects = CachingManager()
    history = HistoricalRecords()

    class Meta:
        unique_together = (('version', 'feature'),)

    def __str__(self):
        return (
            '%s support for feature %s is %s' %
            (self.version, self.feature, self.support))


@python_2_unicode_compatible
class Version(HistoryMixin, models.Model):
    """A version of a browser."""

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
        help_text='Version string.',
        max_length=20)
    release_day = models.DateField(
        help_text='Day of release to public, ISO 8601 format.',
        blank=True, null=True)
    retirement_day = models.DateField(
        help_text='Day this version stopped being supported, ISO 8601 format.',
        blank=True, null=True)
    status = models.CharField(
        max_length=15, choices=STATUS_CHOICES, default='unknown')
    release_notes_uri = TranslatedField(
        help_text='URI of release notes.',
        blank=True, null=True)
    note = TranslatedField(
        help_text='Notes about this version.',
        blank=True, null=True)
    objects = CachingManager()
    history = HistoricalRecords()

    def __str__(self):
        return '{0} {1}'.format(self.browser, self.version)

    def clean(self):
        super(Version, self).clean()
        VersionAndStatusValidator()(self)

    class Meta:
        order_with_respect_to = 'browser'


#
# Customized historical models and registration
#

class HistoricalBrowserRecords(HistoricalRecords):
    additional_fields = {
        'versions': JSONField(default=[])
    }

    def get_versions_value(self, instance, mtype):
        return list(
            instance.versions.values_list('pk', flat=True))


class HistoricalFeatureRecords(HistoricalRecords):
    additional_fields = {
        'references': JSONField(default=[]),
        'children': JSONField(default=[])
    }

    def get_references_value(self, instance, mtype):
        return list(
            instance.references.values_list('pk', flat=True))

    def get_children_value(self, instance, mtype):
        return list(
            instance.get_children().values_list('pk', flat=True))


class HistoricalMaturityRecords(HistoricalRecords):
    def get_meta_options(self, model):
        meta_fields = super(
            HistoricalMaturityRecords, self).get_meta_options(model)
        meta_fields['verbose_name_plural'] = 'historical_maturities'
        return meta_fields


class HistoricalSpecificationRecords(HistoricalRecords):
    additional_fields = {
        'sections': JSONField(default=[])
    }

    def get_sections_value(self, instance, mtype):
        return list(
            instance.sections.values_list('pk', flat=True))


register(Browser, records_class=HistoricalBrowserRecords)
register(Feature, records_class=HistoricalFeatureRecords)
register(Maturity, records_class=HistoricalMaturityRecords)
register(Specification, records_class=HistoricalSpecificationRecords)
