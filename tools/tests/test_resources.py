#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for `web-platform-compat` fields module."""
from __future__ import unicode_literals
from unittest import TestCase as BaseTestCase

from collections import OrderedDict
import mock

from tools.client import Client
from tools.resources import (
    Browser, Collection, CollectionChangeset, Feature, Maturity, Section,
    Specification, Support, Version, Link, LinkList)


class TestCase(BaseTestCase):
    maxDiff = None


class TestLink(TestCase):

    """Test the Link resource."""

    def test_link_without_collection(self):
        link = Link(None, 'browsers', '1')
        self.assertEqual(link.id, '1')

    def test_null_link(self):
        link = Link(None, 'browsers')
        self.assertIsInstance(link.linked_id, Link.NoId)
        self.assertIsNone(link.id)

    def test_link_without_collection_or_id(self):
        link = Link(None, 'browsers')
        self.assertEqual(link.id, None)

    def test_link_with_collection(self):
        collection = Collection()
        link = Link(collection, 'browsers', '1')
        self.assertEqual(link.id, '1')
        collection._override_ids = {'browsers': {'1': '_browser1'}}
        self.assertEqual(link.id, '_browser1')

    def test_null_link_with_collection(self):
        collection = Collection()
        link = Link(collection, 'browsers')
        self.assertIsNone(link.id)


class TestBrowser(TestCase):

    """Test the Browser resource, and general Resource functions."""

    def test_load_at_init(self):
        browser = Browser(slug='browser')
        self.assertEqual('browser', browser.slug)

    def test_load_by_attribute(self):
        browser = Browser()
        browser.id = "6"
        self.assertIsInstance(browser.id, Link)
        self.assertEqual("6", browser.id.id)

    def test_missing_attribute(self):
        raised = False
        browser = Browser()
        try:
            browser.missing_attribute
        except AttributeError:
            raised = True
        self.assertTrue(raised)

    def test_from_json_api(self):
        rep = {
            "browsers": {
                "id": "1",
                "slug": "chrome",
                "name": {"en": "Chrome"},
                "note": None,
                "links": {
                    "history": ["1"],
                    "history_current": "1",
                    "versions": ["1"],
                }
            },
            "links": {
                "browsers.history": {
                    "href": (
                        "http://example.com/api/v1/historical_browsers/"
                        "{browsers.history}"),
                    "type": "historical_browsers"
                },
                "browsers.history_current": {
                    "href": (
                        "http://localhost:8000/api/v1/historical_browsers/"
                        "{browsers.history_current}"),
                    "type": "historical_browsers"
                },
                "browsers.versions": {
                    "href": (
                        "http://localhost:8000/api/v1/versions/"
                        "{browsers.versions}"),
                    "type": "versions"
                }
            }
        }
        browser = Browser()
        self.assertIsNone(browser.id)
        self.assertIsNone(browser.slug)
        self.assertIsNone(browser.name)
        self.assertIsNone(browser.note)
        self.assertIsNone(browser.history)
        self.assertIsNone(browser.history_current)
        self.assertIsNone(browser.versions)

        browser.from_json_api(rep)
        self.assertIsInstance(browser.id, Link)
        self.assertEqual("1", browser.id.id)
        self.assertEqual("chrome", browser.slug)
        self.assertEqual({'en': 'Chrome'}, browser.name)
        self.assertIsNone(browser.note)
        self.assertIsInstance(browser.history, LinkList)
        self.assertEqual(["1"], browser.history.ids)
        self.assertIsInstance(browser.history_current, Link)
        self.assertEqual("1", browser.history_current.id)
        self.assertIsInstance(browser.versions, LinkList)
        self.assertEqual(["1"], browser.versions.ids)

    def test_get_data_id(self):
        browser = Browser(slug='firefox')
        self.assertEqual(('browsers', 'firefox'), browser.get_data_id())

    def test_set_collection(self):
        browser = Browser(slug='firefox', versions=['1.0', '2.0'])
        self.assertIsNone(browser._collection)
        self.assertIsNone(browser.versions.links[0].collection)

        collection = Collection()
        browser.set_collection(collection)
        self.assertEqual(collection, browser._collection)
        self.assertEqual(collection, browser.versions.links[0].collection)

    def test_to_json_api_simple(self):
        browser = Browser()
        browser.name = {'en': 'Browser'}
        expected = {
            "browsers": {
                "name": {'en': 'Browser'}
            }
        }
        actual = browser.to_json_api()
        self.assertEqual(expected, actual)

    def test_to_json_api_complex(self):
        browser = Browser(
            id="1", slug="chrome", name={"en": "Chrome"}, history=["1"],
            history_current="1", versions=["1"])
        expected = {
            "browsers": {
                "slug": "chrome",
                "name": {"en": "Chrome"},
            }
        }
        actual = browser.to_json_api(with_sorted=False)
        self.assertEqual(expected, actual)

    def test_to_json_api_complex_with_sorted(self):
        browser = Browser(
            id="1", slug="chrome", name={"en": "Chrome"}, history=["1"],
            history_current="1", versions=["1"])
        expected = {
            "browsers": {
                "slug": "chrome",
                "name": {"en": "Chrome"},
                "links": {"versions": ["1"]},
            }
        }
        actual = browser.to_json_api()
        self.assertEqual(expected, actual)


