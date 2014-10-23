#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for `web-platform-compat.viewsets.HistoricalFeatureViewSet` class.
"""
from __future__ import unicode_literals
from datetime import datetime
from json import loads
from pytz import UTC

from django.core.urlresolvers import reverse

from webplatformcompat.models import Feature, Maturity, Section, Specification

from .base import APITestCase


class TestHistoricalFeatureViewset(APITestCase):

    def test_get(self):
        user = self.login_superuser()
        feature = self.create(
            Feature, slug="the_feature", name={"en": "The Feature"},
            _history_user=user,
            _history_date=datetime(2014, 10, 1, 14, 25, 14, 955097, UTC))
        history = feature.history.all()[0]
        url = reverse('historicalfeature-detail', kwargs={'pk': history.pk})
        response = self.client.get(url, HTTP_ACCEPT="application/vnd.api+json")
        self.assertEqual(200, response.status_code, response.data)

        expected_data = {
            'id': history.history_id,
            'date': feature._history_date,
            'event': 'created',
            'user': user.pk,
            'feature': feature.pk,
            'features': {
                'id': str(feature.id),
                'slug': 'the_feature',
                'mdn_path': None,
                'experimental': False,
                'standardized': True,
                'stable': True,
                'obsolete': False,
                'name': {'en': 'The Feature'},
                'links': {
                    'parent': None,
                    'sections': [],
                    'history_current': str(history.id),
                }
            },
        }
        self.assertDataEqual(expected_data, response.data)
        expected_json = {
            'historical_features': {
                'id': str(history.history_id),
                'date': '2014-10-01T14:25:14.955Z',
                'event': 'created',
                'features': {
                    'id': str(feature.id),
                    'slug': 'the_feature',
                    'mdn_path': None,
                    'experimental': False,
                    'standardized': True,
                    'stable': True,
                    'obsolete': False,
                    'name': {'en': 'The Feature'},
                    'links': {
                        'parent': None,
                        'sections': [],
                        'history_current': str(history.id),
                    }
                },
                'links': {
                    'feature': str(feature.pk),
                    'user': str(user.pk),
                },
            },
            'links': {
                'historical_features.feature': {
                    'href': (
                        'http://testserver/api/v1/features/'
                        '{historical_features.feature}'),
                    'type': 'features'
                },
                'historical_features.user': {
                    'href': (
                        'http://testserver/api/v1/users/'
                        '{historical_features.user}'),
                    'type': 'users'
                },
            }
        }
        actual_json = loads(response.content.decode('utf-8'))
        self.assertDataEqual(expected_json, actual_json)

    def test_get_with_sections(self):
        user = self.login_superuser()
        feature = self.create(
            Feature, slug="the_feature", name={"en": "The Feature"},
            _history_user=user,
            _history_date=datetime(2014, 10, 1, 14, 25, 14, 955097, UTC))
        maturity = self.create(Maturity, slug='Bar')
        specification = self.create(Specification, maturity=maturity)
        section = self.create(Section, specification=specification)
        feature.sections.add(section)
        feature.save()
        self.assertEqual(2, len(feature.history.all()))
        history = feature.history.all()[0]
        url = reverse('historicalfeature-detail', kwargs={'pk': history.pk})
        response = self.client.get(url, HTTP_ACCEPT="application/vnd.api+json")
        self.assertEqual(200, response.status_code, response.data)

        expected_data = {
            'id': history.history_id,
            'date': feature._history_date,
            'event': 'changed',
            'user': user.pk,
            'feature': feature.pk,
            'features': {
                'id': str(feature.id),
                'slug': 'the_feature',
                'mdn_path': None,
                'experimental': False,
                'standardized': True,
                'stable': True,
                'obsolete': False,
                'name': {'en': 'The Feature'},
                'links': {
                    'parent': None,
                    'sections': [str(section.pk)],
                    'history_current': str(history.history_id),
                }
            },
        }
        self.assertDataEqual(expected_data, response.data)

    def test_filter_by_id(self):
        user = self.login_superuser()
        parent = self.create(Feature, slug="parent-feature")
        feature = self.create(
            Feature, slug="a-feature", parent=parent,
            _history_user=user,
            _history_date=datetime(2014, 10, 1, 14, 29, 33, 22803, UTC))
        history = feature.history.all()[0]
        url = reverse('historicalfeature-list')
        response = self.client.get(url, {'id': feature.id})
        expected_data = {
            'count': 1,
            'previous': None,
            'next': None,
            'results': [{
                'id': history.history_id,
                'date': feature._history_date,
                'event': 'created',
                'user': user.pk,
                'feature': feature.pk,
                'features': {
                    'id': str(feature.pk),
                    'slug': 'a-feature',
                    'mdn_path': None,
                    'experimental': False,
                    'standardized': True,
                    'stable': True,
                    'obsolete': False,
                    'name': None,
                    'links': {
                        'parent': str(parent.id),
                        'sections': [],
                        'history_current': str(history.id),
                    }
                },
            }]}
        self.assertDataEqual(expected_data, response.data)
