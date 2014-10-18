#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for `web-platform-compat` views module.
"""
from json import loads

from django.core.urlresolvers import reverse

from .base import TestCase


class TestViews(TestCase):
    def test_home(self):
        response = self.client.get('')
        self.assertEqual(response.status_code, 200)

    def test_api_root(self):
        response = self.client.get(reverse('api-root'))
        expected = {
            'resources': {
                'browsers': self.reverse('browser-list'),
                'features': self.reverse('feature-list'),
                'maturities': self.reverse('maturity-list'),
                'supports': self.reverse('support-list'),
                'versions': self.reverse('version-list'),
            },
            'change-control': {
                'users': self.reverse('user-list'),
            },
            'history': {
                'historical_browsers': self.reverse('historicalbrowser-list'),
                'historical_features': self.reverse('historicalfeature-list'),
                'historical_maturities': self.reverse(
                    'historicalmaturity-list'),
                'historical_supports': self.reverse('historicalsupport-list'),
                'historical_versions': self.reverse('historicalversion-list'),
            },
            'views': {
                'view_features': self.reverse('viewfeatures-list')
            },
        }
        actual = loads(response.content.decode('utf-8'))
        self.assertDataEqual(expected, actual)
