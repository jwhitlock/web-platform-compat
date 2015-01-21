# -*- coding: utf-8 -*-
"""Model definitions for MDN migration app."""

from __future__ import unicode_literals
from collections import OrderedDict
from json import dumps, loads

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.html import escape
from django.utils.six.moves.urllib_parse import urlparse
from django.utils.timesince import timesince
from django_extensions.db.fields import ModificationDateTimeField

from webplatformcompat.models import Feature


def validate_mdn_url(value):
    """Validate than a URL is an acceptable MDN URL."""
    disallowed_chars = '?$#'
    for c in disallowed_chars:
        if c in value:
            raise ValidationError('"?" is not allowed in URL')
    allowed_prefix = False
    for allowed in settings.MDN_ALLOWED_URLS:
        allowed_prefix = allowed_prefix or value.startswith(allowed)
    if not allowed_prefix:
        raise ValidationError(
            '%s does not start with an allowed URL prefix' % value)


@python_2_unicode_compatible
class FeaturePage(models.Model):
    """A page on MDN describing a feature."""
    url = models.URLField(
        help_text="URL of the English translation of an MDN page",
        db_index=True, unique=True, validators=[validate_mdn_url])
    feature = models.ForeignKey(
        Feature, help_text="Feature in API", unique=True)

    STATUS_STARTING = 0
    STATUS_META = 1
    STATUS_PAGES = 2
    STATUS_PARSING = 3
    STATUS_PARSED = 4
    STATUS_ERROR = 5
    STATUS_CHOICES = (
        (STATUS_STARTING, "Starting Import"),
        (STATUS_META, "Fetching Metadata"),
        (STATUS_PAGES, "Fetching MDN pages"),
        (STATUS_PARSING, "Parsing MDN pages"),
        (STATUS_PARSED, "Parsing Complete"),
        (STATUS_ERROR, "Scraping Failed"),
    )
    status = models.IntegerField(
        help_text="Status of MDN Parsing process",
        default=STATUS_STARTING, choices=STATUS_CHOICES)
    modified = ModificationDateTimeField(
        help_text="Last modification time", db_index=True)
    raw_data = models.TextField(help_text="JSON-encoded parsed content")
    has_issues = models.BooleanField(
        help_text="Issues found when parsing the page", default=False)

    def __str__(self):
        return "%s for %s" % (self.get_status_display(), self.slug())

    def domain(self):
        """Protocol + domain portion of URL"""
        url_bits = urlparse(self.url)
        return "%s://%s" % (url_bits.scheme, url_bits.netloc)

    def path(self):
        """Path portion of URL"""
        return urlparse(self.url).path

    def slug(self):
        path = self.path()
        prefix = '/en-US/docs/'
        assert path.startswith(prefix)
        return path[len(prefix):]

    def same_since(self):
        """Return a string indicating when the object was changes"""
        return timesince(self.modified) + " ago"

    def meta(self):
        """Get the page Meta section."""
        meta, created = self.pagemeta_set.get_or_create(defaults={
            'path': self.path() + '$json',
            'raw': '',
            'status': Content.STATUS_STARTING})
        return meta

    def translations(self):
        """Get the page translations, after fetching the meta data."""
        meta = self.meta()
        translations = []
        for locale, path in meta.locale_paths():
            content, created = self.translatedcontent_set.get_or_create(
                locale=locale, defaults={
                    'path': path,
                    'raw': '',
                    'status': TranslatedContent.STATUS_STARTING})
            translations.append(content)
        return translations

    def reset(self, delete_cache=True):
        """Reset to initial state

        drop_cache - Delete cached MDN content
        """
        self.status = FeaturePage.STATUS_STARTING
        self.reset_data()
        self.save()
        meta = self.meta()
        meta.status = meta.STATUS_STARTING
        meta.save()
        for t in self.translatedcontent_set.all():
            if delete_cache or (t.status == t.STATUS_ERROR):
                t.status = t.STATUS_STARTING
                t.raw = ""
                t.save()

    def reset_data(self):
        """Reset JSON data to initial state"""
        feature = OrderedDict((
            ('id', str(self.feature.id)),
            ('slug', self.feature.slug),
            ('mdn_uri', OrderedDict((('en', self.url),))),
            ('experimental', self.feature.experimental),
            ('standardized', self.feature.standardized),
            ('stable', self.feature.stable),
            ('obsolete', self.feature.obsolete),
            ('name', self.feature.name),
            ('links', OrderedDict((
                ('sections', []),
                ('supports', []),
                ('parent', str(self.feature.parent_id)),
                ('children', []),
            )))))
        view_feature = OrderedDict((
            ('features', feature),
            ('linked', OrderedDict((
                ('browsers', []),
                ('versions', []),
                ('supports', []),
                ('maturities', []),
                ('specifications', []),
                ('sections', []),
                ('features', []),
            ))),
            ('meta', OrderedDict((
                ("compat_table", OrderedDict((
                    ("supports", OrderedDict()),
                    ("tabs", []),
                    ("pagination", OrderedDict()),
                    ("languages", []),
                    ("footnotes", OrderedDict()),
                ))),
                ("scrape", OrderedDict((
                    ("phase", "Starting Import"),
                    ("errors", []),
                    ("raw", None)))))))))
        self.data = view_feature
        self.has_issues = False
        return view_feature

    @property
    def data(self):
        """Scraped data in JSON-API format."""
        try:
            data = loads(self.raw_data, object_pairs_hook=OrderedDict)
        except (ValueError, TypeError):
            data = {}
        if not data:
            data = self.reset_data()
        return data

    @data.setter
    def data(self, value):
        """Serialize the data for storage"""
        self.raw_data = dumps(value, indent=2)

    def add_error(self, error, safe=False):
        """Add an error to the JSON data"""
        data = self.data
        errors = data['meta']['scrape']['errors']
        if safe:
            err = error
        else:
            err = '<pre>%s</pre>' % escape(error)
        if err not in errors:
            errors.append(err)
        self.data = data
        self.has_issues = True

    @models.permalink
    def get_absolute_url(self):
        return ('mdn.views.feature_page_detail', [str(self.id)])


