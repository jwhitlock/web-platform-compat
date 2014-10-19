#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for `web-platform-compat.viewsets.HistoricalSpecificationViewSet` class.
"""
from __future__ import unicode_literals
from datetime import datetime
from json import loads
from pytz import UTC

from django.core.urlresolvers import reverse

from webplatformcompat.models import Maturity, Specification

from .base import APITestCase


class TestHistoricalSpecificationViewset(APITestCase):

    def test_get(self):
        user = self.login_superuser()
        maturity = self.create(
            Maturity, key='M', name={'en': 'A Maturity'})
        spec = self.create(
            Specification, maturity=maturity, key="Spec",
            name={'en': 'A Specification'},
            uri={'en': 'http://example.com/spec.html'},
            _history_user=user,
            _history_date=datetime(2014, 10, 19, 11, 46, 10, 834522, UTC))
        history_pk = spec.history.all()[0].pk
        url = reverse(
            'historicalspecification-detail', kwargs={'pk': history_pk})
        response = self.client.get(url, HTTP_ACCEPT="application/vnd.api+json")
        self.assertEqual(200, response.status_code, response.data)

        expected_data = {
            'id': history_pk,
            'date': spec._history_date,
            'event': 'created',
            'user': user.pk,
            'specification': spec.pk,
            'specifications': {
                'id': str(spec.id),
                'key': 'Spec',
                'name': {'en': 'A Specification'},
                'uri': {'en': 'http://example.com/spec.html'},
                'links': {
                    'maturity': str(maturity.id),
                    'history_current': str(history_pk),
                }
            },
        }
        self.assertDataEqual(expected_data, response.data)
        expected_json = {
            'historical_specifications': {
                'id': str(history_pk),
                'date': '2014-10-19T11:46:10.834Z',
                'event': 'created',
                'specifications': {
                    'id': str(spec.id),
                    'key': 'Spec',
                    'name': {'en': 'A Specification'},
                    'uri': {'en': 'http://example.com/spec.html'},
                    'links': {
                        'maturity': str(maturity.id),
                        'history_current': str(history_pk),
                    },
                },
                'links': {
                    'specification': str(spec.pk),
                    'user': str(user.pk),
                },
            },
            'links': {
                'historical_specifications.specification': {
                    'href': (
                        'http://testserver/api/v1/specifications/'
                        '{historical_specifications.specification}'),
                    'type': 'specifications'
                },
                'historical_specifications.user': {
                    'href': (
                        'http://testserver/api/v1/users/'
                        '{historical_specifications.user}'),
                    'type': 'users'
                },
            }
        }
        actual_json = loads(response.content.decode('utf-8'))
        self.assertDataEqual(expected_json, actual_json)

    def test_filter_by_id(self):
        user = self.login_superuser()
        maturity = self.create(
            Maturity, key='M', name={'en': 'A Maturity'})
        self.create(
            Specification, maturity=maturity, key='Other Spec',
            name={'en': 'Other Spec'}, uri={'en': 'http://w3c.org/spec'})
        spec = self.create(
            Specification, maturity=maturity, key="Spec",
            name={'en': 'A Specification'},
            uri={'en': 'http://example.com/spec.html'},
            _history_user=user,
            _history_date=datetime(2014, 10, 19, 11, 47, 22, 595634, UTC))
        history_pk = spec.history.all()[0].pk
        url = reverse('historicalspecification-list')
        response = self.client.get(url, {'id': spec.id})
        expected_data = {
            'count': 1,
            'previous': None,
            'next': None,
            'results': [{
                'id': history_pk,
                'date': spec._history_date,
                'event': 'created',
                'user': user.pk,
                'specification': spec.pk,
                'specifications': {
                    'id': str(spec.pk),
                    'key': 'Spec',
                    'name': {'en': 'A Specification'},
                    'uri': {'en': 'http://example.com/spec.html'},
                    'links': {
                        'maturity': str(maturity.id),
                        'history_current': str(history_pk),
                    }
                },
            }]}
        self.assertDataEqual(expected_data, response.data)
