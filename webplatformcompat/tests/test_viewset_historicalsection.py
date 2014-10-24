#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for `web-platform-compat.viewsets.HistoricalSectionViewSet` class.
"""
from __future__ import unicode_literals
from datetime import datetime
from json import loads
from pytz import UTC

from django.core.urlresolvers import reverse

from webplatformcompat.models import Maturity, Section, Specification

from .base import APITestCase


class TestHistoricalSectionViewset(APITestCase):

    def test_get(self):
        user = self.login_superuser()
        maturity = self.create(
            Maturity, slug='M', name={'en': 'A Maturity'})
        spec = self.create(
            Specification, maturity=maturity, slug="spec",
            name={'en': 'A Specification'},
            uri={'en': 'http://example.com/spec.html'})
        section = self.create(
            Section, specification=spec,
            name={'en': 'The Section'},
            _history_user=user,
            _history_date=datetime(2014, 10, 19, 13, 6, 22, 602237, UTC))
        history_pk = section.history.all()[0].pk
        url = reverse(
            'historicalsection-detail', kwargs={'pk': history_pk})
        response = self.client.get(url, HTTP_ACCEPT="application/vnd.api+json")
        self.assertEqual(200, response.status_code, response.data)

        expected_data = {
            'id': history_pk,
            'date': section._history_date,
            'event': 'created',
            'user': user.pk,
            'section': section.pk,
            'sections': {
                'id': str(section.id),
                'number': None,
                'name': {'en': 'The Section'},
                'subpath': None,
                'note': None,
                'links': {
                    'specification': str(spec.id),
                    'history_current': str(history_pk),
                }
            },
        }
        self.assertDataEqual(expected_data, response.data)
        expected_json = {
            'historical_sections': {
                'id': str(history_pk),
                'date': '2014-10-19T13:06:22.602Z',
                'event': 'created',
                'sections': {
                    'id': str(spec.id),
                    'number': None,
                    'name': {'en': 'The Section'},
                    'subpath': None,
                    'note': None,
                    'links': {
                        'specification': str(spec.id),
                        'history_current': str(history_pk),
                    },
                },
                'links': {
                    'section': str(spec.pk),
                    'user': str(user.pk),
                },
            },
            'links': {
                'historical_sections.section': {
                    'href': (
                        'http://testserver/api/v1/sections/'
                        '{historical_sections.section}'),
                    'type': 'sections'
                },
                'historical_sections.user': {
                    'href': (
                        'http://testserver/api/v1/users/'
                        '{historical_sections.user}'),
                    'type': 'users'
                },
            }
        }
        actual_json = loads(response.content.decode('utf-8'))
        self.assertDataEqual(expected_json, actual_json)

    def test_filter_by_id(self):
        user = self.login_superuser()
        maturity = self.create(
            Maturity, slug='M', name={'en': 'A Maturity'})
        self.create(
            Specification, maturity=maturity, slug='other_spec',
            name={'en': 'Other Spec'}, uri={'en': 'http://w3c.org/spec'})
        spec = self.create(
            Specification, maturity=maturity, slug="spec",
            name={'en': 'A Specification'},
            uri={'en': 'http://example.com/spec.html'})
        section = self.create(
            Section, specification=spec, name={'en': 'A Section'},
            _history_user=user,
            _history_date=datetime(2014, 10, 19, 13, 3, 39, 223434, UTC))

        history_pk = section.history.all()[0].pk
        url = reverse('historicalsection-list')
        response = self.client.get(url, {'id': section.id})
        expected_data = {
            'count': 1,
            'previous': None,
            'next': None,
            'results': [{
                'id': history_pk,
                'date': section._history_date,
                'event': 'created',
                'user': user.pk,
                'section': section.pk,
                'sections': {
                    'id': str(section.pk),
                    'number': None,
                    'name': {'en': 'A Section'},
                    'subpath': None,
                    'note': None,
                    'links': {
                        'specification': str(spec.id),
                        'history_current': str(history_pk),
                    }
                },
            }]}
        self.assertDataEqual(expected_data, response.data)
