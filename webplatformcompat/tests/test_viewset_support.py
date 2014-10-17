#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for `web-platform-compat.viewsets.SupportViewSet` class.
"""
from __future__ import unicode_literals
from json import loads

from django.core.urlresolvers import reverse

from webplatformcompat.models import Browser, Feature, Support, Version

from .base import APITestCase


class TestSupportViewSet(APITestCase):
    def test_get_minimal(self):
        browser = self.create(Browser)
        version = self.create(Version, browser=browser)
        feature = self.create(Feature)
        support = self.create(Support, version=version, feature=feature)
        url = reverse('support-detail', kwargs={'pk': support.pk})
        history_pk = support.history.all()[0].pk
        response = self.client.get(url, HTTP_ACCEPT="application/vnd.api+json")
        self.assertEqual(200, response.status_code, response.data)

        expected_data = {
            'id': support.id,
            'support': 'yes',
            'prefix': None,
            'prefix_mandatory': False,
            'alternate_name': None,
            'alternate_mandatory': False,
            'requires_config': None,
            'default_config': None,
            'protected': False,
            'note': None,
            'footnote': None,
            'version': version.id,
            'feature': feature.id,
            'history': [history_pk],
            'history_current': history_pk,
        }
        self.assertDataEqual(expected_data, response.data)

        expected_json = {
            "supports": {
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
                    "history_current": str(history_pk),
                    "history": [str(history_pk)],
                },
            },
            "links": {
                "supports.version": {
                    "href": (
                        self.baseUrl + "/api/v1/versions/{supports.version}"),
                    "type": "versions",
                },
                "supports.feature": {
                    "href": (
                        self.baseUrl + "/api/v1/features/{supports.feature}"),
                    "type": "features",
                },
                "supports.history_current": {
                    "href": (
                        self.baseUrl + "/api/v1/historical_supports/"
                        "{supports.history_current}"),
                    "type": "historical_supports",
                },
                "supports.history": {
                    "href": (
                        self.baseUrl + "/api/v1/historical_supports/"
                        "{supports.history}"),
                    "type": "historical_supports",
                },
            }
        }
        actual_json = loads(response.content.decode('utf-8'))
        self.assertDataEqual(expected_json, actual_json)

    def test_get_prefix_and_config(self):
        browser = self.create(Browser, slug='firefox', name={'en': 'Firefox'})
        version = self.create(Version, browser=browser, version='34')
        feature = self.create(Feature, name={'zxx': 'RTCPeerConnection'})
        support = self.create(
            Support, version=version, feature=feature,
            prefix='moz', prefix_mandatory=True,
            requires_config='media.peerconnection.enabled=on',
            default_config='media.peerconnection.enabled=on')
        url = reverse('support-detail', kwargs={'pk': support.pk})
        history_pk = support.history.all()[0].pk
        response = self.client.get(url, HTTP_ACCEPT="application/vnd.api+json")
        self.assertEqual(200, response.status_code, response.data)

        expected_data = {
            'id': support.id,
            'support': 'yes',
            'prefix': 'moz',
            'prefix_mandatory': True,
            'alternate_name': None,
            'alternate_mandatory': False,
            'requires_config': 'media.peerconnection.enabled=on',
            'default_config': 'media.peerconnection.enabled=on',
            'protected': False,
            'note': None,
            'footnote': None,
            'version': version.id,
            'feature': feature.id,
            'history': [history_pk],
            'history_current': history_pk,
        }
        self.assertDataEqual(expected_data, response.data)

        expected_json = {
            "supports": {
                "id": str(support.id),
                "support": "yes",
                "prefix": 'moz',
                "prefix_mandatory": True,
                "alternate_name": None,
                "alternate_mandatory": False,
                "requires_config": 'media.peerconnection.enabled=on',
                "default_config": 'media.peerconnection.enabled=on',
                "protected": False,
                "note": None,
                "footnote": None,
                "links": {
                    "version": str(version.id),
                    "feature": str(feature.id),
                    "history_current": str(history_pk),
                    "history": [str(history_pk)],
                },
            },
            "links": {
                "supports.version": {
                    "href": (
                        self.baseUrl + "/api/v1/versions/{supports.version}"),
                    "type": "versions",
                },
                "supports.feature": {
                    "href": (
                        self.baseUrl + "/api/v1/features/{supports.feature}"),
                    "type": "features",
                },
                "supports.history_current": {
                    "href": (
                        self.baseUrl + "/api/v1/historical_supports/"
                        "{supports.history_current}"),
                    "type": "historical_supports",
                },
                "supports.history": {
                    "href": (
                        self.baseUrl + "/api/v1/historical_supports/"
                        "{supports.history}"),
                    "type": "historical_supports",
                },
            }
        }
        actual_json = loads(response.content.decode('utf-8'))
        self.assertDataEqual(expected_json, actual_json)

    def test_filter_by_version(self):
        browser = self.create(Browser)
        version = self.create(Version, browser=browser, version='1.0')
        other_version = self.create(Version, browser=browser, version='2.0')
        feature = self.create(Feature)
        support = self.create(Support, version=version, feature=feature)
        self.create(Support, version=other_version, feature=feature)
        history_pk = support.history.all()[0].pk

        response = self.client.get(
            reverse('support-list'), {'version': str(version.id)})
        self.assertEqual(200, response.status_code, response.data)
        expected_data = {
            'count': 1,
            'previous': None,
            'next': None,
            'results': [{
                'id': support.id,
                'support': 'yes',
                'prefix': None,
                'prefix_mandatory': False,
                'alternate_name': None,
                'alternate_mandatory': False,
                'requires_config': None,
                'default_config': None,
                'protected': False,
                'note': None,
                'footnote': None,
                'version': version.id,
                'feature': feature.id,
                'history': [history_pk],
                'history_current': history_pk,
            }]}
        self.assertDataEqual(response.data, expected_data)

    def test_filter_by_features(self):
        browser = self.create(Browser)
        version = self.create(Version, browser=browser, version='1.0')
        feature = self.create(Feature, slug='feature')
        other_feature = self.create(Feature, slug='other_feature')
        support = self.create(Support, version=version, feature=feature)
        self.create(Support, version=version, feature=other_feature)
        history_pk = support.history.all()[0].pk

        response = self.client.get(
            reverse('support-list'), {'feature': str(feature.id)})
        self.assertEqual(200, response.status_code, response.data)
        expected_data = {
            'count': 1,
            'previous': None,
            'next': None,
            'results': [{
                'id': support.id,
                'support': 'yes',
                'prefix': None,
                'prefix_mandatory': False,
                'alternate_name': None,
                'alternate_mandatory': False,
                'requires_config': None,
                'default_config': None,
                'protected': False,
                'note': None,
                'footnote': None,
                'version': version.id,
                'feature': feature.id,
                'history': [history_pk],
                'history_current': history_pk,
            }]}
        self.assertDataEqual(response.data, expected_data)

    def test_post_empty(self):
        self.login_superuser()
        response = self.client.post(reverse('support-list'), {})
        self.assertEqual(400, response.status_code)
        expected_data = {
            "feature": ["This field is required."],
            "version": ["This field is required."],
        }
        self.assertDataEqual(response.data, expected_data)
