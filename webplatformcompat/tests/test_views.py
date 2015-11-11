#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for `web-platform-compat` views module."""
from json import loads

from django.core.urlresolvers import reverse

from .base import TestCase


class TestViews(TestCase):
    def test_home(self):
        response = self.client.get('')
        self.assertEqual(response.status_code, 200)

    def full_api_reverse(self, viewname):
        """Create a full URL for a namespaced API view."""
        return 'http://testserver' + self.api_reverse(viewname)

    def test_api_root(self):
        response = self.client.get(self.api_reverse('api-root'))
        expected = {
            'resources': {
                'browsers': self.full_api_reverse('browser-list'),
                'features': self.full_api_reverse('feature-list'),
                'maturities': self.full_api_reverse('maturity-list'),
                'specifications': self.full_api_reverse('specification-list'),
                'sections': self.full_api_reverse('section-list'),
                'supports': self.full_api_reverse('support-list'),
                'versions': self.full_api_reverse('version-list'),
            },
            'change_control': {
                'changesets': self.full_api_reverse('changeset-list'),
                'users': self.full_api_reverse('user-list'),
            },
            'history': {
                'historical_browsers': self.full_api_reverse(
                    'historicalbrowser-list'),
                'historical_features': self.full_api_reverse(
                    'historicalfeature-list'),
                'historical_maturities': self.full_api_reverse(
                    'historicalmaturity-list'),
                'historical_sections': self.full_api_reverse(
                    'historicalsection-list'),
                'historical_specifications': self.full_api_reverse(
                    'historicalspecification-list'),
                'historical_supports': self.full_api_reverse(
                    'historicalsupport-list'),
                'historical_versions': self.full_api_reverse(
                    'historicalversion-list'),
            },
            'views': {
                'view_features': self.full_api_reverse('viewfeatures-list')
            },
        }
        actual = loads(response.content.decode('utf-8'))
        self.assertDataEqual(expected, actual)

    def test_view_feature(self):
        response = self.client.get(
            reverse('view_feature', kwargs={'feature_id': 1}))
        self.assertEqual(response.status_code, 200)

    def test_browse_app(self):
        response = self.client.get(reverse('browse'))
        self.assertEqual(response.status_code, 200)
