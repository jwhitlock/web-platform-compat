#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for `web-platform-compat.viewsets.ViewFeaturesViewSet` class."""
from __future__ import unicode_literals
from datetime import date
from json import dumps, loads

from django.core.urlresolvers import reverse
from django.test.utils import override_settings

from webplatformcompat.models import (
    Browser, Feature, Maturity, Section, Specification, Support, Version)
from webplatformcompat.serializers import (
    DjangoResourceClient, ViewFeatureExtraSerializer)

from .base import APITestCase, TestCase


class TestViewFeatureViewSet(APITestCase):
    """Test /view_features/<feature_id>."""

    def test_get_list(self):
        feature = self.create(Feature, slug='feature')
        url = reverse('viewfeatures-list')
        response = self.client.get(url, HTTP_ACCEPT="application/vnd.api+json")
        self.assertEqual(200, response.status_code, response.data)
        detail_url = self.reverse('viewfeatures-detail', pk=feature.pk)
        self.assertContains(response, detail_url)

    def test_minimal(self):
        """Get a minimal but complete viewfeature."""
        feature = self.create(Feature, slug='feature')
        browser = self.create(Browser, slug='chrome', name={'en': 'Browser'})
        version = self.create(Version, browser=browser, status='current')
        support = self.create(Support, version=version, feature=feature)
        maturity = self.create(
            Maturity, slug='maturity', name={'en': 'Maturity'})
        specification = self.create(
            Specification, maturity=maturity, slug='spec',
            name={'en': 'Specification'})
        section = self.create(Section, specification=specification)
        feature.sections = [section]
        self.changeset.closed = True
        self.changeset.save()

        url = reverse('viewfeatures-detail', kwargs={'pk': feature.pk})
        response = self.client.get(url)

        expected_json = {
            "features": {
                "id": str(feature.id),
                "mdn_uri": None,
                "slug": "feature",
                "experimental": False,
                "standardized": True,
                "stable": True,
                "obsolete": False,
                "name": None,
                "links": {
                    "sections": [str(section.pk)],
                    "supports": [str(support.pk)],
                    "parent": None,
                    "children": [],
                    "history_current": self.history_pk_str(feature),
                    "history": self.history_pks_str(feature),
                }
            },
            "linked": {
                "browsers": [{
                    "id": str(browser.pk),
                    "slug": "chrome",
                    "name": {"en": "Browser"},
                    "note": None,
                    "links": {
                        "history_current": self.history_pk_str(browser),
                        "history": self.history_pks_str(browser),
                    }
                }],
                "features": [],
                "maturities": [{
                    "id": str(maturity.id),
                    "slug": "maturity",
                    "name": {"en": "Maturity"},
                    "links": {
                        "history_current": self.history_pk_str(maturity),
                        "history": self.history_pks_str(maturity),
                    }
                }],
                "sections": [{
                    "id": str(section.id),
                    "number": None,
                    "name": None,
                    "subpath": None,
                    "note": None,
                    "links": {
                        "specification": str(specification.id),
                        "history_current": self.history_pk_str(section),
                        "history": self.history_pks_str(section),
                    }
                }],
                "specifications": [{
                    "id": str(specification.id),
                    "slug": "spec",
                    "mdn_key": None,
                    "name": {"en": "Specification"},
                    "uri": None,
                    "links": {
                        "maturity": str(maturity.id),
                        "history_current": self.history_pk_str(specification),
                        "history": self.history_pks_str(specification),
                    }
                }],
                "supports": [{
                    "id": str(support.id),
                    "support": "yes",
                    "prefix": None,
                    "prefix_mandatory": False,
                    "alternate_name": None,
                    "alternate_mandatory": False,
                    "requires_config": None,
                    "default_config": None,
                    "protected": False,
                    "note": None,
                    "footnote": None,
                    "links": {
                        "version": str(version.id),
                        "feature": str(feature.id),
                        "history_current": self.history_pk_str(support),
                        "history": self.history_pks_str(support),
                    }
                }],
                "versions": [{
                    "id": str(version.id),
                    "version": None,
                    "release_day": None,
                    "retirement_day": None,
                    "status": "current",
                    "release_notes_uri": None,
                    "note": None,
                    "order": 0,
                    "links": {
                        "browser": str(browser.id),
                        "history_current": self.history_pk_str(version),
                        "history": self.history_pks_str(version),
                    }
                }],
            },
            "links": {
                "browsers.history": {
                    "href": (
                        self.baseUrl + "/api/v1/historical_browsers/"
                        "{browsers.history}"),
                    "type": "historical_browsers"
                },
                "browsers.history_current": {
                    "href": (
                        self.baseUrl + "/api/v1/historical_browsers/"
                        "{browsers.history_current}"),
                    "type": "historical_browsers"
                },
                "features.children": {
                    "href": (
                        self.baseUrl + "/api/v1/features/"
                        "{features.children}"),
                    "type": "features"
                },
                "features.history": {
                    "href": (
                        self.baseUrl + "/api/v1/historical_features/"
                        "{features.history}"),
                    "type": "historical_features"
                },
                "features.history_current": {
                    "href": (
                        self.baseUrl + "/api/v1/historical_features/"
                        "{features.history_current}"),
                    "type": "historical_features"
                },
                "features.parent": {
                    "href": (
                        self.baseUrl + "/api/v1/features/"
                        "{features.parent}"),
                    "type": "features"
                },
                "features.sections": {
                    "href": (
                        self.baseUrl + "/api/v1/sections/"
                        "{features.sections}"),
                    "type": "sections"
                },
                "features.supports": {
                    "href": (
                        self.baseUrl + "/api/v1/supports/"
                        "{features.supports}"),
                    "type": "supports"
                },
                "maturities.history": {
                    "href": (
                        self.baseUrl + "/api/v1/historical_maturities/"
                        "{maturities.history}"),
                    "type": "historical_maturities"
                },
                "maturities.history_current": {
                    "href": (
                        self.baseUrl + "/api/v1/historical_maturities/"
                        "{maturities.history_current}"),
                    "type": "historical_maturities"
                },
                "sections.history": {
                    "href": (
                        self.baseUrl + "/api/v1/historical_sections/"
                        "{sections.history}"),
                    "type": "historical_sections"
                },
                "sections.history_current": {
                    "href": (
                        self.baseUrl + "/api/v1/historical_sections/"
                        "{sections.history_current}"),
                    "type": "historical_sections"
                },
                "sections.specification": {
                    "href": (
                        self.baseUrl + "/api/v1/specifications/"
                        "{sections.specification}"),
                    "type": "specifications"
                },
                "specifications.history": {
                    "href": (
                        self.baseUrl + "/api/v1/historical_specifications/"
                        "{specifications.history}"),
                    "type": "historical_specifications"
                },
                "specifications.history_current": {
                    "href": (
                        self.baseUrl + "/api/v1/historical_specifications/"
                        "{specifications.history_current}"),
                    "type": "historical_specifications"
                },
                "specifications.maturity": {
                    "href": (
                        self.baseUrl + "/api/v1/maturities/"
                        "{specifications.maturity}"),
                    "type": "maturities"
                },
                "supports.feature": {
                    "href": (
                        self.baseUrl + "/api/v1/features/"
                        "{supports.feature}"),
                    "type": "features"
                },
                "supports.history": {
                    "href": (
                        self.baseUrl + "/api/v1/historical_supports/"
                        "{supports.history}"),
                    "type": "historical_supports"
                },
                "supports.history_current": {
                    "href": (
                        self.baseUrl + "/api/v1/historical_supports/"
                        "{supports.history_current}"),
                    "type": "historical_supports"
                },
                "supports.version": {
                    "href": (
                        self.baseUrl + "/api/v1/versions/"
                        "{supports.version}"),
                    "type": "versions"
                },
                "versions.browser": {
                    "href": (
                        self.baseUrl + "/api/v1/browsers/"
                        "{versions.browser}"),
                    "type": "browsers"
                },
                "versions.history": {
                    "href": (
                        self.baseUrl + "/api/v1/historical_versions/"
                        "{versions.history}"),
                    "type": "historical_versions"
                },
                "versions.history_current": {
                    "href": (
                        self.baseUrl + "/api/v1/historical_versions/"
                        "{versions.history_current}"),
                    "type": "historical_versions"
                },
            },
            "meta": {
                "compat_table": {
                    "tabs": [
                        {
                            "name": {"en": "Desktop Browsers"},
                            "browsers": [str(browser.pk)]
                        },
                    ],
                    "supports": {
                        str(feature.pk): {
                            str(browser.pk): [str(support.pk)],
                        }
                    },
                    "pagination": {
                        "linked.features": {
                            "previous": None,
                            "next": None,
                            "count": 0,
                        },
                    },
                    "languages": ['en'],
                    "footnotes": {},
                }
            }
        }
        actual_json = loads(response.content.decode('utf-8'))
        self.assertDataEqual(expected_json, actual_json)

    def test_multiple_versions(self):
        """Meta section spells out significant versions."""
        feature = self.create(Feature, slug='feature')
        browser = self.create(Browser, slug='browser', name={'en': 'Browser'})
        version1 = self.create(
            Version, browser=browser, status='current', version="1.0")
        version2 = self.create(
            Version, browser=browser, status='current', version="2.0")
        version3 = self.create(
            Version, browser=browser, status='current', version="3.0")
        support1 = self.create(
            Support, version=version1, feature=feature, support="no")
        # No change in support
        self.create(
            Support, version=version2, feature=feature, support="no")
        support3 = self.create(
            Support, version=version3, feature=feature, support="yes")
        self.changeset.closed = True
        self.changeset.save()

        url = reverse('viewfeatures-detail', kwargs={'pk': feature.pk})
        response = self.client.get(url)
        actual_json = loads(response.content.decode('utf-8'))
        expected_supports = {
            str(feature.pk): {
                str(browser.pk): [str(support1.pk), str(support3.pk)],
            }
        }
        actual_supports = actual_json['meta']['compat_table']['supports']
        self.assertDataEqual(expected_supports, actual_supports)

    @override_settings(PAGINATE_VIEW_FEATURE=2)
    def test_large_feature_tree(self):
        feature = self.create(Feature, slug='feature')
        self.create(Feature, slug='child1', parent=feature)
        self.create(Feature, slug='child2', parent=feature)
        self.create(Feature, slug='child3', parent=feature)
        self.changeset.closed = True
        self.changeset.save()

        url = reverse('viewfeatures-detail', kwargs={'pk': feature.pk})
        response = self.client.get(url)
        actual_json = loads(response.content.decode('utf-8'))
        expected_pagination = {
            'linked.features': {
                'previous': None,
                'next': self.baseUrl + url + '?page=2',
                'count': 3,
            }
        }
        actual_pagination = actual_json['meta']['compat_table']['pagination']
        self.assertDataEqual(expected_pagination, actual_pagination)

        response = self.client.get(url + '?page=2')
        actual_json = loads(response.content.decode('utf-8'))
        expected_pagination = {
            'linked.features': {
                'previous': self.baseUrl + url + '?page=1',
                'next': None,
                'count': 3,
            }
        }
        actual_pagination = actual_json['meta']['compat_table']['pagination']
        self.assertDataEqual(expected_pagination, actual_pagination)

    def test_important_versions(self):
        feature = self.create(Feature, slug='feature')
        browser = self.create(Browser, slug='browser')
        v1 = self.create(Version, browser=browser, version='1')
        support = {
            'support': 'yes',
            'prefix': '--pre',
            'prefix_mandatory': True,
            'alternate_name': 'future',
            'alternate_mandatory': True,
            'requires_config': 'feature=Yes',
            'default_config': 'feature=No',
            'protected': False,
            'note': {'en': 'note'},
            'footnote': {'en': 'footnote'},
        }
        s1 = self.create(Support, version=v1, feature=feature, **support)

        v2 = self.create(Version, browser=browser, version='2')
        support['prefix_mandatory'] = False
        s2 = self.create(Support, version=v2, feature=feature, **support)

        v3 = self.create(Version, browser=browser, version='3')
        support['prefix'] = ''
        s3 = self.create(Support, version=v3, feature=feature, **support)

        v4 = self.create(Version, browser=browser, version='4')
        support['alternate_mandatory'] = False
        s4 = self.create(Support, version=v4, feature=feature, **support)

        v5 = self.create(Version, browser=browser, version='5')
        support['alternate_name'] = ''
        s5 = self.create(Support, version=v5, feature=feature, **support)

        # BORING VERSION
        v51 = self.create(Version, browser=browser, version='5.1')
        self.create(Support, version=v51, feature=feature, **support)

        v6 = self.create(Version, browser=browser, version='6')
        support['default_config'] = 'feature=Yes'
        s6 = self.create(Support, version=v6, feature=feature, **support)

        v7 = self.create(Version, browser=browser, version='7')
        support['protected'] = True
        s7 = self.create(Support, version=v7, feature=feature, **support)

        v8 = self.create(Version, browser=browser, version='8')
        support['note']['es'] = 'el note'
        s8 = self.create(Support, version=v8, feature=feature, **support)

        v9 = self.create(Version, browser=browser, version='9')
        support['footnote'] = None
        s9 = self.create(Support, version=v9, feature=feature, **support)

        url = reverse('viewfeatures-detail', kwargs={'pk': feature.pk})
        response = self.client.get(url)
        actual_json = loads(response.content.decode('utf-8'))
        expected_supports = {
            str(feature.pk): {
                str(browser.pk): [
                    str(s1.pk), str(s2.pk), str(s3.pk), str(s4.pk),
                    str(s5.pk), str(s6.pk), str(s7.pk), str(s8.pk),
                    str(s9.pk)
                ]}}
        actual_supports = actual_json['meta']['compat_table']['supports']
        self.assertDataEqual(expected_supports, actual_supports)

    def test_get_documented(self):
        """Get the viewfeature with the hand-coded values for docs.

        Emulates the MDN page en-US/docs/Web/HTML/Element/address page
        Names include the documentation IDs, but actual IDs will differ
        """
        feature_parent_800 = self.create(Feature, slug='html')
        feature_816 = self.create(
            Feature, parent=feature_parent_800,
            mdn_uri={
                'en': ('https://developer.mozilla.org/'
                       'en-US/docs/Web/HTML/Element/address')},
            slug='html-element-address', name={'zxx': 'address'})
        feature_row_191 = self.create(
            Feature, parent=feature_816, slug='html-address',
            name={'en': 'Basic support'})

        browser_chrome_1 = self.create(
            Browser, slug='chrome', name={'en': 'Chrome'})
        browser_firefox_2 = self.create(
            Browser, slug='firefox', name={"en": "Firefox"},
            note={"en": "Uses Gecko for its web browser engine."})
        browser_ie_3 = self.create(
            Browser, slug='internet_explorer',
            name={"en": "Internet Explorer"})
        browser_opera_4 = self.create(
            Browser, slug='opera', name={"en": "Opera"})
        browser_safari_5 = self.create(
            Browser, slug='safari', name={"en": "Safari"},
            note={"en": "Uses Webkit for its web browser engine."})
        browser_android_6 = self.create(
            Browser, slug='android', name={"en": "Android"})
        browser_ffmobile_7 = self.create(
            Browser, slug='firefox_mobile', name={"en": "Firefox Mobile"},
            note={"en": "Uses Gecko for its web browser engine."})
        browser_iephone_8 = self.create(
            Browser, slug='ie_mobile', name={"en": "IE Mobile"})
        browser_operamobile_9 = self.create(
            Browser, slug='opera_mobile', name={"en": "Opera Mobile"})
        browser_safarimobile_10 = self.create(
            Browser, slug='safari_mobile', name={"en": "Safari Mobile"})
        browser_operamini_11 = self.create(
            Browser, slug="opera_mini", name={"en": "Opera Mini"})

        version_chrome_758 = self.create(
            Version, browser=browser_chrome_1, status='current')
        version_firefox_759 = self.create(
            Version, browser=browser_firefox_2, version="1.0",
            status="retired", release_day=date(2004, 12, 9),
            retirement_day=date(2005, 2, 24))
        version_ie_760 = self.create(
            Version, browser=browser_ie_3,
            version="1.0", status="retired", release_day=date(1995, 8, 16))
        version_opera_761 = self.create(
            Version, browser=browser_opera_4, version="5.12",
            status="retired", release_day=date(2001, 6, 27))
        version_safari_762 = self.create(
            Version, browser=browser_safari_5, version="1.0",
            status="retired", release_day=date(2003, 6, 23))
        version_android_763 = self.create(
            Version, browser=browser_android_6, status="current")
        version_ffmobile_764 = self.create(
            Version, browser=browser_ffmobile_7, version="1.0",
            status="retired", note={'en': "Uses Gecko 1.7"})
        version_iephone_765 = self.create(
            Version, browser=browser_iephone_8, status="current")
        version_operamobile_766 = self.create(
            Version, browser=browser_operamobile_9, status="current")
        version_safarimobile_767 = self.create(
            Version, browser=browser_safarimobile_10, status="current")
        version_operamini_768 = self.create(
            Version, browser=browser_operamini_11, status="current")

        support_chrome_358 = self.create(
            Support, version=version_chrome_758, feature=feature_row_191)
        support_firefox_359 = self.create(
            Support, version=version_firefox_759, feature=feature_row_191)
        support_ie_360 = self.create(
            Support, version=version_ie_760, feature=feature_row_191)
        support_opera_361 = self.create(
            Support, version=version_opera_761, feature=feature_row_191)
        support_safari_362 = self.create(
            Support, version=version_safari_762, feature=feature_row_191)
        support_android_363 = self.create(
            Support, version=version_android_763, feature=feature_row_191)
        support_ffmobile_364 = self.create(
            Support, version=version_ffmobile_764, feature=feature_row_191)
        support_iephone_365 = self.create(
            Support, version=version_iephone_765, feature=feature_row_191)
        support_operamobile_366 = self.create(
            Support, version=version_operamobile_766, feature=feature_row_191)
        support_safarimobile_367 = self.create(
            Support, version=version_safarimobile_767, feature=feature_row_191)
        support_operamini_368 = self.create(
            Support, version=version_operamini_768, feature=feature_row_191)

        mat_23 = self.create(
            Maturity, slug='Living', name={'en': 'Living Standard'})
        mat_49 = self.create(
            Maturity, slug='PR',
            name={
                'en': 'Proposed Recommendation',
                'ja': "勧告案",
            })
        mat_52 = self.create(
            Maturity, slug='REC',
            name={
                'en': 'Recommendation',
                'jp': '勧告'
            })

        spec_114 = self.create(
            Specification, maturity=mat_49,
            slug='html5_w3c', mdn_key='HTML5 W3C',
            name={'en': 'HTML5'},
            uri={'en': 'http://www.w3.org/TR/html5/'})
        spec_273 = self.create(
            Specification, maturity=mat_23,
            slug="html_whatwg", mdn_key="HTML WHATWG",
            name={"en": "WHATWG HTML Living Standard"},
            uri={
                "en":
                "http://www.whatwg.org/specs/web-apps/current-work/multipage/",
            })
        spec_576 = self.create(
            Specification, maturity=mat_52,
            slug='html4_01', mdn_key='HTML4.01',
            name={'en': 'HTML 4.01 Specification'},
            uri={"en": "http://www.w3.org/TR/html401/"})

        section_70 = self.create(
            Section, specification=spec_576,
            number={'en': '7.5.6'},
            name={'en': 'The ADDRESS element'},
            subpath={'en': 'struct/global.html#h-7.5.6'})
        section_421 = self.create(
            Section, specification=spec_114,
            number={'en': '4.3.9'},
            name={'en': 'The address element'},
            subpath={'en': 'sections.html#the-address-element'})
        section_746 = self.create(
            Section, specification=spec_273,
            number={'en': '4.3.10'},
            name={'en': 'The address element'},
            subpath={'en': 'sections.html#the-address-element'})
        feature_816.sections = (section_746, section_421, section_70)
        self.changeset.closed = True
        self.changeset.save()

        url = reverse('viewfeatures-detail', kwargs={'pk': feature_816.pk})
        response = self.client.get(url)

        expected_json = {
            "features": {
                "id": str(feature_816.id),
                "mdn_uri": {
                    "en": ("https://developer.mozilla.org/"
                           "en-US/docs/Web/HTML/Element/address")
                },
                "slug": "html-element-address",
                "experimental": False,
                "standardized": True,
                "stable": True,
                "obsolete": False,
                "name": "address",
                "links": {
                    "sections": [
                        str(section_746.pk),
                        str(section_421.pk),
                        str(section_70.pk),
                    ],
                    "supports": [],
                    "parent": str(feature_parent_800.id),
                    "children": [str(feature_row_191.id)],
                    "history_current": self.history_pk_str(feature_816),
                    "history": self.history_pks_str(feature_816),
                }
            },
            "linked": {
                "browsers": [
                    {
                        "id": str(browser_chrome_1.pk),
                        "slug": "chrome",
                        "name": {
                            "en": "Chrome"
                        },
                        "note": None,
                        "links": {
                            "history_current": self.history_pk_str(
                                browser_chrome_1),
                            "history": self.history_pks_str(browser_chrome_1),
                        }
                    },
                    {
                        "id": str(browser_firefox_2.pk),
                        "slug": "firefox",
                        "name": {
                            "en": "Firefox"
                        },
                        "note": {
                            "en": "Uses Gecko for its web browser engine."
                        },
                        "links": {
                            "history_current": self.history_pk_str(
                                browser_firefox_2),
                            "history": self.history_pks_str(browser_firefox_2),
                        }
                    },
                    {
                        "id": str(browser_ie_3.pk),
                        "slug": "internet_explorer",
                        "name": {
                            "en": "Internet Explorer"
                        },
                        "note": None,
                        "links": {
                            "history_current": self.history_pk_str(
                                browser_ie_3),
                            "history": self.history_pks_str(browser_ie_3),
                        }
                    },
                    {
                        "id": str(browser_opera_4.pk),
                        "slug": "opera",
                        "name": {
                            "en": "Opera"
                        },
                        "note": None,
                        "links": {
                            "history_current": self.history_pk_str(
                                browser_opera_4),
                            "history": self.history_pks_str(browser_opera_4),
                        }
                    },
                    {
                        "id": str(browser_safari_5.pk),
                        "slug": "safari",
                        "name": {
                            "en": "Safari"
                        },
                        "note": {
                            "en": "Uses Webkit for its web browser engine."
                        },
                        "links": {
                            "history_current": self.history_pk_str(
                                browser_safari_5),
                            "history": self.history_pks_str(browser_safari_5),
                        }
                    },
                    {
                        "id": str(browser_android_6.pk),
                        "slug": "android",
                        "name": {
                            "en": "Android"
                        },
                        "note": None,
                        "links": {
                            "history_current": self.history_pk_str(
                                browser_android_6),
                            "history": self.history_pks_str(browser_android_6),
                        }
                    },
                    {
                        "id": str(browser_ffmobile_7.pk),
                        "slug": "firefox_mobile",
                        "name": {
                            "en": "Firefox Mobile"
                        },
                        "note": {
                            "en": "Uses Gecko for its web browser engine."
                        },
                        "links": {
                            "history_current": self.history_pk_str(
                                browser_ffmobile_7),
                            "history": self.history_pks_str(
                                browser_ffmobile_7),
                        }
                    },
                    {
                        "id": str(browser_iephone_8.pk),
                        "slug": "ie_mobile",
                        "name": {
                            "en": "IE Mobile"
                        },
                        "note": None,
                        "links": {
                            "history_current": self.history_pk_str(
                                browser_iephone_8),
                            "history": self.history_pks_str(browser_iephone_8),
                        }
                    },
                    {
                        "id": str(browser_operamobile_9.pk),
                        "slug": "opera_mobile",
                        "name": {
                            "en": "Opera Mobile"
                        },
                        "note": None,
                        "links": {
                            "history_current": self.history_pk_str(
                                browser_operamobile_9),
                            "history": self.history_pks_str(
                                browser_operamobile_9),
                        }
                    },
                    {
                        "id": str(browser_safarimobile_10.pk),
                        "slug": "safari_mobile",
                        "name": {
                            "en": "Safari Mobile"
                        },
                        "note": None,
                        "links": {
                            "history_current": self.history_pk_str(
                                browser_safarimobile_10),
                            "history": self.history_pks_str(
                                browser_safarimobile_10),
                        }
                    },
                    {
                        "id": str(browser_operamini_11.pk),
                        "slug": "opera_mini",
                        "name": {
                            "en": "Opera Mini"
                        },
                        "note": None,
                        "links": {
                            "history_current": self.history_pk_str(
                                browser_operamini_11),
                            "history": self.history_pks_str(
                                browser_operamini_11),
                        }
                    }
                ],
                "features": [
                    {
                        "id": str(feature_row_191.id),
                        "slug": "html-address",
                        "experimental": False,
                        "standardized": True,
                        "stable": True,
                        "obsolete": False,
                        "name": {
                            "en": "Basic support"
                        },
                        "mdn_uri": None,
                        "links": {
                            "sections": [],
                            "supports": [
                                str(support_chrome_358.pk),
                                str(support_firefox_359.pk),
                                str(support_ie_360.pk),
                                str(support_opera_361.pk),
                                str(support_safari_362.pk),
                                str(support_android_363.pk),
                                str(support_ffmobile_364.pk),
                                str(support_iephone_365.pk),
                                str(support_operamobile_366.pk),
                                str(support_safarimobile_367.pk),
                                str(support_operamini_368.pk)
                            ],
                            "parent": str(feature_816.id),
                            "children": [],
                            "history_current": self.history_pk_str(
                                feature_row_191),
                            "history": self.history_pks_str(feature_row_191),
                        }
                    }
                ],
                "maturities": [
                    {
                        "id": str(mat_23.id),
                        "slug": "Living",
                        "name": {"en": "Living Standard"},
                        "links": {
                            "history_current": self.history_pk_str(mat_23),
                            "history": self.history_pks_str(mat_23),
                        }
                    },
                    {
                        "id": str(mat_49.id),
                        "slug": "PR",
                        "name": {
                            "en": "Proposed Recommendation",
                            "ja": "\u52e7\u544a\u6848"
                        },
                        "links": {
                            "history_current": self.history_pk_str(mat_49),
                            "history": self.history_pks_str(mat_49),
                        }
                    },
                    {
                        "id": str(mat_52.id),
                        "slug": "REC",
                        "name": {
                            "en": "Recommendation",
                            "jp": "\u52e7\u544a"
                        },
                        "links": {
                            "history_current": self.history_pk_str(mat_52),
                            "history": self.history_pks_str(mat_52),
                        }
                    },
                ],
                "sections": [
                    {
                        "id": str(section_70.id),
                        "number": {"en": "7.5.6"},
                        "name": {"en": "The ADDRESS element"},
                        "subpath": {"en": "struct/global.html#h-7.5.6"},
                        "note": None,
                        "links": {
                            "specification": str(spec_576.id),
                            "history_current": self.history_pk_str(section_70),
                            "history": self.history_pks_str(section_70),
                        }
                    },
                    {
                        "id": str(section_421.id),
                        "number": {"en": "4.3.9"},
                        "name": {"en": "The address element"},
                        "subpath": {"en": "sections.html#the-address-element"},
                        "note": None,
                        "links": {
                            "specification": str(spec_114.id),
                            "history_current": self.history_pk_str(
                                section_421),
                            "history": self.history_pks_str(section_421),
                        }
                    },
                    {
                        "id": str(section_746.id),
                        "number": {"en": "4.3.10"},
                        "name": {"en": "The address element"},
                        "subpath": {"en": "sections.html#the-address-element"},
                        "note": None,
                        "links": {
                            "specification": str(spec_273.id),
                            "history_current": self.history_pk_str(
                                section_746),
                            "history": self.history_pks_str(section_746),
                        }
                    },
                ],
                "specifications": [
                    {
                        "id": str(spec_114.id),
                        "slug": "html5_w3c",
                        "mdn_key": "HTML5 W3C",
                        "name": {
                            "en": "HTML5"
                        },
                        "uri": {
                            "en": "http://www.w3.org/TR/html5/"
                        },
                        "links": {
                            "maturity": str(mat_49.id),
                            "history_current": self.history_pk_str(spec_114),
                            "history": self.history_pks_str(spec_114),
                        }
                    },
                    {
                        "id": str(spec_273.id),
                        "slug": "html_whatwg",
                        "mdn_key": "HTML WHATWG",
                        "name": {
                            "en": "WHATWG HTML Living Standard"
                        },
                        "uri": {
                            "en": (
                                "http://www.whatwg.org/specs/web-apps/"
                                "current-work/multipage/"),
                        },
                        "links": {
                            "maturity": str(mat_23.id),
                            "history_current": self.history_pk_str(spec_273),
                            "history": self.history_pks_str(spec_273),
                        }
                    },
                    {
                        "id": str(spec_576.id),
                        "slug": "html4_01",
                        "mdn_key": "HTML4.01",
                        "name": {
                            "en": "HTML 4.01 Specification"
                        },
                        "uri": {
                            "en": "http://www.w3.org/TR/html401/"
                        },
                        "links": {
                            "maturity": str(mat_52.id),
                            "history_current": self.history_pk_str(spec_576),
                            "history": self.history_pks_str(spec_576),
                        }
                    },
                ],
                "supports": [
                    {
                        "id": str(support_chrome_358.id),
                        "support": "yes",
                        "prefix": None,
                        "prefix_mandatory": False,
                        "alternate_name": None,
                        "alternate_mandatory": False,
                        "requires_config": None,
                        "default_config": None,
                        "protected": False,
                        "note": None,
                        "footnote": None,
                        "links": {
                            "version": str(version_chrome_758.id),
                            "feature": str(feature_row_191.id),
                            "history_current": self.history_pk_str(
                                support_chrome_358),
                            "history": self.history_pks_str(
                                support_chrome_358),
                        }
                    },
                    {
                        "id": str(support_firefox_359.id),
                        "support": "yes",
                        "prefix": None,
                        "prefix_mandatory": False,
                        "alternate_name": None,
                        "alternate_mandatory": False,
                        "requires_config": None,
                        "default_config": None,
                        "protected": False,
                        "note": None,
                        "footnote": None,
                        "links": {
                            "version": str(version_firefox_759.id),
                            "feature": str(feature_row_191.id),
                            "history_current": self.history_pk_str(
                                support_firefox_359),
                            "history": self.history_pks_str(
                                support_firefox_359),
                        }
                    },
                    {
                        "id": str(support_ie_360.id),
                        "support": "yes",
                        "prefix": None,
                        "prefix_mandatory": False,
                        "alternate_name": None,
                        "alternate_mandatory": False,
                        "requires_config": None,
                        "default_config": None,
                        "protected": False,
                        "note": None,
                        "footnote": None,
                        "links": {
                            "version": str(version_ie_760.id),
                            "feature": str(feature_row_191.id),
                            "history_current": self.history_pk_str(
                                support_ie_360),
                            "history": self.history_pks_str(
                                support_ie_360),
                        }
                    },
                    {
                        "id": str(support_opera_361.id),
                        "support": "yes",
                        "prefix": None,
                        "prefix_mandatory": False,
                        "alternate_name": None,
                        "alternate_mandatory": False,
                        "requires_config": None,
                        "default_config": None,
                        "protected": False,
                        "note": None,
                        "footnote": None,
                        "links": {
                            "version": str(version_opera_761.id),
                            "feature": str(feature_row_191.id),
                            "history_current": self.history_pk_str(
                                support_opera_361),
                            "history": self.history_pks_str(
                                support_opera_361),
                        }
                    },
                    {
                        "id": str(support_safari_362.id),
                        "support": "yes",
                        "prefix": None,
                        "prefix_mandatory": False,
                        "alternate_name": None,
                        "alternate_mandatory": False,
                        "requires_config": None,
                        "default_config": None,
                        "protected": False,
                        "note": None,
                        "footnote": None,
                        "links": {
                            "version": str(version_safari_762.id),
                            "feature": str(feature_row_191.id),
                            "history_current": self.history_pk_str(
                                support_safari_362),
                            "history": self.history_pks_str(
                                support_safari_362),
                        }
                    },
                    {
                        "id": str(support_android_363.id),
                        "support": "yes",
                        "prefix": None,
                        "prefix_mandatory": False,
                        "alternate_name": None,
                        "alternate_mandatory": False,
                        "requires_config": None,
                        "default_config": None,
                        "protected": False,
                        "note": None,
                        "footnote": None,
                        "links": {
                            "version": str(version_android_763.id),
                            "feature": str(feature_row_191.id),
                            "history_current": self.history_pk_str(
                                support_android_363),
                            "history": self.history_pks_str(
                                support_android_363),
                        }
                    },
                    {
                        "id": str(support_ffmobile_364.id),
                        "support": "yes",
                        "prefix": None,
                        "prefix_mandatory": False,
                        "alternate_name": None,
                        "alternate_mandatory": False,
                        "requires_config": None,
                        "default_config": None,
                        "protected": False,
                        "note": None,
                        "footnote": None,
                        "links": {
                            "version": str(version_ffmobile_764.id),
                            "feature": str(feature_row_191.id),
                            "history_current": self.history_pk_str(
                                support_ffmobile_364),
                            "history": self.history_pks_str(
                                support_ffmobile_364),
                        }
                    },
                    {
                        "id": str(support_iephone_365.id),
                        "support": "yes",
                        "prefix": None,
                        "prefix_mandatory": False,
                        "alternate_name": None,
                        "alternate_mandatory": False,
                        "requires_config": None,
                        "default_config": None,
                        "protected": False,
                        "note": None,
                        "footnote": None,
                        "links": {
                            "version": str(version_iephone_765.id),
                            "feature": str(feature_row_191.id),
                            "history_current": self.history_pk_str(
                                support_iephone_365),
                            "history": self.history_pks_str(
                                support_iephone_365),
                        }
                    },
                    {
                        "id": str(support_operamobile_366.id),
                        "support": "yes",
                        "prefix": None,
                        "prefix_mandatory": False,
                        "alternate_name": None,
                        "alternate_mandatory": False,
                        "requires_config": None,
                        "default_config": None,
                        "protected": False,
                        "note": None,
                        "footnote": None,
                        "links": {
                            "version": str(version_operamobile_766.id),
                            "feature": str(feature_row_191.id),
                            "history_current": self.history_pk_str(
                                support_operamobile_366),
                            "history": self.history_pks_str(
                                support_operamobile_366)
                        }
                    },
                    {
                        "id": str(support_safarimobile_367.id),
                        "support": "yes",
                        "prefix": None,
                        "prefix_mandatory": False,
                        "alternate_name": None,
                        "alternate_mandatory": False,
                        "requires_config": None,
                        "default_config": None,
                        "protected": False,
                        "note": None,
                        "footnote": None,
                        "links": {
                            "version": str(version_safarimobile_767.id),
                            "feature": str(feature_row_191.id),
                            "history_current": self.history_pk_str(
                                support_safarimobile_367),
                            "history": self.history_pks_str(
                                support_safarimobile_367),
                        }
                    },
                    {
                        "id": str(support_operamini_368.id),
                        "support": "yes",
                        "prefix": None,
                        "prefix_mandatory": False,
                        "alternate_name": None,
                        "alternate_mandatory": False,
                        "requires_config": None,
                        "default_config": None,
                        "protected": False,
                        "note": None,
                        "footnote": None,
                        "links": {
                            "version": str(version_operamini_768.id),
                            "feature": str(feature_row_191.id),
                            "history_current": self.history_pk_str(
                                support_operamini_368),
                            "history": self.history_pks_str(
                                support_operamini_368),
                        }
                    }
                ],
                "versions": [
                    {
                        "id": str(version_chrome_758.id),
                        "version": None,
                        "release_day": None,
                        "retirement_day": None,
                        "status": "current",
                        "release_notes_uri": None,
                        "note": None,
                        "order": 0,
                        "links": {
                            "browser": str(browser_chrome_1.id),
                            "history_current": self.history_pk_str(
                                version_chrome_758),
                            "history": self.history_pks_str(
                                version_chrome_758),
                        }
                    },
                    {
                        "id": str(version_firefox_759.id),
                        "version": "1.0",
                        "release_day": "2004-12-09",
                        "retirement_day": "2005-02-24",
                        "status": "retired",
                        "release_notes_uri": None,
                        "note": None,
                        "order": 0,
                        "links": {
                            "browser": str(browser_firefox_2.id),
                            "history_current": self.history_pk_str(
                                version_firefox_759),
                            "history": self.history_pks_str(
                                version_firefox_759),
                        }
                    },
                    {
                        "id": str(version_ie_760.id),
                        "version": "1.0",
                        "release_day": "1995-08-16",
                        "retirement_day": None,
                        "status": "retired",
                        "release_notes_uri": None,
                        "note": None,
                        "order": 0,
                        "links": {
                            "browser": str(browser_ie_3.id),
                            "history_current": self.history_pk_str(
                                version_ie_760),
                            "history": self.history_pks_str(
                                version_ie_760),
                        }
                    },
                    {
                        "id": str(version_opera_761.id),
                        "version": "5.12",
                        "release_day": "2001-06-27",
                        "retirement_day": None,
                        "status": "retired",
                        "release_notes_uri": None,
                        "note": None,
                        "order": 0,
                        "links": {
                            "browser": str(browser_opera_4.id),
                            "history_current": self.history_pk_str(
                                version_opera_761),
                            "history": self.history_pks_str(
                                version_opera_761),
                        }
                    },
                    {
                        "id": str(version_safari_762.id),
                        "version": "1.0",
                        "release_day": "2003-06-23",
                        "retirement_day": None,
                        "status": "retired",
                        "release_notes_uri": None,
                        "note": None,
                        "order": 0,
                        "links": {
                            "browser": str(browser_safari_5.id),
                            "history_current": self.history_pk_str(
                                version_safari_762),
                            "history": self.history_pks_str(
                                version_safari_762),
                        }
                    },
                    {
                        "id": str(version_android_763.id),
                        "version": None,
                        "release_day": None,
                        "retirement_day": None,
                        "status": "current",
                        "release_notes_uri": None,
                        "note": None,
                        "order": 0,
                        "links": {
                            "browser": str(browser_android_6.id),
                            "history_current": self.history_pk_str(
                                version_android_763),
                            "history": self.history_pks_str(
                                version_android_763),
                        }
                    },
                    {
                        "id": str(version_ffmobile_764.id),
                        "version": "1.0",
                        "release_day": None,
                        "retirement_day": None,
                        "status": "retired",
                        "release_notes_uri": None,
                        "note": {"en": "Uses Gecko 1.7"},
                        "order": 0,
                        "links": {
                            "browser": str(browser_ffmobile_7.id),
                            "history_current": self.history_pk_str(
                                version_ffmobile_764),
                            "history": self.history_pks_str(
                                version_ffmobile_764),
                        }
                    },
                    {
                        "id": str(version_iephone_765.id),
                        "version": None,
                        "release_day": None,
                        "retirement_day": None,
                        "status": "current",
                        "release_notes_uri": None,
                        "note": None,
                        "order": 0,
                        "links": {
                            "browser": str(browser_iephone_8.id),
                            "history_current": self.history_pk_str(
                                version_iephone_765),
                            "history": self.history_pks_str(
                                version_iephone_765),
                        }
                    },
                    {
                        "id": str(version_operamobile_766.id),
                        "version": None,
                        "release_day": None,
                        "retirement_day": None,
                        "status": "current",
                        "release_notes_uri": None,
                        "note": None,
                        "order": 0,
                        "links": {
                            "browser": str(browser_operamobile_9.id),
                            "history_current": self.history_pk_str(
                                version_operamobile_766),
                            "history": self.history_pks_str(
                                version_operamobile_766),
                        }
                    },
                    {
                        "id": str(version_safarimobile_767.id),
                        "version": None,
                        "release_day": None,
                        "retirement_day": None,
                        "status": "current",
                        "release_notes_uri": None,
                        "note": None,
                        "order": 0,
                        "links": {
                            "browser": str(browser_safarimobile_10.id),
                            "history_current": self.history_pk_str(
                                version_safarimobile_767),
                            "history": self.history_pks_str(
                                version_safarimobile_767),
                        }
                    },
                    {
                        "id": str(version_operamini_768.id),
                        "version": None,
                        "release_day": None,
                        "retirement_day": None,
                        "status": "current",
                        "release_notes_uri": None,
                        "note": None,
                        "order": 0,
                        "links": {
                            "browser": str(browser_operamini_11.id),
                            "history_current": self.history_pk_str(
                                version_operamini_768),
                            "history": self.history_pks_str(
                                version_operamini_768),
                        }
                    }
                ],
            },
            "links": {
                "browsers.history": {
                    "href": (
                        self.baseUrl + "/api/v1/historical_browsers/"
                        "{browsers.history}"),
                    "type": "historical_browsers"
                },
                "browsers.history_current": {
                    "href": (
                        self.baseUrl + "/api/v1/historical_browsers/"
                        "{browsers.history_current}"),
                    "type": "historical_browsers"
                },
                "features.children": {
                    "href": (
                        self.baseUrl + "/api/v1/features/"
                        "{features.children}"),
                    "type": "features"
                },
                "features.history": {
                    "href": (
                        self.baseUrl + "/api/v1/historical_features/"
                        "{features.history}"),
                    "type": "historical_features"
                },
                "features.history_current": {
                    "href": (
                        self.baseUrl + "/api/v1/historical_features/"
                        "{features.history_current}"),
                    "type": "historical_features"
                },
                "features.parent": {
                    "href": (
                        self.baseUrl + "/api/v1/features/"
                        "{features.parent}"),
                    "type": "features"
                },
                "features.sections": {
                    "href": (
                        self.baseUrl + "/api/v1/sections/"
                        "{features.sections}"),
                    "type": "sections"
                },
                "features.supports": {
                    "href": (
                        self.baseUrl + "/api/v1/supports/"
                        "{features.supports}"),
                    "type": "supports"
                },
                "maturities.history": {
                    "href": (
                        self.baseUrl + "/api/v1/historical_maturities/"
                        "{maturities.history}"),
                    "type": "historical_maturities"
                },
                "maturities.history_current": {
                    "href": (
                        self.baseUrl + "/api/v1/historical_maturities/"
                        "{maturities.history_current}"),
                    "type": "historical_maturities"
                },
                "sections.history": {
                    "href": (
                        self.baseUrl + "/api/v1/historical_sections/"
                        "{sections.history}"),
                    "type": "historical_sections"
                },
                "sections.history_current": {
                    "href": (
                        self.baseUrl + "/api/v1/historical_sections/"
                        "{sections.history_current}"),
                    "type": "historical_sections"
                },
                "sections.specification": {
                    "href": (
                        self.baseUrl + "/api/v1/specifications/"
                        "{sections.specification}"),
                    "type": "specifications"
                },
                "specifications.history": {
                    "href": (
                        self.baseUrl + "/api/v1/historical_specifications/"
                        "{specifications.history}"),
                    "type": "historical_specifications"
                },
                "specifications.history_current": {
                    "href": (
                        self.baseUrl + "/api/v1/historical_specifications/"
                        "{specifications.history_current}"),
                    "type": "historical_specifications"
                },
                "specifications.maturity": {
                    "href": (
                        self.baseUrl + "/api/v1/maturities/"
                        "{specifications.maturity}"),
                    "type": "maturities"
                },
                "supports.feature": {
                    "href": (
                        self.baseUrl + "/api/v1/features/"
                        "{supports.feature}"),
                    "type": "features"
                },
                "supports.history": {
                    "href": (
                        self.baseUrl + "/api/v1/historical_supports/"
                        "{supports.history}"),
                    "type": "historical_supports"
                },
                "supports.history_current": {
                    "href": (
                        self.baseUrl + "/api/v1/historical_supports/"
                        "{supports.history_current}"),
                    "type": "historical_supports"
                },
                "supports.version": {
                    "href": (
                        self.baseUrl + "/api/v1/versions/"
                        "{supports.version}"),
                    "type": "versions"
                },
                "versions.browser": {
                    "href": (
                        self.baseUrl + "/api/v1/browsers/"
                        "{versions.browser}"),
                    "type": "browsers"
                },
                "versions.history": {
                    "href": (
                        self.baseUrl + "/api/v1/historical_versions/"
                        "{versions.history}"),
                    "type": "historical_versions"
                },
                "versions.history_current": {
                    "href": (
                        self.baseUrl + "/api/v1/historical_versions/"
                        "{versions.history_current}"),
                    "type": "historical_versions"
                },
            },
            "meta": {
                "compat_table": {
                    "tabs": [
                        {
                            "name": {
                                "en": "Desktop Browsers"
                            },
                            "browsers": [
                                str(browser_chrome_1.pk),
                                str(browser_firefox_2.pk),
                                str(browser_ie_3.pk),
                                str(browser_opera_4.pk),
                                str(browser_safari_5.pk),
                            ]
                        },
                        {
                            "name": {
                                "en": "Mobile Browsers"
                            },
                            "browsers": [
                                str(browser_android_6.pk),
                                str(browser_ffmobile_7.pk),
                                str(browser_iephone_8.pk),
                                str(browser_operamini_11.pk),
                                str(browser_operamobile_9.pk),
                                str(browser_safarimobile_10.pk),
                            ]
                        }
                    ],
                    "supports": {
                        str(feature_816.pk): {},
                        str(feature_row_191.pk): {
                            str(browser_chrome_1.pk): [
                                str(support_chrome_358.pk)],
                            str(browser_firefox_2.pk): [
                                str(support_firefox_359.pk)],
                            str(browser_ie_3.pk): [
                                str(support_ie_360.pk)],
                            str(browser_opera_4.pk): [
                                str(support_opera_361.pk)],
                            str(browser_safari_5.pk): [
                                str(support_safari_362.pk)],
                            str(browser_android_6.pk): [
                                str(support_android_363.pk)],
                            str(browser_ffmobile_7.pk): [
                                str(support_ffmobile_364.pk)],
                            str(browser_iephone_8.pk): [
                                str(support_iephone_365.pk)],
                            str(browser_operamini_11.pk): [
                                str(support_operamini_368.pk)],
                            str(browser_operamobile_9.pk): [
                                str(support_operamobile_366.pk)],
                            str(browser_safarimobile_10.pk): [
                                str(support_safarimobile_367.pk)],
                        }
                    },
                    "pagination": {
                        "linked.features": {
                            "previous": None,
                            "next": None,
                            "count": 1,
                        },
                    },
                    "languages": ['en', 'ja', 'jp'],
                    "footnotes": {},
                }
            }
        }
        actual_json = loads(response.content.decode('utf-8'))
        self.assertDataEqual(expected_json, actual_json)

        response = self.client.get(url + '.html')
        expected = """\
<section class="webplatformcompat-feature" lang="en-us" data-type="features"\
 data-id="%(f_id)s">
<h2>Specifications</h2>
<table class="specifications-table">
  <thead>
    <tr>
      <th>Specification</th>
      <th>Status</th>
      <th>Comment</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>
        <a href="http://www.whatwg.org/specs/web-apps/current-work/\
multipage/sections.html#the-address-element">
          <span lang="en">WHATWG HTML Living Standard</span>
          <br>
          <small><span lang="en">4.3.10</span> \
<span lang="en">The address element</span></small>
        </a>
      </td>
      <td>
        <span class="maturity-Living" lang="en">Living Standard</span>
      </td>
      <td>
      </td>
    </tr>
    <tr>
      <td>
        <a href="http://www.w3.org/TR/html5/sections.html#the-address-element">
          <span lang="en">HTML5</span>
          <br>
          <small><span lang="en">4.3.9</span> \
<span lang="en">The address element</span></small>
        </a>
      </td>
      <td>
        <span class="maturity-PR" lang="en">Proposed Recommendation</span>
      </td>
      <td>
      </td>
    </tr>
    <tr>
      <td>
        <a href="http://www.w3.org/TR/html401/struct/global.html#h-7.5.6">
          <span lang="en">HTML 4.01 Specification</span>
          <br>
          <small><span lang="en">7.5.6</span> \
<span lang="en">The ADDRESS element</span></small>
        </a>
      </td>
      <td>
        <span class="maturity-REC" lang="en">Recommendation</span>
      </td>
      <td>
      </td>
    </tr>
  </tbody>
</table>

<h2>Browser compatibility</h2>

<h3>Desktop Browsers</h3>
<table class="compat-table">
  <thead>
    <tr>
      <th>Feature</th>
      <th><span lang="en">Chrome</span></th>
      <th><span lang="en">Firefox</span></th>
      <th><span lang="en">Internet Explorer</span></th>
      <th><span lang="en">Opera</span></th>
      <th><span lang="en">Safari</span></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><span lang="en">Basic support</span></td>
      <td>
        (yes)
      </td>
      <td>
        1.0
      </td>
      <td>
        1.0
      </td>
      <td>
        5.12
      </td>
      <td>
        1.0
      </td>
    </tr>
  </tbody>
</table>

<h3>Mobile Browsers</h3>
<table class="compat-table">
  <thead>
    <tr>
      <th>Feature</th>
      <th><span lang="en">Android</span></th>
      <th><span lang="en">Firefox Mobile</span></th>
      <th><span lang="en">IE Mobile</span></th>
      <th><span lang="en">Opera Mini</span></th>
      <th><span lang="en">Opera Mobile</span></th>
      <th><span lang="en">Safari Mobile</span></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><span lang="en">Basic support</span></td>
      <td>
        (yes)
      </td>
      <td>
        1.0
      </td>
      <td>
        (yes)
      </td>
      <td>
        (yes)
      </td>
      <td>
        (yes)
      </td>
      <td>
        (yes)
      </td>
    </tr>
  </tbody>
</table>

</section>
<section class="webplatformcompat-feature-meta" lang="en-us">
<p><em>Showing language "en-us". Other languages:</em></p>
<ul>
  <li><a href="/api/v1/view_features/%(f_id)s?format=html&lang=en">en</a></li>
  <li><a href="/api/v1/view_features/%(f_id)s?format=html&lang=ja">ja</a></li>
  <li><a href="/api/v1/view_features/%(f_id)s?format=html&lang=jp">jp</a></li>
</ul>
</section>
""" % {'f_id': feature_816.id}
        self.assertDataEqual(expected, response.content.decode('utf-8'))
        self.assertContains(response, expected, html=True)


