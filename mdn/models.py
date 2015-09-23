# -*- coding: utf-8 -*-
"""Model definitions for MDN migration app."""

from __future__ import unicode_literals
from collections import OrderedDict
from json import dumps, loads

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.encoding import python_2_unicode_compatible
from django.utils.functional import cached_property
from django.utils.six import text_type
from django.utils.six.moves import zip
from django.utils.six.moves.urllib_parse import urlparse
from django.utils.timesince import timesince
from django_extensions.db.fields.json import JSONField

from webplatformcompat.models import Feature
from .issues import ISSUES, SEVERITIES, UNKNOWN_ISSUE, WARNING, ERROR, CRITICAL


def validate_mdn_url(value):
    """Validate than a URL is an acceptable MDN URL."""
    disallowed_chars = '?$#'
    for c in disallowed_chars:
        if c in value:
            raise ValidationError('"{}" is not allowed in URL'.format(c))
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
    STATUS_NO_DATA = 6
    STATUS_PARSED_WARNING = 7
    STATUS_PARSED_ERROR = 8
    STATUS_PARSED_CRITICAL = 9
    STATUS_CHOICES = (
        (STATUS_STARTING, "Starting Import"),
        (STATUS_META, "Fetching Metadata"),
        (STATUS_PAGES, "Fetching MDN pages"),
        (STATUS_PARSING, "Parsing MDN pages"),
        (STATUS_PARSED, "Parsing Complete"),
        (STATUS_ERROR, "Scraping Failed"),
        (STATUS_NO_DATA, "No Compat Data"),
        (STATUS_PARSED_WARNING, "Has Warnings"),
        (STATUS_PARSED_ERROR, "Has Errors"),
        (STATUS_PARSED_CRITICAL, "Has Critical Errors"),
    )
    status = models.IntegerField(
        help_text="Status of MDN Parsing process",
        default=STATUS_STARTING, choices=STATUS_CHOICES)
    modified = models.DateTimeField(
        help_text="Last modification time", db_index=True, auto_now=True)
    raw_data = models.TextField(help_text="JSON-encoded parsed content")

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
        prefix = '/en-US/'
        assert path.startswith(prefix)
        return path[len(prefix):]

    def same_since(self):
        """Return a string indicating when the object was changes"""
        return timesince(self.modified or timezone.now()) + " ago"

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
        for locale, path, title in meta.locale_paths():
            content, created = self.translatedcontent_set.get_or_create(
                locale=locale, defaults={
                    'path': path, 'raw': '', 'title': title,
                    'status': TranslatedContent.STATUS_STARTING})
            if content.title != title or content.path != path:
                content.path = path
                content.title = title
                content.save()
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

    def reset_data(self, keep_issues=False):
        """Reset JSON data to initial state.

        If keep_issues is False (default), issues are dropped. If true, then
        issues are added to meta.scrape.issues.
        """
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
        canonical = (list(feature['name'].keys()) == ['zxx'])
        if canonical:
            feature['name'] = feature['name']['zxx']
        for t in self.translations():
            if t.locale != 'en-US':
                feature['mdn_uri'][t.locale] = t.url()
                if not canonical:
                    feature['name'][t.locale] = t.title

        issues = []
        if keep_issues:
            for issue in self.issues.order_by('id'):
                issue_plus = [issue.slug, issue.start, issue.end, issue.params]
                if issue.content:
                    issue_plus.append(issue.content.locale)
                else:
                    issue_plus.append(None)
                issues.append(issue_plus)
        else:
            self.issues.all().delete()

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
                    ("notes", OrderedDict()),
                ))),
                ("scrape", OrderedDict((
                    ("phase", "Starting Import"),
                    ("issues", issues),
                    ("raw", None)))))))))

        self.data = view_feature
        return view_feature

    @property
    def data(self):
        """Scraped data in JSON-API format."""
        try:
            data = loads(self.raw_data, object_pairs_hook=OrderedDict)
        except (ValueError, TypeError):
            data = {}
        if not data:
            data = self.reset_data(keep_issues=True)

        return data

    @data.setter
    def data(self, value):
        """Serialize the data for storage"""
        self.raw_data = dumps(value, indent=2)

    @property
    def has_issues(self):
        return bool(sum(self.issue_counts.values()))

    @cached_property
    def issue_counts(self):
        counts = {WARNING: 0, ERROR: 0, CRITICAL: 0}
        issues = self.data['meta']['scrape']['issues']
        if not issues:
            # Legacy - get from raw data
            raw = self.data['meta']['scrape']['raw'] or {}
            issues = raw.get('issues', [])
        for issue in issues:
            slug = issue[0]
            severity = ISSUES.get(slug, UNKNOWN_ISSUE)[0]
            counts[severity] += 1
        return counts

    @property
    def warnings(self):
        return self.issue_counts[WARNING]

    @property
    def errors(self):
        return self.issue_counts[ERROR]

    @property
    def critical(self):
        return self.issue_counts[CRITICAL]

    def add_issue(self, issue, locale=None):
        """Add an issue to the page."""
        slug, start, end, params = issue
        if locale:
            content = self.translatedcontent_set.get(locale=locale)
        else:
            content = None

        # Did we already add this issue?
        if self.issues.filter(slug=slug, start=start, end=end).exists():
            raise ValueError("Duplicate issue")

        # Add issue to database, data
        data = self.data
        self.issues.create(
            slug=slug, start=start, end=end, params=params, content=content)
        issue_plus = list(issue)
        issue_plus.append(locale)
        data['meta']['scrape']['issues'].append(issue_plus)
        self.data = data
        try:
            del self.issue_counts
        except AttributeError:
            pass  # Wasn't cached yet

    @models.permalink
    def get_absolute_url(self):
        return ('mdn.views.feature_page_detail', [str(self.id)])

    @property
    def is_parsed(self):
        return self.status in (
            self.STATUS_PARSED,
            self.STATUS_PARSED_WARNING,
            self.STATUS_PARSED_ERROR,
            self.STATUS_PARSED_CRITICAL,
            self.STATUS_NO_DATA)