@python_2_unicode_compatible
class Content(models.Model):
    """The content of an MDN page."""
    page = models.ForeignKey(FeaturePage)
    path = models.CharField(help_text="Path of MDN page", max_length=255)
    crawled = ModificationDateTimeField(
        help_text="Time when the content was retrieved")
    raw = models.TextField(help_text="Raw content of the page")
    STATUS_STARTING = 0
    STATUS_FETCHING = 1
    STATUS_FETCHED = 2
    STATUS_ERROR = 3
    STATUS_CHOICES = (
        (STATUS_STARTING, "Starting Fetch"),
        (STATUS_FETCHING, "Fetching Page"),
        (STATUS_FETCHED, "Fetched Page"),
        (STATUS_ERROR, "Error Fetching Page"),
    )
    status = models.IntegerField(
        help_text="Status of MDN fetching process",
        default=STATUS_STARTING, choices=STATUS_CHOICES)

    class Meta:
        abstract = True

    def url(self):
        return self.page.domain() + self.path

    def __str__(self):
        return "%s retrieved %s ago" % (self.path, timesince(self.crawled))


class PageMeta(Content):
    """The metadata for a page, retrieved by adding $json to the URL."""

    def data(self):
        """Get the metdata for the page"""
        assert self.status == self.STATUS_FETCHED
        return loads(self.raw)

    def locale_paths(self):
        """Get the locals and their paths.

        If the meta section isn't fetched, will return an empty list.
        """
        if self.status != self.STATUS_FETCHED:
            return []
        meta = self.data()
        locale_paths = [(meta['locale'], meta['url'])]
        for t in meta['translations']:
            locale_paths.append((t['locale'], t['url']))
        return locale_paths


class TranslatedContent(Content):
    """The raw translated content of a MDN feature page."""
    locale = models.CharField(
        help_text="Locale for page translation",
        max_length=5, db_index=True)
