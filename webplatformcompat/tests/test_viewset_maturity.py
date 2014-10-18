#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for `web-platform-compat.viewsets.MaturityViewSet` class.
"""
from __future__ import unicode_literals
from json import loads

from django.core.urlresolvers import reverse

from webplatformcompat.models import Maturity

from .base import APITestCase


class TestMaturityViewSet(APITestCase):
    def test_get(self):
        name = {
            'en-US': 'Draft',
            'ja': u'\u30c9\u30e9\u30d5\u30c8',
            'de': 'Entwurf',
            'ru': u'\u0427\u0435\u0440\u043d\u043e\u0432\u0438\u043a',
        }
        maturity = self.create(Maturity, key='Draft', name=name)
        url = reverse('maturity-detail', kwargs={'pk': maturity.pk})
        fh_pk = maturity.history.all()[0].pk
        response = self.client.get(url, HTTP_ACCEPT="application/vnd.api+json")
        self.assertEqual(200, response.status_code, response.data)

        expected_data = {
            'id': maturity.id,
            'key': 'Draft',
            'name': {
                'en-US': 'Draft',
                'ja': u'\u30c9\u30e9\u30d5\u30c8',
                'de': 'Entwurf',
                'ru': u'\u0427\u0435\u0440\u043d\u043e\u0432\u0438\u043a',
            },
            'history': [fh_pk],
            'history_current': fh_pk,
        }
        self.assertDataEqual(expected_data, response.data)

        expected_json = {
            "maturities": {
                "id": str(maturity.id),
                "key": "Draft",
                'name': {
                    'en-US': 'Draft',
                    'ja': u'\u30c9\u30e9\u30d5\u30c8',
                    'de': 'Entwurf',
                    'ru': u'\u0427\u0435\u0440\u043d\u043e\u0432\u0438\u043a',
                },
                "links": {
                    "history_current": str(fh_pk),
                    "history": [str(fh_pk)],
                },
            },
            "links": {
                "maturities.history_current": {
                    "href": (
                        self.baseUrl + "/api/v1/historical_maturities/"
                        "{maturities.history_current}"),
                    "type": "historical_maturities",
                },
                "maturities.history": {
                    "href": (
                        self.baseUrl + "/api/v1/historical_maturities/"
                        "{maturities.history}"),
                    "type": "historical_maturities",
                },
            }
        }
        actual_json = loads(response.content.decode('utf-8'))
        self.assertDataEqual(expected_json, actual_json)

    def test_filter_by_key(self):
        maturity = self.create(
            Maturity, key='WD', name={'en': 'Working Draft'})
        self.create(Maturity, key="ED", name={'en': "Editor's Draft"})
        history_pk = maturity.history.all()[0].pk

        response = self.client.get(reverse('maturity-list'), {'key': 'WD'})
        self.assertEqual(200, response.status_code, response.data)
        expected_data = {
            'count': 1,
            'previous': None,
            'next': None,
            'results': [{
                'id': maturity.id,
                'key': 'WD',
                'name': {'en': 'Working Draft'},
                'history': [history_pk],
                'history_current': history_pk,
            }]}
        self.assertDataEqual(response.data, expected_data)

    def test_post_empty(self):
        self.login_superuser()
        response = self.client.post(reverse('maturity-list'), {})
        self.assertEqual(400, response.status_code)
        expected_data = {
            "key": ["This field is required."],
            "name": ["This field is required."],
        }
        self.assertDataEqual(response.data, expected_data)
