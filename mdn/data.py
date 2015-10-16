# coding: utf-8
"""Data lookup operations for MDN parsing."""
from __future__ import unicode_literals
from collections import namedtuple

from webplatformcompat.models import (
    Browser, Feature, Section, Specification, Support, Version)
from .utils import is_new_id, normalize_name, slugify


class Data(object):
    """
    Provide data operations for MDN parsing.

    Parsing an MDN page requires loading existing data for many purposes.
    This class loads the data and, if it can, caches the data.
    """

    def __init__(self):
        self.specifications = {}
        self.browser_data = None
        self.subfeature_data = {}

    BrowserParams = namedtuple(
        'BrowserParams', ['browser', 'browser_id', 'name', 'slug'])

    browser_name_fixes = {
        'Android': 'Android Browser',
        'BlackBerry': 'BlackBerry Browser',
        'Chrome': 'Chrome for Desktop',
        'Firefox (Gecko)': 'Firefox for Desktop',
        'Firefox Mobile (Gecko)': 'Firefox for Android',
        'Firefox Mobile': 'Firefox for Android',
        'Firefox OS (Gecko)': 'Firefox OS',
        'Firefox': 'Firefox for Desktop',
        'IE Mobile': 'Internet Explorer Mobile',
        'IE Phone': 'Internet Explorer Mobile',
        'IE': 'Internet Explorer for Desktop',
        'iOS Safari': 'Safari for iOS',
        'Internet Explorer': 'Internet Explorer for Desktop',
        'Opera': 'Opera for Desktop',
        'Opera (Presto)': 'Opera for Desktop',
        'Safari (WebKit)': 'Safari for Desktop',
        'Safari Mobile': 'Safari for iOS',
        'Safari': 'Safari for Desktop',
        'Windows Phone': 'Internet Explorer Mobile',
    }

    def lookup_browser_params(self, name, locale='en'):
        """Get or create the browser ID, name, and slug given a raw name.

        Return is a named tuple:
        * browser - A Browser if found, None if no existing browser
        * brower_id - The browser ID, prefixed with an underscore if new
        * name - The normalized name
        * slug - A unique slug for this browser
        """
        # Load existing browser data
        if self.browser_data is None:
            self.browser_data = {}
            for browser in Browser.objects.all():
                key = browser.name[locale]
                self.browser_data[key] = self.BrowserParams(
                    browser, browser.pk, key, browser.slug)

        # Expand to full name, handle common alternate names
        full_name = self.browser_name_fixes.get(name, name)

        # Select the Browser ID and slug
        if full_name not in self.browser_data:
            browser_id = '_' + full_name
            # TODO: unique slugify instead of browser_id
            self.browser_data[full_name] = self.BrowserParams(
                None, browser_id, full_name, browser_id)
        return self.browser_data[full_name]

    FeatureParams = namedtuple(
        'FeatureParams', ['feature', 'feature_id', 'slug'])

    def lookup_feature_params(self, parent_feature, name):
        """Get or create the feature ID and slug given a name.

        Return is a named tuple:
        * feature - A Feature if found, None if no existing feature
        * feature_id - The feature ID, prefixed with an underscore if new
        * slug - A unique slug for this feature
        """
        nname = normalize_name(name)

        # Treat "Basic Support" rows as parent feature
        if nname.lower() == 'basic support':
            return self.FeatureParams(
                parent_feature, parent_feature.id, parent_feature.slug)

        # Initialize subfeature data as needed
        if parent_feature.id not in self.subfeature_data:
            subfeatures = {}
            for feature in Feature.objects.filter(parent=parent_feature):
                if 'zxx' in feature.name:
                    fname = feature.name['zxx']
                else:
                    fname = feature.name['en']
                fname = normalize_name(fname)
                subfeatures[fname] = self.FeatureParams(
                    feature, feature.id, feature.slug)
            self.subfeature_data[parent_feature.id] = subfeatures

        # Select the Feature ID and slug
        subfeatures = self.subfeature_data[parent_feature.id]
        if nname not in subfeatures:
            feature_id = '_' + nname
            attempt = 0
            feature_slug = None
            while not feature_slug:
                base_slug = parent_feature.slug + '_' + nname
                feature_slug = slugify(base_slug, suffix=attempt)
                if Feature.objects.filter(slug=feature_slug).exists():
                    attempt += 1
                    feature_slug = ''
            subfeatures[nname] = self.FeatureParams(
                None, feature_id, feature_slug)

        return self.subfeature_data[parent_feature.id][nname]

    def lookup_section_id(self, spec_id, subpath, locale='en'):
        """Retrieve a section ID given a Specification ID and subpath."""
        for section in Section.objects.filter(specification_id=spec_id):
            if section.subpath.get(locale) == subpath:
                return section.id
        return None

    def lookup_specification(self, mdn_key):
        """Retrieve a Specification by key."""
        if mdn_key not in self.specifications:
            try:
                spec = Specification.objects.get(mdn_key=mdn_key)
            except Specification.DoesNotExist:
                spec = None
            self.specifications[mdn_key] = spec
        return self.specifications[mdn_key]

    def lookup_support_id(self, version_id, feature_id):
        """Lookup or create a support ID for a version and feature."""
        support = None
        real_version = not is_new_id(version_id)
        real_feature = not is_new_id(feature_id)
        if real_version and real_feature:
            # Might be known version
            try:
                support = Support.objects.get(
                    version=version_id, feature=feature_id)
            except Support.DoesNotExist:
                pass
        if support:
            # Known support
            support_id = support.id
        else:
            # New support
            support_id = "_%s-%s" % (feature_id, version_id)
        return support_id

    VersionParams = namedtuple("VersionParams", ["version", "version_id"])

    def lookup_version_params(
            self, browser_id, browser_name, version_name):
        """Get or create the version ID and normalized name by version string.

        Keyword Arguments:
        * browser_id - The ID of an existing browser, or a underscore-prefixed
            string for a new browser.
        * browser_name - The name of the browser
        * version_name - The version string, such as 1.0, 'current', or
            'nightly'

        Return is a named tuple:
        * version - A Version if found, None if no existing version
        * version_id - The version ID, prefixed with an underscore if new
        """
        version = None
        if not is_new_id(browser_id):
            # Might be known version
            try:
                version = Version.objects.get(
                    browser=browser_id, version=version_name)
            except Version.DoesNotExist:
                pass
        if version:
            # Known version
            version_id = version.id
        else:
            # New version
            version_id = "_%s-%s" % (browser_name, version_name)

        return self.VersionParams(version, version_id)