@python_2_unicode_compatible
class Issue(models.Model):
    """An issue on a FeaturePage."""
    page = models.ForeignKey(FeaturePage, related_name='issues')
    slug = models.SlugField(
        help_text="Human-friendly slug for issue.",
        choices=[(slug, slug) for slug in sorted(ISSUES.keys())])
    start = models.IntegerField(
        help_text="Start position in source text")
    end = models.IntegerField(
        help_text="End position in source text")
    params = JSONField(
        help_text="Parameters for description templates")
    content = models.ForeignKey(
        'TranslatedContent', null=True, blank=True,
        help_text="Content the issue was found on")

    def __str__(self):
        if self.content:
            url = self.content.url()
        else:
            url = self.page.url
        return "{slug} [{start}:{end}] on {url}".format(
            slug=self.slug, start=self.start, end=self.end, url=url)

    @property
    def severity(self):
        return ISSUES.get(self.slug, UNKNOWN_ISSUE)[0]

    @property
    def brief_description(self):
        return ISSUES.get(self.slug, UNKNOWN_ISSUE)[1].format(**self.params)

    @property
    def long_description(self):
        return ISSUES.get(self.slug, UNKNOWN_ISSUE)[2].format(**self.params)

    @property
    def context(self):
        if not self.content:
            return ''

        raw = self.content.raw
        if not raw.endswith('\n'):
            raw += '\n'
        start_line = raw.count('\n', 0, self.start)
        end_line = raw.count('\n', 0, self.end)
        ctx_start_line = max(0, start_line - 2)
        ctx_end_line = min(end_line + 3, raw.count('\n'))
        digits = len(text_type(ctx_end_line))
        context_lines = raw.split('\n')[ctx_start_line:ctx_end_line]

        # Highlight the errored portion
        err_page_bits = []
        err_line_count = 1
        for p, c in enumerate(raw):  # pragma: no branch
            if c == '\n':
                err_page_bits.append(c)
                err_line_count += 1
                if err_line_count > ctx_end_line:
                    break
            elif p < self.start or p >= self.end:
                err_page_bits.append(' ')
            else:
                err_page_bits.append('^')
        err_page = ''.join(err_page_bits)
        err_lines = err_page.split('\n')[ctx_start_line:ctx_end_line]

        out = []
        for num, (line, err_line) in enumerate(zip(context_lines, err_lines)):
            lnum = ctx_start_line + num + 1
            out.append(
                text_type(lnum).rjust(digits) + ' ' + line)
            if '^' in err_line:
                out.append('*' * digits + ' ' + err_line)

        return '\n'.join(out)

    def get_severity_display(self):
        return SEVERITIES[self.severity]


@python_2_unicode_compatible
class Content(models.Model):
    """The content of an MDN page."""
    page = models.ForeignKey(FeaturePage)
    path = models.CharField(help_text="Path of MDN page", max_length=1024)
    crawled = models.DateTimeField(
        help_text="Time when the content was retrieved", auto_now=True)
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
        return "%s retrieved %s ago" % (
            self.path, timesince(self.crawled or timezone.now()))


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
        locale_paths = [(meta['locale'], meta['url'], meta['title'])]
        for t in meta['translations']:
            locale_paths.append((t['locale'], t['url'], t['title']))
        return locale_paths


class TranslatedContent(Content):
    """The raw translated content of a MDN feature page."""
    locale = models.CharField(
        help_text="Locale for page translation",
        max_length=5, db_index=True)
    title = models.TextField(help_text="Page title in locale", blank=True)
