#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for `web-platform-compat.viewsets."""
from __future__ import unicode_literals
from datetime import datetime
from json import dumps, loads
from pytz import UTC

from django.core.urlresolvers import reverse
import mock

from webplatformcompat.history import Changeset
from webplatformcompat.models import Browser, Feature

from .base import APITestCase


class TestGenericViewset(APITestCase):
    """Test common viewset functionality through the browsers viewset."""

    def test_get_browser_detail(self):
        browser = self.create(
            Browser,
            slug="firefox",
            name={"en": "Firefox"},
            note={"en": "Uses Gecko for its web browser engine"})
        url = reverse('browser-detail', kwargs={'pk': browser.pk})
        response = self.client.get(url)
        history_pk = browser.history.get().pk
        expected_content = {
            'browsers': {
                'id': str(browser.pk),
                'slug': 'firefox',
                'name': {"en": "Firefox"},
                'note': {"en": "Uses Gecko for its web browser engine"},
                'links': {
                    'history': [str(history_pk)],
                    'history_current': str(history_pk),
                    'versions': [],
                }
            },
            'links': {
                'browsers.history': {
                    'href': (
                        'http://testserver/api/v1/historical_browsers/'
                        '{browsers.history}'),
                    'type': 'historical_browsers'
                },
                'browsers.history_current': {
                    'href': (
                        'http://testserver/api/v1/historical_browsers/'
                        '{browsers.history_current}'),
                    'type': 'historical_browsers'
                },
                'browsers.versions': {
                    'href': (
                        'http://testserver/api/v1/versions/'
                        '{browsers.versions}'),
                    'type': u'versions'
                }
            }
        }
        actual_content = loads(response.content.decode('utf-8'))
        self.assertDataEqual(expected_content, actual_content)

    def test_get_browser_list(self):
        firefox = self.create(
            Browser,
            slug="firefox", name={"en": "Firefox"},
            note={"en": "Uses Gecko for its web browser engine"})
        chrome = self.create(Browser, slug="chrome", name={"en": "Chrome"})
        response = self.client.get(reverse('browser-list'))
        firefox_history_id = str(firefox.history.get().pk)
        chrome_history_id = str(chrome.history.get().pk)
        expected_content = {
            'browsers': [
                {
                    'id': str(firefox.pk),
                    'slug': 'firefox',
                    'name': {"en": "Firefox"},
                    'note': {"en": "Uses Gecko for its web browser engine"},
                    'links': {
                        'history': [firefox_history_id],
                        'history_current': firefox_history_id,
                        'versions': [],
                    },
                }, {
                    'id': '%s' % chrome.pk,
                    'slug': 'chrome',
                    'name': {"en": "Chrome"},
                    'note': None,
                    'links': {
                        'history': [chrome_history_id],
                        'history_current': chrome_history_id,
                        'versions': [],
                    },
                },
            ],
            'links': {
                'browsers.history': {
                    'href': (
                        'http://testserver/api/v1/historical_browsers/'
                        '{browsers.history}'),
                    'type': 'historical_browsers',
                },
                'browsers.history_current': {
                    'href': (
                        'http://testserver/api/v1/historical_browsers/'
                        '{browsers.history_current}'),
                    'type': 'historical_browsers',
                },
                'browsers.versions': {
                    'href': (
                        'http://testserver/api/v1/versions/'
                        '{browsers.versions}'),
                    'type': 'versions',
                },
            },
            'meta': {
                'pagination': {
                    'browsers': {
                        'count': 2,
                        'previous': None,
                        'next': None
                    },
                },
            },
        }
        actual_content = loads(response.content.decode('utf-8'))
        self.assertDataEqual(expected_content, actual_content)

    def test_get_browsable_api(self):
        browser = self.create(Browser)
        url = self.reverse('browser-list')
        response = self.client.get(url, HTTP_ACCEPT="text/html")
        history_pk = browser.history.get().pk
        expected_data = {
            'count': 1,
            'previous': None,
            'next': None,
            'results': [{
                'id': browser.pk,
                'slug': '',
                'name': None,
                'note': None,
                'history': [history_pk],
                'history_current': history_pk,
                'versions': [],
            }]}
        self.assertDataEqual(response.data, expected_data)
        self.assertTrue(response['content-type'].startswith('text/html'))

    def test_post_minimal(self):
        self.login_user()
        data = {'slug': 'firefox', 'name': '{"en": "Firefox"}'}
        response = self.client.post(reverse('browser-list'), data)
        self.assertEqual(201, response.status_code, response.data)
        browser = Browser.objects.get()
        history_pk = browser.history.get().pk
        expected_data = {
            "id": browser.pk,
            "slug": "firefox",
            "name": {"en": "Firefox"},
            "note": None,
            'history': [history_pk],
            'history_current': history_pk,
            'versions': [],
        }
        self.assertDataEqual(response.data, expected_data)

    @mock.patch('webplatformcompat.tasks.update_cache_for_instance')
    def test_put_as_json_api(self, mock_update):
        """If content is application/vnd.api+json, put is partial"""
        browser = self.create(
            Browser, slug='browser', name={'en': 'Old Name'})
        data = dumps({
            'browsers': {
                'name': {
                    'en': 'New Name'
                }
            }
        })
        url = reverse('browser-detail', kwargs={'pk': browser.pk})
        mock_update.reset_mock()
        response = self.client.put(
            url, data=data, content_type="application/vnd.api+json")
        self.assertEqual(200, response.status_code, response.data)
        histories = browser.history.all()
        expected_data = {
            "id": browser.pk,
            "slug": "browser",
            "name": {"en": "New Name"},
            "note": None,
            "history": [h.pk for h in histories],
            "history_current": histories[0].pk,
            "versions": [],
        }
        self.assertDataEqual(response.data, expected_data)
        mock_update.assert_called_once_with(
            'Browser', browser.pk, browser, False)

    @mock.patch('webplatformcompat.tasks.update_cache_for_instance')
    def test_put_in_changeset(self, mock_update):
        browser = self.create(
            Browser, slug='browser', name={'en': 'Old Name'})
        changeset = Changeset.objects.create(user=self.user)
        data = dumps({
            'browsers': {
                'name': {
                    'en': 'New Name'
                }
            }
        })
        url = reverse('browser-detail', kwargs={'pk': browser.pk})
        url += '?changeset=%s' % changeset.pk
        mock_update.reset_mock()
        response = self.client.put(
            url, data=data, content_type="application/vnd.api+json")
        self.assertEqual(200, response.status_code, response.data)
        mock_update.assert_not_called()

    def test_put_as_json(self):
        """If content is application/json, put is full put"""
        browser = self.create(
            Browser, slug='browser', name={'en': 'Old Name'})
        data = {'name': '{"en": "New Name"}'}
        url = reverse('browser-detail', kwargs={'pk': browser.pk})
        response = self.client.put(url, data=data)
        self.assertEqual(200, response.status_code, response.data)
        histories = browser.history.all()
        expected_data = {
            "id": browser.pk,
            "slug": "browser",
            "name": {"en": "New Name"},
            "note": None,
            "history": [h.pk for h in histories],
            "history_current": histories[0].pk,
            "versions": [],
        }
        self.assertDataEqual(response.data, expected_data)

    @mock.patch('webplatformcompat.tasks.update_cache_for_instance')
    def test_delete(self, mock_update):
        self.login_user(groups=["change-resource", "delete-resource"])
        browser = self.create(Browser, slug='firesux', name={'en': 'Firesux'})
        url = reverse('browser-detail', kwargs={'pk': browser.pk})
        mock_update.reset_mock()
        response = self.client.delete(url)
        self.assertEqual(204, response.status_code, response.content)
        self.assertFalse(Browser.objects.filter(pk=browser.pk).exists())
        mock_update.assert_called_once_with(
            'Browser', browser.pk, mock.ANY, False)

    def test_delete_not_allowed(self):
        self.login_user()
        browser = self.create(
            Browser, slug='browser', name={'en': 'Old Name'})
        url = reverse('browser-detail', kwargs={'pk': browser.pk})
        response = self.client.delete(url)
        self.assertEqual(403, response.status_code)
        expected_data = {
            'detail': "You do not have permission to perform this action."
        }
        self.assertDataEqual(response.data, expected_data)

    @mock.patch('webplatformcompat.tasks.update_cache_for_instance')
    def test_delete_in_changeset(self, mock_update):
        self.login_user(groups=["change-resource", "delete-resource"])
        browser = self.create(
            Browser, slug="internet_exploder",
            name={'en': 'Internet Exploder'})
        url = reverse('browser-detail', kwargs={'pk': browser.pk})
        url += "?changeset=%d" % self.changeset.id
        mock_update.reset_mock()
        response = self.client.delete(url)
        self.assertEqual(204, response.status_code, response.content)
        self.assertFalse(Browser.objects.filter(pk=browser.pk).exists())
        mock_update.assert_not_called()


