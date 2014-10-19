#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for `web-platform-compat.viewsets.SpecificationViewSet` class.
"""
from __future__ import unicode_literals
from json import loads

from django.core.urlresolvers import reverse

from webplatformcompat.models import Maturity, Specification

from .base import APITestCase


class TestSpecificationViewSet(APITestCase):
    def test_get(self):
        maturity = self.create(
            Maturity, key='REC', name={'en': 'Recommendation'})
        spec = self.create(
            Specification, maturity=maturity, key="CSS1",
            name={'en': "CSS Level&nbsp;1"},
            uri={'en': 'http://www.w3.org/TR/CSS1/'})
        url = reverse('specification-detail', kwargs={'pk': spec.pk})
        history_pk = spec.history.all()[0].pk
        response = self.client.get(url, HTTP_ACCEPT="application/vnd.api+json")
        self.assertEqual(200, response.status_code, response.data)

        expected_data = {
            'id': spec.id,
            'key': 'CSS1',
            'name': {'en': 'CSS Level&nbsp;1'},
            'uri': {'en': 'http://www.w3.org/TR/CSS1/'},
            'maturity': maturity.pk,
            'history': [history_pk],
            'history_current': history_pk,
        }
        self.assertDataEqual(expected_data, response.data)

        expected_json = {
            "specifications": {
                "id": str(spec.id),
                "key": 'CSS1',
                "name": {"en": "CSS Level&nbsp;1"},
                "uri": {"en": "http://www.w3.org/TR/CSS1/"},
                "links": {
                    "maturity": str(maturity.pk),
                    "history_current": str(history_pk),
                    "history": [str(history_pk)],
                },
            },
            "links": {
                "specifications.maturity": {
                    "href": (
                        "http://testserver/api/v1/maturities/"
                        "{specifications.maturity}"),
                    "type": "maturities"
                },
                "specifications.history_current": {
                    "href": (
                        "http://testserver/api/v1/historical_specifications/"
                        "{specifications.history_current}"),
                    "type": "historical_specifications"
                },
                "specifications.history": {
                    "href": (
                        "http://testserver/api/v1/historical_specifications/"
                        "{specifications.history}"),
                    "type": "historical_specifications"
                },
            }
        }
        actual_json = loads(response.content.decode('utf-8'))
        self.assertDataEqual(expected_json, actual_json)

    def test_list(self):
        maturity = self.create(
            Maturity, key='WD', name={'en': 'Working Draft'})
        spec = self.create(
            Specification, maturity=maturity, key="CSS3 Animations",
            name={'en': "CSS Animations"},
            uri={'en': 'http://dev.w3.org/csswg/css-animations/'})
        url = reverse('specification-list')
        history_pk = spec.history.all()[0].pk
        response = self.client.get(url, HTTP_ACCEPT="application/vnd.api+json")
        self.assertEqual(200, response.status_code, response.data)

        expected_data = {
            'count': 1,
            'previous': None,
            'next': None,
            'results': [{
                'id': spec.id,
                'key': 'CSS3 Animations',
                'name': {'en': "CSS Animations"},
                'uri': {'en': 'http://dev.w3.org/csswg/css-animations/'},
                'maturity': maturity.pk,
                'history': [history_pk],
                'history_current': history_pk,
            }]}
        self.assertDataEqual(expected_data, response.data)

        expected_json = {
            "specifications": [{
                "id": str(spec.id),
                "key": "CSS3 Animations",
                "name": {"en": "CSS Animations"},
                "uri": {"en": "http://dev.w3.org/csswg/css-animations/"},
                "links": {
                    "maturity": str(maturity.pk),
                    "history_current": str(history_pk),
                    "history": [str(history_pk)],
                },
            }],
            "links": {
                "specifications.maturity": {
                    "href": (
                        "http://testserver/api/v1/maturities/"
                        "{specifications.maturity}"),
                    "type": "maturities"
                },
                "specifications.history_current": {
                    "href": (
                        "http://testserver/api/v1/historical_specifications/"
                        "{specifications.history_current}"),
                    "type": "historical_specifications"
                },
                "specifications.history": {
                    "href": (
                        "http://testserver/api/v1/historical_specifications/"
                        "{specifications.history}"),
                    "type": "historical_specifications"
                },
            },
            "meta": {
                "pagination": {
                    "specifications": {
                        "previous": None,
                        "next": None,
                        "count": 1,
                    },
                },
            },
        }
        actual_json = loads(response.content.decode('utf-8'))
        self.assertDataEqual(expected_json, actual_json)

    def test_filter_by_key(self):
        maturity = self.create(
            Maturity, key="CR", name={'en': 'Candidate Recommendation'})
        spec = self.create(
            Specification, maturity=maturity, key='Web Workers',
            name={'en': 'Web Workers'},
            uri={'en': 'http://dev.w3.org/html5/workers/'})
        self.create(
            Specification, key='Websockets', maturity=maturity,
            name={'en': 'The WebSocket API'},
            uri={'en': 'http://dev.w3.org/html5/websockets/'})
        history_pk = spec.history.all()[0].pk

        response = self.client.get(
            reverse('specification-list'), {'key': 'Web Workers'})
        self.assertEqual(200, response.status_code, response.data)
        expected_data = {
            'count': 1,
            'previous': None,
            'next': None,
            'results': [{
                'id': spec.id,
                'key': 'Web Workers',
                'name': {'en': 'Web Workers'},
                'uri': {'en': 'http://dev.w3.org/html5/workers/'},
                'maturity': maturity.pk,
                'history': [history_pk],
                'history_current': history_pk,
            }]}
        self.assertDataEqual(response.data, expected_data)