class TestVersion(TestCase):
    def test_load_by_json(self):
        rep = {
            "versions": {
                "id": "2",
                "version": "0.2",
                "release_day": None,
                "retirement_day": None,
                "status": "unknown",
                "release_notes_uri": None,
                "note": None,
                "order": 1,
                "links": {
                    "browser": "1",
                    "supports": [
                        "1120", "1119", "1118", "1117", "1116", "1115", "1114",
                        "1113", "1112", "1111", "1110", "1109",
                    ],
                    "history": ["2"],
                    "history_current": "2"
                }
            },
        }
        version = Version()
        self.assertIsNone(version.id)
        self.assertIsNone(version.version)
        self.assertIsNone(version.release_day)
        self.assertIsNone(version.retirement_day)
        self.assertIsNone(version.status)
        self.assertIsNone(version.release_notes_uri)
        self.assertIsNone(version.note)
        self.assertIsNone(version.supports)
        self.assertIsNone(version.history)
        self.assertIsNone(version.history_current)

        version.from_json_api(rep)
        self.assertIsInstance(version.id, Link)
        self.assertEqual("2", version.id.id)
        self.assertEqual("0.2", version.version)
        self.assertIsNone(version.release_day)
        self.assertIsNone(version.retirement_day)
        self.assertEqual('unknown', version.status)
        self.assertIsNone(version.release_notes_uri)
        self.assertIsNone(version.note)
        self.assertIsInstance(version.supports, LinkList)
        self.assertEqual(
            ['1120', '1119', '1118', '1117', '1116', '1115', '1114', '1113',
             '1112', '1111', '1110', '1109'],
            version.supports.ids)
        self.assertIsInstance(version.history_current, Link)
        self.assertEqual("2", version.history_current.id)
        self.assertIsInstance(version.history, LinkList)
        self.assertEqual(["2"], version.history.ids)

    def test_get_data_id(self):
        version = Version(id="254", version="0.2", browser="2")
        browser = Browser(id="2", slug="the_browser")
        collection = Collection()
        collection.add(version)
        collection.add(browser)
        self.assertEqual(
            ('versions', 'the_browser', '0.2'), version.get_data_id())

    def test_get_data_id_null_version(self):
        version = Version(id="254", version=None, browser="2")
        browser = Browser(id="2", slug="the_browser")
        collection = Collection()
        collection.add(version)
        collection.add(browser)
        self.assertEqual(
            ('versions', 'the_browser', ''), version.get_data_id())

    def test_to_json(self):
        version = Version(
            id="2", version="0.2", status="unknown", supports=["1120", "1119"],
            browser="2")
        expected = {
            "versions": {
                "version": "0.2",
                "status": "unknown",
                "links": {
                    "browser": "2"
                }
            }
        }
        self.assertEqual(expected, version.to_json_api())


class TestFeature(TestCase):
    def test_to_json_no_parent(self):
        feature = Feature(id="1", slug="web", name={"en": "Web"})
        expected = {
            "features": {
                "slug": "web",
                "name": {"en": "Web"},
            }
        }
        self.assertEqual(expected, feature.to_json_api())

    def test_to_json_null_parent(self):
        feature = Feature(
            id="1", slug="web", name={"en": "Web"}, parent=None)
        expected = {
            "features": {
                "slug": "web",
                "name": {"en": "Web"},
                "links": {
                    "parent": None
                }
            }
        }
        self.assertEqual(expected, feature.to_json_api())


class TestSupport(TestCase):
    def test_to_json(self):
        support = Support(
            support="unknown", version="_version", feature="_feature")
        expected = {
            "supports": {
                "support": "unknown",
                "links": {
                    "version": "_version",
                    "feature": "_feature",
                }}}
        self.assertEqual(expected, support.to_json_api())