class TestFeatureViewSet(APITestCase):
    """Test FeatureViewSet."""
    def test_filter_by_slug(self):
        parent = self.create(Feature, slug='parent', name={'en': 'Parent'})
        feature = self.create(
            Feature, slug='feature', parent=parent, name={'en': 'A Feature'})
        self.create(Feature, slug="other", name={'en': 'Other'})
        response = self.client.get(
            reverse('feature-list'), {'slug': 'feature'})
        self.assertEqual(200, response.status_code, response.data)
        self.assertEqual(1, response.data['count'])
        self.assertEqual(feature.id, response.data['results'][0]['id'])

    def test_filter_by_parent(self):
        parent = self.create(Feature, slug='parent', name={'en': 'Parent'})
        feature = self.create(
            Feature, slug='feature', parent=parent, name={'en': 'A Feature'})
        self.create(Feature, slug="other", name={'en': 'Other'})
        response = self.client.get(
            reverse('feature-list'), {'parent': str(parent.id)})
        self.assertEqual(200, response.status_code, response.data)
        self.assertEqual(1, response.data['count'])
        self.assertEqual(feature.id, response.data['results'][0]['id'])

    def test_filter_by_no_parent(self):
        parent = self.create(Feature, slug='parent', name={'en': 'Parent'})
        self.create(
            Feature, slug='feature', parent=parent, name={'en': 'The Feature'})
        other = self.create(Feature, slug="other", name={'en': 'Other'})
        response = self.client.get(reverse('feature-list'), {'parent': ''})
        self.assertEqual(200, response.status_code, response.data)
        self.assertEqual(2, response.data['count'])
        self.assertEqual(parent.id, response.data['results'][0]['id'])
        self.assertEqual(other.id, response.data['results'][1]['id'])


