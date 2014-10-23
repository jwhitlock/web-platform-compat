#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for `web-platform-compat.viewsets.SpecificationViewSet` class.
"""
from __future__ import unicode_literals
from json import dumps, loads

from django.core.urlresolvers import reverse

from webplatformcompat.models import Maturity, Section, Specification

from .base import APITestCase


class TestSpecificationViewSet(APITestCase):
    def test_get(self):
        maturity = self.create(
            Maturity, key='REC', name={'en': 'Recommendation'})
        spec = self.create(
            Specification, maturity=maturity, slug="css1", mdn_key="CSS1",
            name={'en': "CSS Level&nbsp;1"},
            uri={'en': 'http://www.w3.org/TR/CSS1/'})
        url = reverse('specification-detail', kwargs={'pk': spec.pk})
        history_pk = spec.history.all()[0].pk
        response = self.client.get(url, HTTP_ACCEPT="application/vnd.api+json")
        self.assertEqual(200, response.status_code, response.data)

        expected_data = {
            'id': spec.id,
            'slug': 'css1',
            'mdn_key': 'CSS1',
            'name': {'en': 'CSS Level&nbsp;1'},
            'uri': {'en': 'http://www.w3.org/TR/CSS1/'},
            'maturity': maturity.pk,
            'sections': [],
            'history': [history_pk],
            'history_current': history_pk,
        }
        self.assertDataEqual(expected_data, response.data)

        expected_json = {
            "specifications": {
                "id": str(spec.id),
                'slug': 'css1',
                'mdn_key': 'CSS1',
                "name": {"en": "CSS Level&nbsp;1"},
                "uri": {"en": "http://www.w3.org/TR/CSS1/"},
                "links": {
                    "maturity": str(maturity.pk),
                    "sections": [],
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
                "specifications.sections": {
                    "href": (
                        "http://testserver/api/v1/sections/"
                        "{specifications.sections}"),
                    "type": "sections"
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

    def test_add_name(self):
        maturity = self.create(
            Maturity, key='REC', name={'en': 'Recommendation'})
        spec = self.create(
            Specification, maturity=maturity, slug="css1",
            name={'en': "Cascading Style Sheets, level 1"},
            uri={'en': 'http://www.w3.org/TR/REC-CSS1/'})
        url = reverse('specification-detail', kwargs={'pk': spec.pk})
        data = {
            "specifications": {
                'name': {
                    'en': 'Cascading Style Sheets, level 1',
                    'fr': 'Les feuilles de style en cascade, niveau 1',
                },
                'uri': {
                    'en': 'http://www.w3.org/TR/REC-CSS1/',
                    'fr': 'http://www.yoyodesign.org/doc/w3c/css1/index.html',
                }
            }
        }
        response = self.client.put(
            url, dumps(data), content_type='application/vnd.api+json')
        self.assertEqual(200, response.status_code, response.data)
        history_pk = spec.history.all()[0].pk

        expected_data = {
            'id': spec.id,
            'slug': 'css1',
            'mdn_key': None,
            'name': {
                'en': "Cascading Style Sheets, level 1",
                'fr': "Les feuilles de style en cascade, niveau 1"
            },
            'uri': {
                'en': 'http://www.w3.org/TR/REC-CSS1/',
                'fr': 'http://www.yoyodesign.org/doc/w3c/css1/index.html'
            },
            'maturity': maturity.pk,
            'sections': [],
            'history': [h.pk for h in spec.history.all()],
            'history_current': history_pk,
        }
        self.assertDataEqual(expected_data, response.data)

    def test_sections_are_ordered(self):
        maturity = self.create(
            Maturity, key='WD', name={'en': 'Working Draft'})
        spec = self.create(
            Specification, maturity=maturity, slug="css3-animations",
            mdn_key='CSS3 Animations',
            name={'en': "CSS Animations"},
            uri={'en': 'http://dev.w3.org/csswg/css-animations/'})
        section46 = self.create(
            Section, specification=spec,
            name={'en': "The 'animation-direction' property"},
            subpath={'en': "#animation-direction"})
        section45 = self.create(
            Section, specification=spec,
            name={'en': "The 'animation-iteration-count' property"},
            subpath={'en': "#animation-iteration-count"})

        url = reverse('specification-detail', kwargs={'pk': spec.pk})
        history_pk = spec.history.all()[0].pk
        response = self.client.get(url, HTTP_ACCEPT="application/vnd.api+json")
        self.assertEqual(200, response.status_code, response.data)

        expected_data = {
            'id': spec.id,
            'slug': 'css3-animations',
            'mdn_key': 'CSS3 Animations',
            'name': {'en': "CSS Animations"},
            'uri': {'en': 'http://dev.w3.org/csswg/css-animations/'},
            'maturity': maturity.pk,
            'sections': [section46.pk, section45.pk],
            'history': [history_pk],
            'history_current': history_pk,
        }
        self.assertDataEqual(expected_data, response.data)

        data = {
            "specifications": {
                "links": {
                    "sections": [str(section45.pk), str(section46.pk)]
                }
            }
        }
        response = self.client.put(
            url, dumps(data), content_type='application/vnd.api+json')
        self.assertEqual(200, response.status_code, response.data)
        history_pk = spec.history.all()[0].pk

        expected_data = {
            'id': spec.id,
            'slug': 'css3-animations',
            'mdn_key': 'CSS3 Animations',
            'name': {'en': "CSS Animations"},
            'uri': {'en': 'http://dev.w3.org/csswg/css-animations/'},
            'maturity': maturity.pk,
            'sections': [section45.pk, section46.pk],
            'history': [h.pk for h in spec.history.all()],
            'history_current': history_pk,
        }
        self.assertDataEqual(expected_data, response.data)

        response = self.client.put(
            url, dumps(data), content_type='application/vnd.api+json')
        self.assertEqual(200, response.status_code, response.data)
        history_pk = spec.history.all()[0].pk

        expected_data = {
            'id': spec.id,
            'slug': 'css3-animations',
            'mdn_key': 'CSS3 Animations',
            'name': {'en': "CSS Animations"},
            'uri': {'en': 'http://dev.w3.org/csswg/css-animations/'},
            'maturity': maturity.pk,
            'sections': [section45.pk, section46.pk],
            'history': [h.pk for h in spec.history.all()],
            'history_current': history_pk,
        }
        self.assertDataEqual(expected_data, response.data)

    def test_list(self):
        maturity = self.create(
            Maturity, key='WD', name={'en': 'Working Draft'})
        spec = self.create(
            Specification, maturity=maturity, slug='css3_animations',
            mdn_key="CSS3 Animations",
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
                'slug': 'css3_animations',
                'mdn_key': 'CSS3 Animations',
                'name': {'en': "CSS Animations"},
                'uri': {'en': 'http://dev.w3.org/csswg/css-animations/'},
                'maturity': maturity.pk,
                'sections': [],
                'history': [history_pk],
                'history_current': history_pk,
            }]}
        self.assertDataEqual(expected_data, response.data)

        expected_json = {
            "specifications": [{
                "id": str(spec.id),
                "slug": "css3_animations",
                "mdn_key": "CSS3 Animations",
                "name": {"en": "CSS Animations"},
                "uri": {"en": "http://dev.w3.org/csswg/css-animations/"},
                "links": {
                    "maturity": str(maturity.pk),
                    "sections": [],
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
                "specifications.sections": {
                    "href": (
                        "http://testserver/api/v1/sections/"
                        "{specifications.sections}"),
                    "type": "sections"
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

    def test_filter_by_slug(self):
        maturity = self.create(
            Maturity, key="CR", name={'en': 'Candidate Recommendation'})
        spec = self.create(
            Specification, maturity=maturity, slug='web-workers',
            mdn_key='Web Workers',
            name={'en': 'Web Workers'},
            uri={'en': 'http://dev.w3.org/html5/workers/'})
        self.create(
            Specification, slug='websockets', mdn_key='Websockets',
            maturity=maturity,
            name={'en': 'The WebSocket API'},
            uri={'en': 'http://dev.w3.org/html5/websockets/'})
        history_pk = spec.history.all()[0].pk

        response = self.client.get(
            reverse('specification-list'), {'slug': 'web-workers'})
        self.assertEqual(200, response.status_code, response.data)
        expected_data = {
            'count': 1,
            'previous': None,
            'next': None,
            'results': [{
                'id': spec.id,
                'slug': 'web-workers',
                'mdn_key': 'Web Workers',
                'name': {'en': 'Web Workers'},
                'uri': {'en': 'http://dev.w3.org/html5/workers/'},
                'maturity': maturity.pk,
                'sections': [],
                'history': [history_pk],
                'history_current': history_pk,
            }]}
        self.assertDataEqual(response.data, expected_data)

    def test_filter_by_mdn_key(self):
        maturity = self.create(
            Maturity, key="CR", name={'en': 'Candidate Recommendation'})
        spec = self.create(
            Specification, maturity=maturity, slug='web-workers',
            mdn_key='Web Workers',
            name={'en': 'Web Workers'},
            uri={'en': 'http://dev.w3.org/html5/workers/'})
        self.create(
            Specification, slug='websockets', mdn_key='Websockets',
            maturity=maturity,
            name={'en': 'The WebSocket API'},
            uri={'en': 'http://dev.w3.org/html5/websockets/'})
        history_pk = spec.history.all()[0].pk

        response = self.client.get(
            reverse('specification-list'), {'mdn_key': 'Web Workers'})
        self.assertEqual(200, response.status_code, response.data)
        expected_data = {
            'count': 1,
            'previous': None,
            'next': None,
            'results': [{
                'id': spec.id,
                'slug': 'web-workers',
                'mdn_key': 'Web Workers',
                'name': {'en': 'Web Workers'},
                'uri': {'en': 'http://dev.w3.org/html5/workers/'},
                'maturity': maturity.pk,
                'sections': [],
                'history': [history_pk],
                'history_current': history_pk,
            }]}
        self.assertDataEqual(response.data, expected_data)
