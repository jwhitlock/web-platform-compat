# coding: utf-8
"""Test mdn.data"""
from __future__ import unicode_literals

from mdn.data import Data
from webplatformcompat.models import Feature, Support
from .base import TestCase


class TestDataBase(TestCase):
    def setUp(self):
        self.data = Data()


class TestLookupBrowserParams(TestDataBase):
    def assert_browser_params(self, raw_name, browser, b_id, name, slug):
        params = self.data.lookup_browser_params(raw_name)
        self.assertEqual(params.browser, browser)
        self.assertEqual(params.browser_id, b_id)
        self.assertEqual(params.name, name)
        self.assertEqual(params.slug, slug)
        with self.assertNumQueries(0):
            new_params = self.data.lookup_browser_params(raw_name)
        self.assertEqual(params, new_params)

    def test_browser_params_new_browser(self):
        self.assert_browser_params(
            'Safari', None, '_Safari for Desktop', 'Safari for Desktop',
            '_Safari for Desktop')

    def test_browser_params_match(self):
        match = self.get_instance('Browser', 'firefox_desktop')
        self.assert_browser_params(
            'Firefox', match, match.id, 'Firefox for Desktop',
            'firefox_desktop')


class TestLookupFeatureParams(TestDataBase):
    def setUp(self):
        super(TestLookupFeatureParams, self).setUp()
        self.parent = self.get_instance('Feature', 'web-css-background-size')

    def assert_feature_params(self, name, feature, f_id, slug):
        params = self.data.lookup_feature_params(self.parent, name)
        self.assertEqual(params.feature, feature)
        self.assertEqual(params.feature_id, f_id)
        self.assertEqual(params.slug, slug)
        with self.assertNumQueries(0):
            new_params = self.data.lookup_feature_params(self.parent, name)
        self.assertEqual(params, new_params)

    def test_feature_params_basic_support(self):
        self.assert_feature_params(
            'Basic Support', self.parent, self.parent.id,
            'web-css-background-size')

    def test_feature_params_new(self):
        self.assert_feature_params(
            'Row Feature', None, '_row feature',
            'web-css-background-size_row_feature')

    def test_feature_params_match(self):
        match = self.get_instance(
            'Feature', 'web-css-background-size-contain_and_cover')
        self.assert_feature_params(
            match.name['en'], match, match.id, match.slug)

    def test_feature_params_match_canonical(self):
        match = self.create(
            Feature, parent=self.parent, name={'zxx': 'list-item'},
            slug='wcb-list-item')
        self.assert_feature_params(
            'list-item', match, match.id, match.slug)

    def test_feature_params_slug_collision(self):
        self.create(Feature, slug='web-css-background-size_slug')
        self.assert_feature_params(
            'slug', None, '_slug', 'web-css-background-size_slug1')


class TestLookupSpecification(TestDataBase):
    def assert_specification(self, key, expected):
        with self.assertNumQueries(1):
            self.assertEqual(self.data.lookup_specification(key), expected)
        with self.assertNumQueries(0):
            self.assertEqual(self.data.lookup_specification(key), expected)

    def test_missing(self):
        self.assert_specification('NoSpec', None)

    def test_found(self):
        spec = self.get_instance('Specification', 'css3_backgrounds')
        self.assert_specification(spec.mdn_key, spec)


class TestLookupSectionId(TestDataBase):
    def setUp(self):
        super(TestLookupSectionId, self).setUp()
        self.spec = self.get_instance('Specification', 'css3_backgrounds')

    def test_not_found(self):
        self.assertIsNone(
            self.data.lookup_section_id(self.spec.id, "#the-background-size"))

    def test_found(self):
        section = self.get_instance('Section', 'background-size')
        section_id = self.data.lookup_section_id(
            self.spec.id, "#the-background-size")
        self.assertEqual(section_id, section.id)

    def test_not_found_but_others(self):
        self.get_instance('Section', 'background-size')
        self.assertIsNone(self.data.lookup_section_id(self.spec.id, "#other"))


class TestLookupSupportId(TestDataBase):
    def setUp(self):
        super(TestLookupSupportId, self).setUp()
        self.version = self.get_instance(
            'Version', ('firefox_desktop', 'current'))
        self.feature = self.get_instance(
            'Feature', 'web-css-background-size-contain_and_cover')

    def assert_new_support_id(self, version_id, feature_id):
        support_id = self.data.lookup_support_id(version_id, feature_id)
        expected_support_id = '_{}-{}'.format(feature_id, version_id)
        self.assertEqual(expected_support_id, support_id)

    def test_all_new(self):
        self.assert_new_support_id('_version', '_feature')

    def test_real_version(self):
        self.assert_new_support_id(self.version.id, '_feature')

    def test_real_feature(self):
        self.assert_new_support_id('_version', self.feature.id)

    def test_not_found(self):
        self.assert_new_support_id(self.version.id, self.feature.id)

    def test_found(self):
        support = self.create(
            Support, version=self.version, feature=self.feature)
        support_id = self.data.lookup_support_id(
            self.version.id, self.feature.id)
        self.assertEqual(support.id, support_id)


class TestLookupVersionParams(TestDataBase):
    def setUp(self):
        super(TestLookupVersionParams, self).setUp()
        self.browser = self.get_instance('Browser', 'firefox_desktop')

    def test_new_browser(self):
        params = self.data.lookup_version_params('_browser', 'Browser', '1.0')
        self.assertIsNone(params.version)
        self.assertEqual('_Browser-1.0', params.version_id)

    def test_new_version(self):
        params = self.data.lookup_version_params(
            self.browser.id, self.browser.name['en'], '1.0')
        self.assertIsNone(params.version)
        self.assertEqual('_Firefox for Desktop-1.0', params.version_id)

    def test_existing_version(self):
        version = self.get_instance('Version', ('firefox_desktop', 'current'))
        params = self.data.lookup_version_params(
            self.browser.id, self.browser.name['en'], 'current')
        self.assertEqual(version, params.version)
        self.assertEqual(version.id, params.version_id)