class TestHistoricaViewset(APITestCase):
    """Test common historical viewset functionality through browsers."""
    def test_get_historical_browser_detail(self):
        browser = self.create(
            Browser, slug='browser', name={'en': 'A Browser'},
            _history_date=datetime(2014, 8, 25, 20, 50, 38, 868903, UTC))
        history = browser.history.all()[0]
        url = reverse('historicalbrowser-detail', kwargs={'pk': history.pk})
        response = self.client.get(
            url, HTTP_ACCEPT="application/vnd.api+json")
        self.assertEqual(200, response.status_code, response.data)

        expected_json = {
            'historical_browsers': {
                'id': str(history.pk),
                'date': self.dt_json(browser._history_date),
                'event': 'created',
                'browsers': {
                    'id': str(browser.pk),
                    'slug': 'browser',
                    'name': {
                        'en': 'A Browser'
                    },
                    'note': None,
                    'links': {
                        'history_current': str(history.pk),
                    },
                },
                'links': {
                    'browser': str(browser.pk),
                    'changeset': str(history.history_changeset_id),
                }
            },
            'links': {
                'historical_browsers.browser': {
                    'href': (
                        'http://testserver/api/v1/browsers/'
                        '{historical_browsers.browser}'),
                    'type': 'browsers'
                },
                'historical_browsers.changeset': {
                    'href': (
                        'http://testserver/api/v1/changesets/'
                        '{historical_browsers.changeset}'),
                    'type': 'changesets'
                }
            }
        }
        actual_json = loads(response.content.decode('utf-8'))
        self.assertDataEqual(expected_json, actual_json)
