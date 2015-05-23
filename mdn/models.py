# -*- coding: utf-8 -*-
"""Model definitions for MDN migration app."""

from __future__ import unicode_literals
from collections import OrderedDict
from json import dumps, loads

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.six import text_type
from django.utils.six.moves.urllib_parse import urlparse
from django.utils.timesince import timesince
from django_extensions.db.fields import ModificationDateTimeField
from django_extensions.db.fields.json import JSONField

from webplatformcompat.models import Feature


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
    STATUS_CHOICES = (
        (STATUS_STARTING, "Starting Import"),
        (STATUS_META, "Fetching Metadata"),
        (STATUS_PAGES, "Fetching MDN pages"),
        (STATUS_PARSING, "Parsing MDN pages"),
        (STATUS_PARSED, "Parsing Complete"),
        (STATUS_ERROR, "Scraping Failed"),
        (STATUS_NO_DATA, "No Compat Data"),
    )
    status = models.IntegerField(
        help_text="Status of MDN Parsing process",
        default=STATUS_STARTING, choices=STATUS_CHOICES)
    modified = ModificationDateTimeField(
        help_text="Last modification time", db_index=True)
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
        self.issues.all().delete()
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
        canonical = (list(feature['name'].keys()) == ['zxx'])
        if canonical:
            feature['name'] = feature['name']['zxx']
        for t in self.translations():
            if t.locale != 'en-US':
                feature['mdn_uri'][t.locale] = t.url()
                if not canonical:
                    feature['name'][t.locale] = t.title

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
                    ("issues", []),
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
            data = self.reset_data()

        # Add issues
        issues = []
        for issue in self.issues.order_by('id'):
            issues.append([
                issue.slug, issue.start, issue.end, issue.params])
        data['meta']['scrape']['issues'] = issues

        return data

    @data.setter
    def data(self, value):
        """Serialize the data for storage"""
        self.raw_data = dumps(value, indent=2)

    @property
    def has_issues(self):
        return self.issues.exists()

    @property
    def issue_counts(self):
        if not getattr(self, '_issue_counts', None):
            self._issue_counts = {WARNING: 0, ERROR: 0, CRITICAL: 0}
            for issue in self.issues.all():
                self._issue_counts[issue.severity] += 1
        return self._issue_counts

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
        self.issues.create(
            slug=slug, start=start, end=end, params=params, content=content)
        self._issue_counts = None

    @models.permalink
    def get_absolute_url(self):
        return ('mdn.views.feature_page_detail', [str(self.id)])

# Issue severity
WARNING = 1
ERROR = 2
CRITICAL = 3
SEVERITIES = {
    WARNING: 'Warning',
    ERROR: 'Error',
    CRITICAL: 'Critical',
}