class TestSpecification(TestCase):
    def test_to_json(self):
        spec = Specification(
            slug="css1", mdn_key='CSS1', name={'en': 'CSS Level&nbsp;1'},
            uri={'en': "http://www.w3.org/TR/CSS1/"}, maturity="1",
            sections=["2"])
        expected = {
            "specifications": {
                'slug': 'css1',
                'mdn_key': 'CSS1',
                "name": {"en": "CSS Level&nbsp;1"},
                "uri": {"en": "http://www.w3.org/TR/CSS1/"},
                "links": {
                    "maturity": "1",
                },
            },
        }
        self.assertEqual(expected, spec.to_json_api(with_sorted=False))

    def test_to_json_with_sorted(self):
        spec = Specification(
            slug="css1", mdn_key='CSS1', name={'en': 'CSS Level&nbsp;1'},
            uri={'en': "http://www.w3.org/TR/CSS1/"}, maturity="1",
            sections=["2"])
        expected = {
            "specifications": {
                'slug': 'css1',
                'mdn_key': 'CSS1',
                "name": {"en": "CSS Level&nbsp;1"},
                "uri": {"en": "http://www.w3.org/TR/CSS1/"},
                "links": {
                    "maturity": "1",
                    "sections": ["2"],
                },
            },
        }
        self.assertEqual(expected, spec.to_json_api())


class TestSection(TestCase):
    def test_to_json(self):
        section = Section(
            number={'en': '1.2.3'}, name={'en': 'section foo'},
            subpath={'en': '/foo'}, specification='_spec')
        expected = {
            "sections": {
                "number": {'en': '1.2.3'},
                "name": {'en': 'section foo'},
                "subpath": {'en': '/foo'},
                "links": {
                    "specification": "_spec",
                }}}
        self.assertEqual(expected, section.to_json_api())

    def test_get_data_id_with_number(self):
        maturity = Maturity(id="2")
        spec = Specification(id="22", maturity="2", mdn_key="SPEC")
        feature = Feature(id="222")
        section = Section(
            id="_sec", specification="22", features=["222"],
            number={"en": "1.2.3"}, subpath={"en": "#123"})
        collection = Collection()
        collection.add(maturity)
        collection.add(spec)
        collection.add(feature)
        collection.add(section)
        self.assertEqual(('sections', 'SPEC', '#123'), section.get_data_id())

    def test_without_number(self):
        section = Section(
            name={'en': 'section foo'}, subpath={'en': '/foo'},
            specification='_spec')
        expected = {
            "sections": {
                "name": {'en': 'section foo'},
                "subpath": {'en': '/foo'},
                "links": {
                    "specification": "_spec",
                }}}
        self.assertEqual(expected, section.to_json_api())

    def test_get_data_id_without_subpath(self):
        maturity = Maturity(id="2")
        spec = Specification(id="22", maturity="2", mdn_key="SPEC")
        feature = Feature(id="222")
        section = Section(id="_sec", specification="22", features=["222"])
        collection = Collection()
        collection.add(maturity)
        collection.add(spec)
        collection.add(feature)
        collection.add(section)
        self.assertEqual(('sections', 'SPEC', ''), section.get_data_id())

    def test_with_empty_number(self):
        section = Section(
            name={'en': 'section foo'}, subpath={'en': '/foo'},
            specification='_spec', number={})
        expected = {
            "sections": {
                "name": {'en': 'section foo'},
                "number": {},
                "subpath": {'en': '/foo'},
                "links": {
                    "specification": "_spec",
                }}}
        self.assertEqual(expected, section.to_json_api())

    def test_get_data_id_with_empty_subpath(self):
        maturity = Maturity(id="2")
        spec = Specification(id="22", maturity="2", mdn_key="SPEC")
        feature = Feature(id="222")
        section = Section(
            id="_sec", specification="22", features=["222"], subpath={})
        collection = Collection()
        collection.add(maturity)
        collection.add(spec)
        collection.add(feature)
        collection.add(section)
        self.assertEqual(('sections', 'SPEC', ''), section.get_data_id())


class TestMaturity(TestCase):
    def test_to_json(self):
        maturity = Maturity(
            id="_mat", slug="REC", name={'en': 'Recommendation'})
        expected = {
            "maturities": {
                "slug": "REC",
                "name": {'en': 'Recommendation'},
            }}
        self.assertEqual(expected, maturity.to_json_api())


