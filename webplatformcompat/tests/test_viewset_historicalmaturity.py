#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for `web-platform-compat.viewsets.HistoricalMaturityViewSet` class.
"""
from __future__ import unicode_literals
from datetime import datetime
from json import loads
from pytz import UTC

from django.core.urlresolvers import reverse

from webplatformcompat.models import Maturity

from .base import APITestCase


class TestHistoricalMaturityViewset(APITestCase):

    def test_get(self):
        user = self.login_superuser()
        maturity = self.create(
            Maturity, key="CR", name={"en": "Candidate Recommendation"},
            _history_user=user,
            _history_date=datetime(2014, 10, 19, 10, 20, 45, 609995, UTC))
        history = maturity.history.all()[0]
        url = reverse('historicalmaturity-detail', kwargs={'pk': history.pk})
        response = self.client.get(url, HTTP_ACCEPT="application/vnd.api+json")
        self.assertEqual(200, response.status_code, response.data)

        expected_data = {
            'id': history.history_id,
            'date': maturity._history_date,
            'event': 'created',
            'user': user.pk,
            'maturity': maturity.pk,
            'maturities': {
                'id': str(maturity.id),
                'key': 'CR',
                'name': {'en': 'Candidate Recommendation'},
                'links': {
                    'history_current': str(history.id),
                }
            },
        }
        self.assertDataEqual(expected_data, response.data)
        expected_json = {
            'historical_maturities': {
                'id': str(history.history_id),
                'date': '2014-10-19T10:20:45.609Z',
                'event': 'created',
                'maturities': {
                    'id': str(maturity.id),
                    'key': 'CR',
                    'name': {'en': 'Candidate Recommendation'},
                    'links': {
                        'history_current': str(history.id),
                    }
                },
                'links': {
                    'maturity': str(maturity.pk),
                    'user': str(user.pk),
                },
            },
            'links': {
                'historical_maturities.maturity': {
                    'href': (
                        'http://testserver/api/v1/maturities/'
                        '{historical_maturities.maturity}'),
                    'type': 'maturities'
                },
                'historical_maturities.user': {
                    'href': (
                        'http://testserver/api/v1/users/'
                        '{historical_maturities.user}'),
                    'type': 'users'
                },
            }
        }
        actual_json = loads(response.content.decode('utf-8'))
        self.assertDataEqual(expected_json, actual_json)

    def test_filter_by_id(self):
        user = self.login_superuser()
        maturity = self.create(
            Maturity, key="PR", name={'en-US': 'Proposed Recommendation'},
            _history_user=user,
            _history_date=datetime(2014, 10, 19, 10, 23, 38, 279164, UTC))
        history = maturity.history.all()[0]
        url = reverse('historicalmaturity-list')
        response = self.client.get(url, {'id': maturity.id})
        expected_data = {
            'count': 1,
            'previous': None,
            'next': None,
            'results': [{
                'id': history.history_id,
                'date': maturity._history_date,
                'event': 'created',
                'user': user.pk,
                'maturity': maturity.pk,
                'maturities': {
                    'id': str(maturity.pk),
                    'key': 'PR',
                    'name': {'en-US': 'Proposed Recommendation'},
                    'links': {
                        'history_current': str(history.id),
                    }
                },
            }]}
        self.assertDataEqual(expected_data, response.data)