# Issue slugs, severity, brief templates, and long templates
# This was a database model, but it was cumbersome to update text with a
#  database migration, and changing slugs require code changes as well.
ISSUES = {
    'bad_json': (
        CRITICAL,
        'Response from {url} is not JSON',
        'Actual content:\n{content}'),
    'compatgeckodesktop_unknown': (
        ERROR,
        'Unknown Gecko version "{version}"',
        'The importer does not recognize this version for CompatGeckoDesktop.'
        ' Change the MDN page or update the importer.'),
    'compatgeckofxos_override': (
        ERROR,
        'Override "{override}" is invalid for Gecko version "{version}".',
        'The importer does not recognize this override for CompatGeckoFxOS.'
        ' Change the MDN page or update the importer.'),
    'compatgeckofxos_unknown': (
        ERROR,
        'Unknown Gecko version "{version}"',
        'The importer does not recognize this version for CompatGeckoFxOS.'
        ' Change the MDN page or update the importer.'),
    'doc_parse_error': (
        CRITICAL,
        'No imported data due to unexpected page structure.',
        'The importer was unable to handle the page structure enough to'
        ' determine if there was compatibility data.'),
    'exception': (CRITICAL, 'Unhandled exception', '{traceback}'),
    'extra_cell': (
        ERROR,
        'Extra cell in compatibility table row.',
        'A row in the compatibility table has more cells than the header'
        ' row. It may be the cell identified in the context, a different'
        ' cell in the row, or a missing header cell.'),
    'failed_download': (
        CRITICAL, 'Failed to download {url}.',
        'Status {status}, Content:\n{content}'),
    'false_start': (
        CRITICAL,
        'No <h2> found in page.',
        'A compatibility table must be after a proper <h2> to be imported.'),
    'feature_header': (
        WARNING,
        'Expected first header to be "Feature"',
        'The first header is "{header}", not "Feature"'),
    'footnote_feature': (
        ERROR,
        'Footnotes are not allowed on features',
        'The Feature model does not include a notes field. Remove the'
        ' footnote from the feature.'),
    'footnote_missing': (
        ERROR,
        'Footnote [{footnote_id}] not found.',
        'The compatibility table has a reference to footnote'
        ' "{footnote_id}", but no matching footnote was found. This may'
        ' be due to parse issues in the footnotes section, a typo in the MDN'
        ' page, or a footnote that was removed without removing the footnote'
        ' reference from the table.'),
    'footnote_multiple': (
        ERROR,
        'Only one footnote allowed per compatibility cell.',
        'The API supports only one footnote per support assertion. Combine'
        ' footnotes [{prev_footnote_id}] and [{footnote_id}], or remove'
        ' one of them.'),
    'footnote_no_id': (
        ERROR,
        'Footnote has no ID.',
        'Footnote references, such as [1], are used to link the footnote to'
        ' the support assertion in the compatibility table. Reformat the MDN'
        ' page to use footnote references.'),
    'footnote_unused': (
        ERROR,
        'Footnote [{footnote_id}] is unused.',
        'No cells in the compatibility table included the footnote reference'
        ' [{footnote_id}]. This could be due to a issue importing the'
        ' compatibility cell, a typo on the MDN page, or an extra footnote'
        ' that should be removed from the MDN page.'),
    'halt_import': (
        CRITICAL,
        'Unable to finish importing MDN page.',
        'The importer was unable to finish parsing the MDN page. This may be'
        ' due to a duplicated section, or other unexpected content.'),
    'inline_text': (
        ERROR,
        'Unknown inline support text "{text}".',
        'The API schema does not include inline notes. This text needs to be'
        ' converted to a footnote, converted to a support attribute (which'
        ' may require an importer update), or removed.'),
    'nested_p': (
        ERROR,
        'Nested <p> tags are not supported.',
        'Edit the MDN page to remove the nested <p> tag'),
    'section_skipped': (
        CRITICAL,
        'Section <h2>{title}</h2> has unexpected content.',
        'The parser was trying to match rule "{rule_name}", but was unable to'
        ' understand some unexpected content. This may be markup or'
        ' text, or a side-effect of previous issues. Look closely at the'
        ' context (as well as any previous issues) to find the problem'
        ' content.'),
    'section_missed': (
        CRITICAL,
        'Section <h2>{title}</h2> was not imported.',
        'The import of section {title} failed, but no parse error was'
        ' detected. This is usually because of a previous critical error,'
        ' which must be cleared before any parsing can be attempted.'),
    'spec_h2_id': (
        WARNING,
        'Expected <h2 id="Specifications">, actual id={h2_id}',
        'Fix the id so that the table of contents, other feature work.'),
    'spec_h2_name': (
        WARNING,
        'Expected <h2 name="Specifications">, actual name={h2_name}',
        'Fix or remove the name attribute.'),
    'spec_mismatch': (
        ERROR,
        'SpecName({specname_key}, ...) does not match'
        ' Spec2({spec2_key}).',
        'SpecName and Spec2 must refer to the same mdn_key. Update the MDN'
        ' page.'),
    'specname_blank_key': (
        ERROR,
        'KumaScript SpecName has a blank key',
        'Update the MDN page to include a valid mdn_key'),
    'spec2_wrong_kumascript': (
        ERROR,
        'Expected KumaScript Spec2(), got {kumascript}',
        'Change to Spec2(mdn_key), using the mdn_key from the SpecName()'
        ' KumaScript.'),
    'spec2_arg_count': (
        ERROR,
        'KumaScript {kumascript} should have 1 non-blank argument',
        'Argument should be the MDN key that will return a maturity'),
    'unexpected_attribute': (
        WARNING,
        'Unexpected attribute <{node_type} {ident}="{value}">',
        'For <{node_type}>, the importer is ready for the attributes'
        ' {expected}. This unexpected attribute will be discarded.'),
    'unknown_browser': (
        ERROR,
        'Unknown Browser "{name}".',
        'The API does not have a browser with the name "{name}".'
        ' This could be a typo on the MDN page, or the browser needs to'
        ' be added to the API.'),
    'unknown_kumascript': (
        ERROR,
        'Unknown KumaScript {kumascript} in {scope}.',
        'The importer has to run custom code to import KumaScript, and it'
        ' hasn\'t been taught how to import {name} when it appears in a'
        ' {scope}. File a bug, or convert the MDN page to not use this'
        ' KumaScript macro.'),
    'unknown_spec': (
        ERROR,
        'Unknown Specification "{key}".',
        'The API does not have a specification with mdn_key "{key}".'
        ' This could be a typo on the MDN page, or the specification needs to'
        ' be added to the API.'),
    'unknown_version': (
        ERROR,
        'Unknown version "{version}" for browser "{browser_name}"',
        'The API does not have the version "{version}" for browser'
        ' "{browser_name}" (id {browser_id}, slug "{browser_slug}").'
        ' This could be a typo on the MDN page, or the version needs to'
        ' be added to the API.'),
}


@python_2_unicode_compatible
class Issue(models.Model):
    """An issue on a FeaturePage."""
    page = models.ForeignKey(FeaturePage, related_name='issues')
    slug = models.SlugField(
        help_text="Human-friendly slug for issue.",
        choices=[(slug, slug) for slug in ISSUES])
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
        return ISSUES[self.slug][0]

    @property
    def brief_description(self):
        return ISSUES[self.slug][1].format(**self.params)

    @property
    def long_description(self):
        return ISSUES[self.slug][2].format(**self.params)

    @property
    def context(self):
        if not self.content:
            return ''

        raw = self.content.raw
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
            lnum = ctx_start_line + num
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