class TestCollection(TestCase):
    def setUp(self):
        self.col = Collection()

    def test_get_resources(self):
        browser = Browser(slug='firefox')
        self.col.add(browser)
        browsers = self.col.get_resources('browsers')
        self.assertEqual([browser], browsers)

    def test_get_resources_empty(self):
        browsers = self.col.get_resources('browsers')
        self.assertEqual([], browsers)

    def test_get_resources_by_data_id(self):
        browser = Browser(id='1', slug='firefox')
        version = Version(version='1.0', browser='1')
        self.col.add(browser)
        self.col.add(version)
        versions = self.col.get_resources_by_data_id('versions')
        self.assertEqual({('versions', 'firefox', '1.0'): version}, versions)
        browsers = self.col.get_resources_by_data_id('browsers')
        self.assertEqual({('browsers', 'firefox'): browser}, browsers)

    def test_get_all_by_data_id(self):
        browser = Browser(id='1', slug='chrome')
        self.col.add(browser)
        version = Version(id='2', version='1.0', browser='1')
        self.col.add(version)
        feature = Feature(id='3', slug='the-feature')
        self.col.add(feature)
        support = Support(id='4', feature='3', version='2')
        self.col.add(support)
        maturity = Maturity(id='5', slug='REC')
        self.col.add(maturity)
        specification = Specification(
            id='6', slug='css1', mdn_key='CSS1', maturity='5')
        self.col.add(specification)
        section = Section(id='7', subpath={'en': '#561'}, specification='6')
        self.col.add(section)

        index = self.col.get_all_by_data_id()
        expected = {
            ('browsers', 'chrome'): browser,
            ('versions', 'chrome', '1.0'): version,
            ('features', 'the-feature'): feature,
            ('supports', 'the-feature', 'chrome', '1.0'): support,
            ('maturities', 'REC'): maturity,
            ('specifications', 'CSS1'): specification,
            ('sections', 'CSS1', '#561'): section,
        }
        self.assertEqual(expected, index)

    def test_filter_by_property(self):
        browser = Browser(id='_firefox', slug='firefox')
        version1 = Version(version='1.0', browser='_firefox')
        version2 = Version(version='2.0', browser='_firefox')
        self.col.add(browser)
        self.col.add(version1)
        self.col.add(version2)
        versions = self.col.filter('versions', version='1.0')
        self.assertEqual([version1], versions)

    def test_filter_link(self):
        browser = Browser(id='_firefox', slug='firefox')
        version1 = Version(version=None, browser='_firefox')
        version2 = Version(version='1.0', browser='_firefox')
        self.col.add(browser)
        self.col.add(version1)
        self.col.add(version2)
        versions = self.col.filter('versions', browser='_firefox')
        self.assertEqual(2, len(versions))
        self.assertTrue(version1 in versions)
        self.assertTrue(version2 in versions)

    def test_filter_link_is_none(self):
        browser = Browser(id='_firefox', slug='firefox')
        version1 = Version(version=None, browser='_firefox')
        version2 = Version(version='1.0')
        self.col.add(browser)
        self.col.add(version1)
        self.col.add(version2)
        versions = self.col.filter('versions', browser=None)
        self.assertEqual([version2], versions)

    def test_load_all(self):
        self.col.client = mock.Mock(spec_set=['get_resource_collection'])
        self.col.client.get_resource_collection.return_value = {
            "browsers": [{
                "id": "1",
                "slug": "chrome",
                "name": {"en": "Chrome"},
                "note": None,
                "links": {
                    "history": ["1"],
                    "history_current": "1",
                    "versions": ["1", "2"],
                }
            }, {
                "id": "2",
                "slug": "firefox",
                "name": {"en": "Firefox"},
                "note": None,
                "links": {
                    "history": ["2"],
                    "history_current": "2",
                    "versions": ["40", "41", "42"],
                }
            }, {
                "id": "3",
                "slug": "internet_explorer",
                "name": {"en": "Internet Explorer"},
                "note": None,
                "links": {
                    "history": ["3"],
                    "history_current": "3",
                    "versions": ["70", "71", "72"],
                },
            }],
            "links": {
                "browsers.history": {
                    "href": (
                        "http://example.com/api/v1/historical_browsers/"
                        "{browsers.history}"),
                    "type": "historical_browsers"
                },
                "browsers.history_current": {
                    "href": (
                        "http://example.com/api/v1/historical_browsers/"
                        "{browsers.history_current}"),
                    "type": "historical_browsers"
                },
                "browsers.versions": {
                    "href": (
                        "http://example.com/api/v1/versions/"
                        "{browsers.versions}"),
                    "type": "versions"
                }
            },
            "meta": {
                "pagination": {
                    "browsers": {
                        "previous": None,
                        "next": None,
                        "count": 3
                    }
                }
            }
        }
        count = self.col.load_all('browsers')
        self.assertEqual(3, count)

    def test_override_ids_to_match(self):
        # Setup collection resources
        browser = Browser(
            id='_chrome', slug='chrome', versions=['_version'])
        version = Version(
            id='_version', version='1.0', browser='_chrome')
        feature = Feature(id='_feature', slug='the-feature')
        support = Support(
            id='_support', feature='_feature', version='_version')
        maturity = Maturity(id='_maturity', slug='REC')
        specification = Specification(
            id='_spec', slug='css1', mdn_key='CSS1', maturity='_maturity')
        section = Section(
            id='_section', number={'en': '5.6.1'}, specification='_spec')
        self.col.add(browser)
        self.col.add(version)
        self.col.add(feature)
        self.col.add(support)
        self.col.add(maturity)
        self.col.add(specification)
        self.col.add(section)

        # JSON API representation changes
        expected = {
            "versions": {
                "version": "1.0",
                "links": {
                    "browser": "_chrome",
                },
            }
        }
        self.assertEqual(expected, version.to_json_api())

        # Setup other collection with different IDs
        sync_browser = Browser(id='1', slug='chrome')
        sync_version = Version(id='2', version='1.0', browser='1')
        sync_feature = Feature(id='3', slug='the-feature')
        sync_support = Support(id='4', feature='3', version='2')
        sync_maturity = Maturity(id='5', slug='REC')
        sync_specification = Specification(
            id='6', slug='css1', mdn_key='CSS1', maturity='5')
        sync_section = Section(
            id='7', number={'en': '5.6.1'}, specification='6')
        sync_collection = Collection()
        sync_collection.add(sync_browser)
        sync_collection.add(sync_version)
        sync_collection.add(sync_feature)
        sync_collection.add(sync_support)
        sync_collection.add(sync_maturity)
        sync_collection.add(sync_specification)
        sync_collection.add(sync_section)

        # Lookup is by local ID
        self.assertEqual(browser, self.col.get('browsers', '_chrome'))
        self.assertEqual(None, self.col.get('browsers', '1'))

        # Synchronize IDs to the other collection
        self.col.override_ids_to_match(sync_collection)

        # Other IDs are now the same as original IDs
        self.assertEqual('1', browser.id.id)
        self.assertEqual('2', version.id.id)
        self.assertEqual('3', feature.id.id)
        self.assertEqual('4', support.id.id)
        self.assertEqual('5', maturity.id.id)
        self.assertEqual('6', specification.id.id)
        self.assertEqual('7', section.id.id)

        # Linked IDs are changed as well
        self.assertEqual('1', version.browser.id)
        self.assertEqual(['2'], browser.versions.ids)
        self.assertEqual('2', support.version.id)
        self.assertEqual('3', support.feature.id)
        self.assertEqual('5', specification.maturity.id)
        self.assertEqual('6', section.specification.id)

        # JSON API representation changes
        expected = {
            "versions": {
                "version": "1.0",
                "links": {
                    "browser": "1",
                },
            }
        }
        self.assertEqual(expected, version.to_json_api())

        # Lookup is by original ID
        self.assertEqual(None, self.col.get('browsers', '_chrome'))
        self.assertEqual(browser, self.col.get('browsers', '1'))

    def test_override_ids_resource_without_id(self):
        firefox = Browser(slug='firefox')
        chrome = Browser(slug='chrome')
        self.col.add(firefox)
        self.col.add(chrome)
        self.assertEqual(None, self.col.get('browsers', '1'))

        other_col = Collection()
        other_firefox = Browser(id="1", slug="firefox")
        other_col.add(other_firefox)
        self.col.override_ids_to_match(other_col)
        self.assertEqual(firefox, self.col.get('browsers', '1'))
        self.assertIsNone(chrome.id)

    def test_override_ids_resource_with_falsy_id(self):
        firefox = Browser(id="", slug='firefox')
        chrome = Browser(id=0, slug='chrome')
        self.col.add(firefox)
        self.col.add(chrome)
        self.assertEqual(None, self.col.get('browsers', '1'))

        other_col = Collection()
        other_chrome = Browser(id="1", slug="chrome")
        other_firefox = Browser(id="2", slug="firefox")
        other_col.add(other_chrome)
        other_col.add(other_firefox)
        self.col.override_ids_to_match(other_col)
        self.assertEqual(chrome, self.col.get('browsers', '1'))
        self.assertEqual(firefox, self.col.get('browsers', '2'))

    def test_remove(self):
        firefox = Browser(id='_firefox', slug='firefox')
        chrome = Browser(id='_chrome', slug='chrome')
        self.col.add(firefox)
        self.col.add(chrome)

        self.assertEqual([chrome], self.col.filter('browsers', slug='chrome'))
        self.assertEqual(
            [firefox, chrome], self.col.get_resources('browsers'))
        self.assertEqual(chrome, self.col.get('browsers', '_chrome'))
        expected = {
            ('browsers', 'firefox'): firefox,
            ('browsers', 'chrome'): chrome,
        }
        self.assertEqual(
            expected, self.col.get_resources_by_data_id('browsers'))

        self.col.remove(chrome)
        self.assertEqual([], self.col.filter('browsers', slug='chrome'))
        self.assertEqual([firefox], self.col.get_resources('browsers'))
        self.assertEqual(None, self.col.get('browsers', '_chrome'))
        expected = {('browsers', 'firefox'): firefox}
        self.assertEqual(
            expected, self.col.get_resources_by_data_id('browsers'))

    def test_remove_resource_without_id(self):
        firefox = Browser(slug='firefox')
        self.col.add(firefox)
        self.assertEqual([firefox], self.col.get_resources('browsers'))
        self.col.remove(firefox)
        self.assertEqual([], self.col.get_resources('browsers'))

    def test_load_collection(self):
        firefox = Browser(slug='firefox')
        self.col.add(firefox)
        key = ('browsers', 'firefox')
        self.assertEqual(
            {key: firefox}, self.col.get_resources_by_data_id('browsers'))
        copy_col = Collection()
        copy_col.load_collection(self.col)
        new_resources = copy_col.get_resources_by_data_id('browsers')
        self.assertEqual([key], list(new_resources.keys()))
        new_firefox = new_resources[key]
        self.assertEqual(firefox.to_json_api(), new_firefox.to_json_api())
        self.assertIsNone(firefox.id)

    def test_load_collection_with_id(self):
        firefox = Browser(slug='firefox', id=6)
        self.col.add(firefox)
        key = ('browsers', 'firefox')
        self.assertEqual(
            {key: firefox}, self.col.get_resources_by_data_id('browsers'))
        copy_col = Collection()
        copy_col.load_collection(self.col)
        new_resources = copy_col.get_resources_by_data_id('browsers')
        self.assertEqual([key], list(new_resources.keys()))
        new_firefox = new_resources[key]
        self.assertEqual(firefox.to_json_api(), new_firefox.to_json_api())
        self.assertEqual(new_firefox.id.id, 6)


