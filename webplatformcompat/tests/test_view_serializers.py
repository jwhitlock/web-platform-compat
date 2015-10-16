#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for web-platform-compat.view_serializers.

TODO: Refactor this code to be more unit tests than integration tests.
This should wait until bug 1153288 (Reimplement DRF serializers and renderer)
"""
from __future__ import unicode_literals
from json import dumps, loads

from django.core.urlresolvers import reverse
from django.test.utils import override_settings

from webplatformcompat.history import Changeset
from webplatformcompat.models import (
    Browser, Feature, Maturity, Section, Specification, Support, Version)
from webplatformcompat.view_serializers import (
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

    def setup_minimal(self):
        feature = self.create(Feature, slug='feature')
        browser = self.create(
            Browser, slug='chrome_desktop', name={'en': 'Browser'})
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
        return {
            'feature': feature,
            'browser': browser,
            'version': version,
            'support': support,
            'maturity': maturity,
            'specification': specification,
            'section': section,
        }

    def test_minimal(self):
        """Get a minimal but complete viewfeature."""
        resources = self.setup_minimal()
        browser = resources['browser']
        feature = resources['feature']
        section = resources['section']
        support = resources['support']
        maturity = resources['maturity']
        version = resources['version']
        specification = resources['specification']
        url = reverse(
            'viewfeatures-detail', kwargs={'pk': feature.pk})
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
                    "slug": "chrome_desktop",
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
                    "child_pages": False,
                    "pagination": {
                        "linked.features": {
                            "previous": None,
                            "next": None,
                            "count": 0,
                        },
                    },
                    "languages": ['en'],
                    "notes": {},
                }
            }
        }
        actual_json = loads(response.content.decode('utf-8'))
        self.assertDataEqual(expected_json, actual_json)

    def test_canonical_removed(self):
        """zxx (non-linguistic, canonical) does not appear in languages."""
        resources = self.setup_minimal()
        feature = resources['feature']
        del self.changeset
        self.create(Feature, parent=feature, name='{"zxx": "canonical"}')
        url = reverse(
            'viewfeatures-detail', kwargs={'pk': feature.pk})
        response = self.client.get(url)
        actual_json = loads(response.content.decode('utf-8'))
        actual_langs = actual_json['meta']['compat_table']['languages']
        self.assertEqual(['en'], actual_langs)

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

    def setup_feature_tree(self):
        feature = self.create(Feature, slug='feature')
        self.create(Feature, slug='child1', parent=feature)
        self.create(Feature, slug='child2', parent=feature)
        self.create(Feature, slug='child3', parent=feature)
        self.changeset.closed = True
        self.changeset.save()
        return feature

    @override_settings(PAGINATE_VIEW_FEATURE=2)
    def test_large_feature_tree(self):
        feature = self.setup_feature_tree()
        url = reverse('viewfeatures-detail', kwargs={'pk': feature.pk})
        response = self.client.get(url, {'child_pages': True})
        actual_json = loads(response.content.decode('utf-8'))
        expected_pagination = {
            'linked.features': {
                'previous': None,
                'next': self.baseUrl + url + '?child_pages=1&page=2',
                'count': 3,
            }
        }
        actual_pagination = actual_json['meta']['compat_table']['pagination']
        self.assertDataEqual(expected_pagination, actual_pagination)

        response = self.client.get(url, {'child_pages': True, 'page': 2})
        actual_json = loads(response.content.decode('utf-8'))
        expected_pagination = {
            'linked.features': {
                'previous': self.baseUrl + url + '?child_pages=1&page=1',
                'next': None,
                'count': 3,
            }
        }
        actual_pagination = actual_json['meta']['compat_table']['pagination']
        self.assertDataEqual(expected_pagination, actual_pagination)

    @override_settings(PAGINATE_VIEW_FEATURE=2)
    def test_large_feature_tree_html(self):
        feature = self.setup_feature_tree()
        url = reverse(
            'viewfeatures-detail', kwargs={'pk': feature.pk, 'format': 'html'})
        response = self.client.get(url, {'child_pages': True})
        next_url = self.baseUrl + url + "?child_pages=1&page=2"
        expected = '<a href="%s">next page</a>' % next_url
        self.assertContains(response, expected, html=True)

    @override_settings(PAGINATE_VIEW_FEATURE=4)
    def test_just_right_feature_tree(self):
        feature = self.setup_feature_tree()
        url = reverse('viewfeatures-detail', kwargs={'pk': feature.pk})
        response = self.client.get(url, {'child_pages': True})
        actual_json = loads(response.content.decode('utf-8'))
        expected_pagination = {
            'linked.features': {
                'previous': None,
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
        support['note'] = None
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

    def test_slug(self):
        feature = self.create(Feature, slug='feature')
        browser = self.create(Browser, slug='chrome', name={'en': 'Browser'})
        version = self.create(Version, browser=browser, status='current')
        self.create(Support, version=version, feature=feature)
        self.changeset.closed = True
        self.changeset.save()

        url = reverse('viewfeatures-detail', kwargs={'pk': 'feature'})
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)
        self.assertEqual(feature.id, response.data['id'])

    def test_slug_not_found(self):
        url = reverse('viewfeatures-detail', kwargs={'pk': 'feature'})
        response = self.client.get(url)
        self.assertEqual(404, response.status_code)


class TestViewFeatureUpdates(APITestCase):
    """Test PUT to a ViewFeature detail"""
    longMessage = True

    def setUp(self):
        self.feature = self.create(
            Feature, slug='feature', name={'en': "Feature"})
        self.browser = self.create(
            Browser, slug='browser', name={'en': 'Browser'})
        self.version = self.create(
            Version, browser=self.browser, version='1.0',
            release_day='2015-02-17')
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
            "release_day": '2015-02-17', "retirement_day": None, "note": None,
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
        self.assertEqual(list(feature.get_descendants()), [subfeature])

    def test_post_add_second_subfeature(self):
        from django.db import connection
        old_debug = connection.force_debug_cursor
        connection.force_debug_cursor = True
        try:
            sf1 = self.create(
                Feature, slug='sf1', name={'en': 'sf1'}, parent=self.feature)
            sf2_data = {
                "id": "_sf2", "slug": "sf2", "name": {"en": "Sub Feature 2"},
                "links": {"parent": str(self.feature.pk)}}
            json_data = self.json_api(features=[sf2_data])
            response = self.client.put(
                self.url, data=json_data,
                content_type="application/vnd.api+json")
            self.assertEqual(response.status_code, 200, response.content)
            sf2 = Feature.objects.get(slug='sf2')
            self.assertEqual(sf2.parent, self.feature)
            feature = Feature.objects.get(id=self.feature.id)
            actual = list(feature.children.all())
            if actual != [sf1, sf2]:  # pragma: nocover
                # Debug occasional test failure
                def report(f, prefix='Feature'):
                    attrs = ['id', 'lft', 'rght', 'tree_id', 'level', 'parent']
                    return prefix + ': ' + ', '.join(
                        ['%s=%s' % (a, getattr(f, a)) for a in attrs])
                msg_lines = [
                    "=" * 70,
                    'Unexpected failure in test_post_add_second_subfeature.',
                    'Report at:',
                    ' https://bugzilla.mozilla.org/show_bug.cgi?id=1159337',
                    'DB queries:'
                ]
                msg_lines.extend([str(q) for q in connection.queries])
                msg_lines.extend([
                    'Features:',
                    report(self.feature, 'parent'),
                    report(feature, 'parent from DB'),
                    report(sf1, 'sf1'),
                    report(sf2, 'sf2'),
                    "=" * 70]
                )
                print('\n'.join(msg_lines))
            self.assertEqual(list(feature.children.all()), [sf1, sf2])
        finally:
            connection.force_debug_cursor = old_debug

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
                "detail": "This field may not be null.",
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
                "detail": '"maybe" is not a valid choice.',
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

    def test_to_reprepsentation_none(self):
        # This is used by the DRF browsable API
        self.assertIsNone(ViewFeatureExtraSerializer().to_representation(None))

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

    def test_open_changeset(self):
        self.client.open_changeset()
        self.assertFalse(Changeset.objects.exists())

    def test_close_changeset(self):
        self.client.close_changeset()
        self.assertFalse(Changeset.objects.exists())

    def test_delete(self):
        self.assertRaises(
            NotImplementedError, self.client.delete, 'features', '666')