class TestViewFeatureUpdates(APITestCase):
    """Test PUT to a ViewFeature detail"""
    longMessage = True

    def setUp(self):
        self.feature = self.create(
            Feature, slug='feature', name={'en': "Feature"})
        self.browser = self.create(
            Browser, slug='browser', name={'en': 'Browser'})
        self.version = self.create(
            Version, browser=self.browser, version='1.0')
        self.maturity = self.create(Maturity, slug='M', name={"en": 'Mature'})
        self.spec = self.create(
            Specification, slug='spec', mdn_key='SPEC', name={'en': 'Spec'},
            uri={'en': 'http://example.com/Spec'}, maturity=self.maturity)

        self.browser_data = {
            "id": str(self.browser.id), "slug": self.browser.slug,
            "name": self.browser.name, "note": None,
            "links": {"versions": [str(self.version.id)]}}
        self.version_data = {
            "id": str(self.version.id), "version": self.version.version,
            "release_day": None, "retirement_day": None, "note": None,
            "status": "unknown", "release_notes_uri": None,
            "links": {"browser": str(self.browser.id)}}
        self.maturity_data = {
            "id": str(self.maturity.id), "slug": self.maturity.slug,
            "name": self.maturity.name}
        self.spec_data = {
            "id": str(self.spec.id), "slug": self.spec.slug,
            "mdn_key": self.spec.mdn_key, "name": self.spec.name,
            "uri": self.spec.uri,
            "links": {"maturity": str(self.maturity.id), "sections": []}}
        self.url = reverse(
            'viewfeatures-detail', kwargs={'pk': self.feature.pk})

    def json_api(self, feature_data=None, meta=None, **resources):
        base = {'features': {"id": str(self.feature.id)}}
        if feature_data:
            base['features'].update(feature_data)
        if meta:
            base['meta'] = meta
        if resources:
            base['linked'] = {}
        for name, values in resources.items():
            base['linked'][name] = values
        return dumps(base)

    def test_post_just_feature(self):
        data = {
            "mdn_uri": {
                "en": "https://developer.mozilla.org/en-US/docs/feature",
                "fr": "https://developer.mozilla.org/fr/docs/feature",
            },
            "name": {
                "en": "The Feature",
                "fr": "Le Feature",
            }
        }
        json_data = self.json_api(data)
        response = self.client.put(
            self.url, data=json_data, content_type="application/vnd.api+json")
        self.assertEqual(response.status_code, 200, response.content)
        f = Feature.objects.get(id=self.feature.id)
        self.assertEqual(f.mdn_uri, data['mdn_uri'])
        self.assertEqual(f.name, data['name'])

    def test_post_add_subfeature(self):
        subfeature = {
            "id": "_new", "slug": "subfeature", "name": {"en": "Sub Feature"},
            "links": {"parent": str(self.feature.pk)}}
        json_data = self.json_api(features=[subfeature])
        response = self.client.put(
            self.url, data=json_data, content_type="application/vnd.api+json")
        self.assertEqual(response.status_code, 200, response.content)
        subfeature = Feature.objects.get(slug='subfeature')
        self.assertEqual(subfeature.parent, self.feature)
        feature = Feature.objects.get(id=self.feature.id)
        self.assertEqual(list(feature.children.all()), [subfeature])

    def test_post_add_second_subfeature(self):
        sf1 = self.create(
            Feature, slug='sf1', name={'en': 'sf1'}, parent=self.feature)
        sf2_data = {
            "id": "_sf2", "slug": "sf2", "name": {"en": "Sub Feature 2"},
            "links": {"parent": str(self.feature.pk)}}
        json_data = self.json_api(features=[sf2_data])
        response = self.client.put(
            self.url, data=json_data, content_type="application/vnd.api+json")
        self.assertEqual(response.status_code, 200, response.content)
        sf2 = Feature.objects.get(slug='sf2')
        self.assertEqual(sf2.parent, self.feature)
        feature = Feature.objects.get(id=self.feature.id)
        self.assertEqual(list(feature.children.all()), [sf1, sf2])

    def test_post_update_existing_subfeature(self):
        subfeature = self.create(
            Feature, slug='subfeature', name={'en': 'subfeature'},
            parent=self.feature)
        subfeature_data = {
            "id": str(subfeature.id), "slug": "subfeature",
            "name": {"en": "subfeature 1"},
            "links": {"parent": str(self.feature.pk)}}
        json_data = self.json_api(features=[subfeature_data])
        response = self.client.put(
            self.url, data=json_data, content_type="application/vnd.api+json")
        self.assertEqual(response.status_code, 200, response.content)
        subfeature = Feature.objects.get(id=subfeature.id)
        self.assertEqual(subfeature.parent, self.feature)
        self.assertEqual(subfeature.name, {"en": "subfeature 1"})
        feature = Feature.objects.get(id=self.feature.id)
        self.assertEqual(list(feature.children.all()), [subfeature])

    def test_post_add_subsupport(self):
        subfeature_data = {
            "id": "_new", "slug": "subfeature", "name": {"en": "Sub Feature"},
            "links": {"parent": str(self.feature.pk)}}
        support_data = {
            "id": "_new_yes", "support": "yes",
            "links": {"version": str(self.version.id), "feature": "_new"}}
        json_data = self.json_api(
            features=[subfeature_data], supports=[support_data],
            versions=[self.version_data], browsers=[self.browser_data])
        response = self.client.put(
            self.url, data=json_data, content_type="application/vnd.api+json")
        self.assertEqual(response.status_code, 200, response.content)
        subfeature = Feature.objects.get(slug='subfeature')
        self.assertEqual(subfeature.parent, self.feature)
        self.assertEqual(subfeature.name, {"en": "Sub Feature"})
        supports = subfeature.supports.all()
        self.assertEqual(1, len(supports))
        support = supports[0]
        self.assertEqual(support.version, self.version)
        self.assertEqual('yes', support.support)

    def test_post_no_change(self):
        subfeature = self.create(
            Feature, slug='subfeature', name={'en': 'subfeature'},
            parent=self.feature)
        history_count = subfeature.history.all().count()
        subfeature_data = {
            'slug': 'subfeature', 'mdn_uri': None,
            'experimental': False, 'standardized': True, 'stable': True,
            'obsolete': False, 'name': {'en': 'subfeature'},
            'links': {'parent': str(self.feature.id), 'sections': []}}
        json_data = self.json_api(
            features=[subfeature_data], meta={'not': 'used'})
        response = self.client.put(
            self.url, data=json_data, content_type="application/vnd.api+json")
        self.assertEqual(response.status_code, 200, response.content)
        subfeature = Feature.objects.get(slug='subfeature')
        self.assertEqual(subfeature.parent, self.feature)
        self.assertEqual(subfeature.name, {"en": "subfeature"})
        self.assertEqual(history_count, subfeature.history.all().count())

    def test_existing_changeset(self):
        response = self.client.post(
            reverse('changeset-list'), dumps({}),
            content_type="application/vnd.api+json")
        self.assertEqual(201, response.status_code, response.content)
        response_json = loads(response.content.decode('utf-8'))
        changeset_id = response_json['changesets']['id']
        c = '?changeset=%s' % changeset_id

        subfeature = {
            "id": "_new", "slug": "subfeature", "name": {"en": "Sub Feature"},
            "links": {"parent": str(self.feature.pk)}}
        json_data = self.json_api(features=[subfeature])
        response = self.client.put(
            self.url + c, data=json_data,
            content_type="application/vnd.api+json")
        self.assertEqual(response.status_code, 200, response.content)
        subfeature = Feature.objects.get(slug='subfeature')
        self.assertEqual(subfeature.parent, self.feature)
        self.assertEqual(
            int(changeset_id),
            subfeature.history.last().history_changeset_id)

        close = {'changesets': {'id': changeset_id, 'close': True}}
        response = self.client.post(
            reverse('changeset-detail', kwargs={'pk': changeset_id}),
            dumps(close), content_type="application/vnd.api+json")

    def test_invalid_subfeature(self):
        subfeature = {
            "id": "_new", "slug": None, "name": {"en": "Sub Feature"},
            "links": {"parent": str(self.feature.pk)}}
        json_data = self.json_api(features=[subfeature])
        response = self.client.put(
            self.url, data=json_data,
            content_type="application/vnd.api+json")
        self.assertEqual(response.status_code, 400, response.content)
        expected_error = {
            'errors': [{
                "status": "400", "path": "/linked.features.0.slug",
                "detail": "This field is required.",
            }]
        }
        actual_error = loads(response.content.decode('utf-8'))
        self.assertEqual(expected_error, actual_error)

    def test_invalid_support(self):
        subfeature_data = {
            "id": "_new", "slug": "subfeature", "name": {"en": "Sub Feature"},
            "links": {"parent": str(self.feature.pk)}}
        support_data = {
            "id": "_new_maybe", "support": "maybe",
            "links": {"version": str(self.version.id), "feature": "_new"}}
        json_data = self.json_api(
            features=[subfeature_data], supports=[support_data],
            versions=[self.version_data], browsers=[self.browser_data])
        response = self.client.put(
            self.url, data=json_data, content_type="application/vnd.api+json")
        self.assertEqual(response.status_code, 400, response.content)
        expected_error = {
            'errors': [{
                "status": "400", "path": "/linked.supports.0.support",
                "detail": (
                    "Select a valid choice. maybe is not one of the available"
                    " choices."),
            }]
        }
        actual_error = loads(response.content.decode('utf-8'))
        self.assertEqual(expected_error, actual_error)
        self.assertFalse(Feature.objects.filter(slug='subfeature').exists())

    def test_add_section(self):
        section_data = {
            "id": "_section", "name": {"en": "Section"},
            "links": {
                "specification": str(self.spec.id),
                "features": [str(self.feature.id)],
            }}
        json_data = self.json_api(
            {'sections': ['_section']}, sections=[section_data],
            specifications=[self.spec_data], maturities=[self.maturity_data])
        response = self.client.put(
            self.url, data=json_data, content_type="application/vnd.api+json")
        self.assertEqual(response.status_code, 200, response.content)
        section = Section.objects.get()
        self.assertEqual([self.feature], list(section.features.all()))

    def test_add_support_to_target(self):
        support_data = {
            "id": "_yes", "support": "yes",
            "links": {
                "version": str(self.version.id),
                "feature": str(self.feature.id),
            }}
        json_data = self.json_api(
            supports=[support_data], versions=[self.version_data],
            browsers=[self.browser_data])
        response = self.client.put(
            self.url, data=json_data, content_type="application/vnd.api+json")
        self.assertEqual(response.status_code, 200, response.content)
        support = Support.objects.get()
        self.assertEqual(self.version, support.version)
        self.assertEqual(self.feature, support.feature)
        self.assertEqual('yes', support.support)

    def test_to_native_none(self):
        # This is used by the DRF browsable API
        self.assertIsNone(ViewFeatureExtraSerializer().to_native(None))

    def test_top_level_feature_is_error(self):
        subfeature = {
            "id": "_new", "slug": 'slug', "name": {"en": "Sub Feature"},
            "links": {"parent": None}}
        json_data = self.json_api(features=[subfeature])
        response = self.client.put(
            self.url, data=json_data,
            content_type="application/vnd.api+json")
        self.assertEqual(response.status_code, 400, response.content)
        expected_error = {
            'errors': [{
                "status": "400", "path": "/linked.features.0.parent",
                "detail": (
                    "Feature must be a descendant of feature %s." %
                    self.feature.id),
            }]
        }
        actual_error = loads(response.content.decode('utf-8'))
        self.assertEqual(expected_error, actual_error)

    def test_other_feature_is_error(self):
        other = self.create(
            Feature, slug='other', name={'en': "Other"})
        subfeature = {
            "id": "_new", "slug": 'slug', "name": {"en": "Sub Feature"},
            "links": {"parent": str(other.id)}}
        json_data = self.json_api(features=[subfeature])
        response = self.client.put(
            self.url, data=json_data,
            content_type="application/vnd.api+json")
        self.assertEqual(response.status_code, 400, response.content)
        expected_error = {
            'errors': [{
                "status": "400", "path": "/linked.features.0.parent",
                "detail": (
                    "Feature must be a descendant of feature %s." %
                    self.feature.id),
            }]
        }
        actual_error = loads(response.content.decode('utf-8'))
        self.assertEqual(expected_error, actual_error)

    def test_changed_maturity_is_error(self):
        section_data = {
            "id": "_section", "name": {"en": "Section"},
            "links": {
                "specification": str(self.spec.id),
                "features": [str(self.feature.id)],
            }
        }
        maturity_data = self.maturity_data.copy()
        maturity_data['name']['en'] = "New Maturity Name"
        json_data = self.json_api(
            {'sections': ['_section']}, sections=[section_data],
            specifications=[self.spec_data], maturities=[maturity_data])
        response = self.client.put(
            self.url, data=json_data, content_type="application/vnd.api+json")
        self.assertEqual(response.status_code, 400, response.content)
        expected_error = {
            'errors': [{
                "status": "400", "path": "/linked.maturities.0.name",
                "detail": (
                    'Field can not be changed from {"en": "Mature"} to'
                    ' {"en": "New Maturity Name"} as part of this update.'
                    ' Update the resource by itself, and try again.'),
            }]
        }
        actual_error = loads(response.content.decode('utf-8'))
        self.assertEqual(expected_error, actual_error)

    def test_new_specification_is_error(self):
        section_data = {
            "id": "_section", "name": {"en": "Section"},
            "links": {
                "specification": "_NEW", "features": [str(self.feature.id)]}}
        spec_data = {
            "id": "_NEW", "slug": "NEW", "mdn_key": "",
            "name": {"en": "New Specification"},
            "uri": {"en": "https://example.com/new"},
            "links": {"maturity": str(self.maturity.id)}}
        json_data = self.json_api(
            {'sections': ['_section']}, sections=[section_data],
            specifications=[spec_data], maturities=[self.maturity_data])
        response = self.client.put(
            self.url, data=json_data, content_type="application/vnd.api+json")
        self.assertEqual(response.status_code, 400, response.content)
        expected_error = {
            'errors': [{
                "status": "400", "path": "/linked.specifications.0.id",
                "detail": (
                    'Resource can not be created as part of this update.'
                    ' Create first, and try again.'),
            }]
        }
        actual_error = loads(response.content.decode('utf-8'))
        self.assertEqual(expected_error, actual_error)

    def test_omitted_specification_field_is_error(self):
        section_data = {
            "id": "_section", "name": {"en": "Section"},
            "links": {
                "specification": str(self.spec.id),
                "features": [str(self.feature.id)],
            }}
        spec_data = self.spec_data.copy()
        del spec_data['links']['sections']
        json_data = self.json_api(
            {'sections': ['_section']}, sections=[section_data],
            specifications=[spec_data], maturities=[self.maturity_data])
        response = self.client.put(
            self.url, data=json_data, content_type="application/vnd.api+json")
        self.assertEqual(response.status_code, 400, response.content)
        expected_error = {
            'errors': [{
                "status": "400", "path": "/linked.specifications.0.sections",
                "detail": 'Field was omitted, but should be set to []'
            }]
        }
        actual_error = loads(response.content.decode('utf-8'))
        self.assertEqual(expected_error, actual_error)

    def test_new_version_is_error(self):
        support_data = {
            "id": "_yes", "support": "yes",
            "links": {
                "version": "_NEW", "feature": str(self.feature.id),
            }}
        version_data = {
            "id": "_NEW", "version": "1.0", "note": None,
            "links": {"browser": str(self.browser.id)}}
        json_data = self.json_api(
            supports=[support_data], versions=[version_data],
            browsers=[self.browser_data])
        response = self.client.put(
            self.url, data=json_data, content_type="application/vnd.api+json")
        self.assertEqual(response.status_code, 400, response.content)
        expected_error = {
            'errors': [{
                "status": "400", "path": "/linked.versions.0.id",
                "detail": (
                    'Resource can not be created as part of this update.'
                    ' Create first, and try again.'),
            }]
        }
        actual_error = loads(response.content.decode('utf-8'))
        self.assertEqual(expected_error, actual_error)


class TestDjangoResourceClient(TestCase):
    def setUp(self):
        self.client = DjangoResourceClient()

    def test_url_maturity_list(self):
        expected = reverse('maturity-list')
        self.assertEqual(expected, self.client.url('maturities'))

    def test_url_feature_detail(self):
        expected = reverse('feature-detail', kwargs={'pk': '55'})
        self.assertEqual(expected, self.client.url('features', '55'))

    def test_delete(self):
        self.assertRaises(
            NotImplementedError, self.client.delete, 'features', '666')