class TestCollectionChangeset(TestCase):

    def setUp(self):
        self.client = Client('http://example.com')
        self.client.request = mock.Mock()
        self.client.request.side_effect = Exception('should not be called')
        self.orig_col = Collection(self.client)
        self.new_col = Collection()

    def test_empty(self):
        cc = CollectionChangeset(self.orig_col, self.new_col)
        expected = {
            "new": OrderedDict(),
            "same": OrderedDict(),
            "changed": OrderedDict(),
            "deleted": OrderedDict(),
        }
        self.assertEqual(expected, cc.changes)
        expected_summary = ""
        self.assertEqual(expected_summary, cc.summarize())

    def setup_new(self):
        browser = Browser(id='_chrome', slug='chrome')
        version = Version(version='2.0', browser='_chrome')
        self.new_col.add(browser)
        self.new_col.add(version)
        resources = (browser, version)
        return resources, CollectionChangeset(self.orig_col, self.new_col)

    def test_changes_new_items(self):
        (browser, version), cc = self.setup_new()
        expected = {
            "new": OrderedDict([
                (('browsers', 'chrome'), browser),
                (('versions', 'chrome', '2.0'), version),
            ]),
            "same": OrderedDict(),
            "changed": OrderedDict(),
            "deleted": OrderedDict(),
        }
        self.assertEqual(expected, cc.changes)

    def test_change_original_new_items(self):
        _, cc = self.setup_new()

        def fake_request(
                method, resource_type, resource_id=None, params=None,
                data=None):
            if method == 'POST' and resource_type == 'changesets':
                return {'changesets': {'id': '_changeset'}}
            elif method == 'POST' and resource_type == 'browsers':
                self.assertEqual({'browsers': {'slug': 'chrome'}}, data)
                return {'browsers': {'id': '_browser', 'slug': 'chrome'}}
            elif method == 'POST' and resource_type == 'versions':
                expected_data = {
                    "versions": {
                        "version": "2.0",
                        "links": {"browser": "_browser"}}}
                self.assertEqual(expected_data, data)
                returned_data = expected_data.copy()
                returned_data['versions']['id'] = '_version'
                return returned_data
            else:
                assert (method == 'PUT' and resource_type == 'changesets'), \
                    'Unexpected request: %s' % repr(locals())
                self.assertEqual('_changeset', resource_id)
                self.assertEqual({'changesets': {'closed': True}}, data)
                return {'changesets': {'id': '_changeset', 'closed': True}}
        self.client.request.side_effect = fake_request
        expected = {
            'browsers': {'new': 1},
            'versions': {'new': 1},
        }
        changes = cc.change_original_collection()
        self.assertEqual(expected, changes)

    def test_summary_new_items(self):
        _, cc = self.setup_new()
        expected = """\
New:
{
  "browsers": {
    "slug": "chrome"
  }
}
New:
{
  "versions": {
    "version": "2.0",
    "links": {
      "browser": "_chrome"
    }
  }
}"""
        self.assertEqual(expected, cc.summarize())

    def setup_new_with_dependencies(self):
        parent = Feature(id='parent', slug='parent')
        child1 = Feature(id='child1', slug='child1', parent='parent')
        child2 = Feature(id='child2', slug='child2', parent='parent')
        child3 = Feature(id='child3', slug='child3', parent='parent')
        grandchild = Feature(id='gchild', slug='grandchild', parent='child2')

        self.new_col.add(child1)
        self.new_col.add(parent)
        self.new_col.add(child2)
        self.new_col.add(child3)
        self.new_col.add(grandchild)
        resources = (parent, child1, child2, child3, grandchild)
        return resources, CollectionChangeset(self.orig_col, self.new_col)

    def test_changes_new_items_with_dependencies(self):
        resources, cc = self.setup_new_with_dependencies()
        parent, child1, child2, child3, grandchild = resources
        expected_order = OrderedDict([
            (('features', 'parent'), parent),
            (('features', 'child1'), child1),
            (('features', 'child2'), child2),
            (('features', 'child3'), child3),
            (('features', 'grandchild'), grandchild),
        ])
        expected = {
            "new": expected_order,
            "same": OrderedDict(),
            "changed": OrderedDict(),
            "deleted": OrderedDict(),
        }
        self.assertEqual(expected_order.keys(), cc.changes['new'].keys())
        self.assertEqual(expected, cc.changes)

    def test_change_original_new_items_with_dependencies(self):
        _, cc = self.setup_new_with_dependencies()

        def fake_request(
                method, resource_type, resource_id=None, params=None,
                data=None):
            if method == 'POST' and resource_type == 'changesets':
                return {'changesets': {'id': '_changeset'}}
            elif method == 'POST' and resource_type == 'features':
                slug = data['features']['slug']
                return {
                    'features': {
                        'id': '_' + slug,
                        'slug': slug,
                    }
                }
            else:
                assert (method == 'PUT' and resource_type == 'changesets'), \
                    'Unexpected request: %s' % repr(locals())
                self.assertEqual('_changeset', resource_id)
                self.assertEqual({'changesets': {'closed': True}}, data)
                return {'changesets': {'id': '_changeset', 'closed': True}}
        self.client.request.side_effect = fake_request
        expected = {
            'features': {'new': 5},
        }
        changes = cc.change_original_collection()
        self.assertEqual(expected, changes)

    def test_summary_new_items_with_dependencies(self):
        _, cc = self.setup_new_with_dependencies()
        expected = """\
New:
{
  "features": {
    "slug": "parent"
  }
}
New:
{
  "features": {
    "slug": "child1",
    "links": {
      "parent": "parent"
    }
  }
}
New:
{
  "features": {
    "slug": "child2",
    "links": {
      "parent": "parent"
    }
  }
}
New:
{
  "features": {
    "slug": "child3",
    "links": {
      "parent": "parent"
    }
  }
}
New:
{
  "features": {
    "slug": "grandchild",
    "links": {
      "parent": "child2"
    }
  }
}"""
        self.assertEqual(expected, cc.summarize())

    def setup_deleted(self):
        browser = Browser(id='_chrome', slug='chrome')
        version = Version(id='_chrome_2', version='2.0', browser='_chrome')
        self.orig_col.add(browser)
        self.orig_col.add(version)
        resources = (browser, version)
        return resources, CollectionChangeset(self.orig_col, self.new_col)

    def test_changes_deleted_items(self):
        (browser, version), cc = self.setup_deleted()
        expected = {
            "new": OrderedDict(),
            "same": OrderedDict(),
            "changed": OrderedDict(),
            "deleted": OrderedDict([
                (('browsers', 'chrome'), browser),
                (('versions', 'chrome', '2.0'), version),
            ]),
        }
        self.assertEqual(expected, cc.changes)

    def test_change_original_deleted_items(self):
        _, cc = self.setup_deleted()

        def fake_request(
                method, resource_type, resource_id=None, params=None,
                data=None):
            if method == 'POST' and resource_type == 'changesets':
                return {'changesets': {'id': '_changeset'}}
            elif method == 'DELETE':
                return {}
            else:
                assert (method == 'PUT' and resource_type == 'changesets'), \
                    'Unexpected request: %s' % repr(locals())
                self.assertEqual('_changeset', resource_id)
                self.assertEqual({'changesets': {'closed': True}}, data)
                return {'changesets': {'id': '_changeset', 'closed': True}}
        self.client.request.side_effect = fake_request
        expected = {
            'browsers': {'deleted': 1},
            'versions': {'deleted': 1},
        }
        changes = cc.change_original_collection()
        self.assertEqual(expected, changes)

    def test_summary_deleted_items(self):
        _, cc = self.setup_deleted()
        expected = """\
Deleted http://example.com/api/v1/browsers/_chrome:
{
  "browsers": {
    "slug": "chrome"
  }
}
Deleted http://example.com/api/v1/versions/_chrome_2:
{
  "versions": {
    "version": "2.0",
    "links": {
      "browser": "_chrome"
    }
  }
}"""
        self.assertEqual(expected, cc.summarize())

    def setup_matched(self):
        browser = Browser(id='1', slug='chrome')
        version = Version(
            id='1', version='2.0', browser='1', note={'en': 'Second Version'})
        self.orig_col.add(browser)
        self.orig_col.add(version)

        browser_same = Browser(id='_chrome', slug='chrome')
        version_diff = Version(
            id='_version', version='2.0', browser='_chrome',
            note=OrderedDict((
                ('en', 'Second Version'),
                ('es', 'Segunda Versión'))))
        self.new_col.add(version_diff)
        self.new_col.add(browser_same)
        resources = (version, browser_same, version_diff)
        return resources, CollectionChangeset(self.orig_col, self.new_col)

    def test_changes_matched_items(self):
        (version, browser_same, version_diff), cc = self.setup_matched()

        expected = {
            "new": OrderedDict(),
            "same": OrderedDict([
                (('browsers', 'chrome'), browser_same),
            ]),
            "changed": OrderedDict([
                (('versions', 'chrome', '2.0'), version_diff),
            ]),
            "deleted": OrderedDict(),
        }
        self.assertEqual(expected, cc.changes)
        changed = cc.changes['changed'][('versions', 'chrome', '2.0')]
        self.assertEqual(changed._original, version)

    def test_change_original_matched_items(self):
        _, cc = self.setup_matched()

        def fake_request(
                method, resource_type, resource_id=None, params=None,
                data=None):
            if method == 'POST' and resource_type == 'changesets':
                return {'changesets': {'id': '_changeset'}}
            elif method == 'PUT' and resource_type == 'versions':
                return data
            else:
                assert (method == 'PUT' and resource_type == 'changesets'), \
                    'Unexpected request: %s' % repr(locals())
                self.assertEqual('_changeset', resource_id)
                self.assertEqual({'changesets': {'closed': True}}, data)
                return {'changesets': {'id': '_changeset', 'closed': True}}
        self.client.request.side_effect = fake_request
        expected = {
            'versions': {'changed': 1},
        }
        changes = cc.change_original_collection()
        self.assertEqual(expected, changes)

    def test_summary_matched_items(self):
        _, cc = self.setup_matched()
        expected = """\
Changed: http://example.com/api/v1/versions/1:
  {
    "versions": {
      "version": "2.0",
      "note": {
-       "en": "Second Version"
+       "en": "Second Version",
?                             +
+       "es": "Segunda Versi\\u00f3n"
      },
      "links": {
        "browser": "1"
      }
    }
  }"""
        self.assertEqual(expected, cc.summarize())

    def test_new_browser_with_ordered_versions(self):
        """When order matters, creation order is sort order."""
        browser = Browser(
            id='_b', slug='browser', versions=['u', '1.0', '2.0'])
        v_unknown = Version(id='u', version=None, browser='_b')
        v_1 = Version(id='1.0', version='1.0', browser='_b')
        v_2 = Version(id='2.0', version='2.0', browser='_b')
        self.new_col.add(browser)
        self.new_col.add(v_1)
        self.new_col.add(v_unknown)
        self.new_col.add(v_2)
        cc = CollectionChangeset(self.orig_col, self.new_col)
        expected_order = OrderedDict([
            (('browsers', 'browser'), browser),
            (('versions', 'browser', ''), v_unknown),
            (('versions', 'browser', '1.0'), v_1),
            (('versions', 'browser', '2.0'), v_2),
        ])
        expected = {
            "new": expected_order,
            "same": OrderedDict(),
            "changed": OrderedDict(),
            "deleted": OrderedDict(),
        }
        self.assertEqual(expected_order.keys(), cc.changes['new'].keys())
        self.assertEqual(expected, cc.changes)

    def test_new_versions_to_existing_browser(self):
        """When order matters, new items update the parent item."""
        browser = Browser(
            id='_b', slug='browser', versions=['u'])
        v_1 = Version(id='1.0', version='1.0', browser='_b')
        self.orig_col.add(browser)
        self.orig_col.add(v_1)

        browser_new = Browser(
            id='_b', slug='browser', versions=['u', '1.0', '2.0'])
        v_unknown = Version(id='u', version=None, browser='_b')
        v_1_same = Version(id='1.0', version='1.0', browser='_b')
        v_2 = Version(id='2.0', version='2.0', browser='_b')
        self.new_col.add(browser_new)
        self.new_col.add(v_unknown)
        self.new_col.add(v_1_same)
        self.new_col.add(v_2)
        cc = CollectionChangeset(self.orig_col, self.new_col)
        expected_order = OrderedDict([
            (('versions', 'browser', ''), v_unknown),
            (('versions', 'browser', '2.0'), v_2),
        ])
        expected = {
            "new": expected_order,
            "same": OrderedDict([
                (('versions', 'browser', '1.0'), v_1_same),
            ]),
            "changed": OrderedDict([
                (('browsers', 'browser'), browser_new),
            ]),
            "deleted": OrderedDict(),
        }
        self.assertEqual(expected_order.keys(), cc.changes['new'].keys())
        self.assertEqual(expected, cc.changes)

    def test_features_root(self):
        root = Feature(id='root', slug='root', parent=None)
        self.new_col.add(root)
        cc = CollectionChangeset(self.orig_col, self.new_col)
        expected = {
            "new": OrderedDict([
                (('features', 'root'), root),
            ]),
            "changed": OrderedDict(),
            "deleted": OrderedDict(),
            "same": OrderedDict(),
        }
        self.assertEqual(expected, cc.changes)
