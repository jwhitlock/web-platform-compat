#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for `web-platform-compat.viewsets.BrowserViewSet` class.
"""
from __future__ import unicode_literals
from json import dumps, loads

from django.core.urlresolvers import reverse

from webplatformcompat.models import Browser, Version

from .base import APITestCase


class TestBrowserViewset(APITestCase):
    '''Test browsers list and detail, as well as common functionality'''

    def test_get_empty(self):
        browser = self.create(Browser)
        url = self.reverse('browser-detail', pk=browser.pk)
        response = self.client.get(
            url, content_type="application/vnd.api+json")
        history_pk = browser.history.get().pk
        expected_data = {
            'id': browser.pk,
            'slug': '',
            'name': None,
            'note': None,
            'history': [history_pk],
            'history_current': history_pk,
            'versions': [],
        }
        self.assertDataEqual(response.data, expected_data)
        expected_content = {
            "browsers": {
                "id": str(browser.pk),
                "slug": "",
                "name": None,
                "note": None,
                "links": {
                    "history": [str(history_pk)],
                    "history_current": str(history_pk),
                    "versions": [],
                }
            },
            "links": {
                "browsers.history": {
                    "type": "historical_browsers",
                    "href": (
                        "http://testserver/api/v1"
                        "/historical_browsers/{browsers.history}"),
                },
                "browsers.history_current": {
                    "type": "historical_browsers",
                    "href": (
                        "http://testserver/api/v1"
                        "/historical_browsers/{browsers.history_current}"),
                },
                "browsers.versions": {
                    "type": "versions",
                    "href": (
                        "http://testserver/api/v1"
                        "/versions/{browsers.versions}"),
                },
            }
        }
        actual_content = loads(response.content.decode('utf-8'))
        self.assertDataEqual(expected_content, actual_content)

    def test_get_populated(self):
        browser = self.create(
            Browser,
            slug="firefox",
            name={"en": "Firefox"},
            note={"en": "Uses Gecko for its web browser engine"})
        url = reverse('browser-detail', kwargs={'pk': browser.pk})
        response = self.client.get(url)
        history_pk = browser.history.get().pk
        expected_data = {
            'id': browser.pk,
            'slug': 'firefox',
            'name': {"en": "Firefox"},
            'note': {"en": "Uses Gecko for its web browser engine"},
            'history': [history_pk],
            'history_current': history_pk,
            'versions': [],
        }
        self.assertDataEqual(response.data, expected_data)

    def test_get_list(self):
        firefox = self.create(
            Browser,
            slug="firefox", name={"en": "Firefox"},
            note={"en": "Uses Gecko for its web browser engine"})
        chrome = self.create(Browser, slug="chrome", name={"en": "Chrome"})
        response = self.client.get(reverse('browser-list'))
        firefox_history_id = '%s' % firefox.history.get().pk
        chrome_history_id = '%s' % chrome.history.get().pk
        expected_content = {
            'browsers': [
                {
                    'id': '%s' % firefox.pk,
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

    def test_filter_by_slug(self):
        browser = self.create(
            Browser, slug="firefox", name={"en": "Firefox"}, note=None)
        self.create(Browser, slug="chrome", name={"en": "Chrome"})
        url = reverse('browser-list')
        response = self.client.get(url, {'slug': 'firefox'})
        history_pk = browser.history.get().pk
        expected_data = {
            'count': 1,
            'previous': None,
            'next': None,
            'results': [{
                'id': browser.pk,
                'slug': 'firefox',
                'name': {"en": "Firefox"},
                'note': None,
                'history': [history_pk],
                'history_current': history_pk,
                'versions': [],
            }]}
        self.assertDataEqual(response.data, expected_data)

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

    def test_post_not_authorized(self):
        response = self.client.post(reverse('browser-list'), {})
        self.assertEqual(403, response.status_code)
        expected_data = {
            'detail': 'Authentication credentials were not provided.'
        }
        self.assertDataEqual(response.data, expected_data)

    def test_post_empty(self):
        self.login_superuser()
        response = self.client.post(reverse('browser-list'), {})
        self.assertEqual(400, response.status_code)
        expected_data = {
            "slug": ["This field is required."],
            "name": ["This field is required."],
        }
        self.assertDataEqual(response.data, expected_data)

    def test_post_minimal(self):
        self.login_superuser()
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

    def test_post_empty_slug_not_allowed(self):
        self.login_superuser()
        data = {'slug': '', 'name': '{"en": "Firefox"}'}
        response = self.client.post(reverse('browser-list'), data)
        self.assertEqual(400, response.status_code, response.data)
        expected_data = {
            "slug": ["This field is required."],
        }
        self.assertDataEqual(response.data, expected_data)

    def test_post_whitespace_slug_not_allowed(self):
        self.login_superuser()
        data = {'slug': ' ', 'name': '{"en": "Firefox"}'}
        response = self.client.post(reverse('browser-list'), data)
        self.assertEqual(400, response.status_code, response.data)
        expected_data = {
            "slug": [
                "Enter a valid 'slug' consisting of letters, numbers,"
                " underscores or hyphens."],
        }
        self.assertDataEqual(response.data, expected_data)

    def test_post_minimal_json_api(self):
        self.login_superuser()
        data = dumps({
            'browsers': {
                'slug': 'firefox',
                'name': {
                    "en": "Firefox"
                },
            }
        })
        response = self.client.post(
            reverse('browser-list'), data=data,
            content_type="application/vnd.api+json")
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

    def test_post_full(self):
        self.login_superuser()
        data = {
            'slug': 'firefox',
            'name': '{"en": "Firefox"}',
            'note': '{"en": "Uses Gecko for its web browser engine"}',
        }
        response = self.client.post(reverse('browser-list'), data)
        self.assertEqual(201, response.status_code, response.data)
        browser = Browser.objects.get()
        history_pk = browser.history.get().pk
        expected_data = {
            'id': browser.pk,
            'slug': 'firefox',
            'name': {"en": "Firefox"},
            'note': {"en": "Uses Gecko for its web browser engine"},
            'history': [history_pk],
            'history_current': history_pk,
            'versions': [],
        }
        self.assertDataEqual(response.data, expected_data)

    def test_post_bad_data(self):
        self.login_superuser()
        data = {
            'slug': 'bad slug',
            'name': '"Firefox"',
            'note': '{"es": "Utiliza Gecko por su motor del navegador web"}',
        }
        response = self.client.post(reverse('browser-list'), data)
        self.assertEqual(400, response.status_code, response.data)
        expected_data = {
            'slug': [
                "Enter a valid 'slug' consisting of letters, numbers,"
                " underscores or hyphens."],
            'name': [
                "Value must be a JSON dictionary of language codes to"
                " strings."],
            'note': ["Missing required language code 'en'."],
        }
        self.assertDataEqual(response.data, expected_data)

    def test_put_as_json_api(self):
        '''If content is application/vnd.api+json, put is partial'''
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

    def test_put_as_json(self):
        '''If content is application/json, put is full put'''
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

    def test_put_history_current(self):
        browser = self.create(Browser, slug='browser', name={'en': 'Old Name'})
        old_history = browser.history.latest('history_date')
        browser.name = {'en': 'Browser'}
        browser.save()
        data = dumps({
            'browsers': {
                'links': {
                    'history_current': str(old_history.history_id)
                }
            }
        })
        url = reverse('browser-detail', kwargs={'pk': browser.pk})
        response = self.client.put(
            url, data=data, content_type="application/vnd.api+json")
        self.assertEqual(200, response.status_code, response.data)
        current_history = browser.history.all()[0]
        self.assertNotEqual(old_history.history_id, current_history.history_id)
        histories = browser.history.all()
        self.assertEqual(3, len(histories))
        expected_data = {
            "id": browser.pk,
            "slug": "browser",
            "name": {"en": "Old Name"},
            "note": None,
            'history': [h.pk for h in histories],
            'history_current': current_history.pk,
            'versions': [],
        }
        self.assertDataEqual(response.data, expected_data)

    def test_put_history_current_wrong_browser_fails(self):
        browser = self.create(
            Browser, slug='browser', name={'en': 'Old Name'})
        other_browser = self.create(
            Browser, slug='other-browser', name={'en': 'Other Browser'})
        bad_history = other_browser.history.all()[0]
        data = dumps({
            'browsers': {
                'slug': 'browser',
                'links': {
                    'history_current': str(bad_history.history_id)
                }
            }
        })
        url = reverse('browser-detail', kwargs={'pk': browser.pk})
        response = self.client.put(
            url, data=data, content_type="application/vnd.api+json")
        self.assertEqual(400, response.status_code, response.data)
        expected_data = {
            'history_current': ['history is for a different object']
        }
        self.assertDataEqual(response.data, expected_data)

    def test_put_history_same(self):
        browser = self.create(Browser, slug='browser', name={'en': 'Old Name'})
        browser.name = {'en': 'Browser'}
        browser.save()
        current_history = browser.history.latest('history_date')
        data = dumps({
            'browsers': {
                'links': {
                    'history_current': str(current_history.history_id)
                }
            }
        })
        url = reverse('browser-detail', kwargs={'pk': browser.pk})
        response = self.client.put(
            url, data=data, content_type="application/vnd.api+json")
        self.assertEqual(200, response.status_code, response.data)
        new_history = browser.history.all()[0]
        self.assertNotEqual(new_history.history_id, current_history.history_id)
        histories = browser.history.all()
        self.assertEqual(3, len(histories))
        expected_data = {
            "id": browser.pk,
            "slug": "browser",
            "name": {"en": "Browser"},
            "note": None,
            'history': [h.pk for h in histories],
            'history_current': new_history.pk,
            'versions': [],
        }
        self.assertDataEqual(response.data, expected_data)

    def test_versions_are_ordered(self):
        browser = self.create(Browser, slug='browser', name={'en': 'Browser'})
        v2 = self.create(Version, browser=browser, version='2.0')
        v1 = self.create(Version, browser=browser, version='1.0')
        url = reverse('browser-detail', kwargs={'pk': browser.pk})
        response = self.client.get(url, HTTP_ACCEPT='application/vnd.api+json')
        self.assertEqual(200, response.status_code, response.data)
        history = browser.history.all()
        expected_data = {
            "id": browser.pk,
            "slug": 'browser',
            "name": {"en": "Browser"},
            "note": None,
            "history": [h.pk for h in history],
            "history_current": history[0].pk,
            "versions": [v.pk for v in (v2, v1)],
        }
        self.assertDataEqual(response.data, expected_data)

    def test_versions_are_reordered(self):
        browser = self.create(Browser, slug='browser', name={'en': 'Browser'})
        v1 = self.create(Version, browser=browser, version='1.0')
        v2 = self.create(Version, browser=browser, version='2.0')
        url = reverse('browser-detail', kwargs={'pk': browser.pk})
        data = dumps({
            'browsers': {
                'links': {
                    'versions': [str(v1.pk), str(v2.pk)]
                }
            }
        })
        response = self.client.put(
            url, data=data, content_type='application/vnd.api+json',
            HTTP_ACCEPT='application/vnd.api+json')
        self.assertEqual(200, response.status_code, response.data)
        history = browser.history.all()
        expected_data = {
            "id": browser.pk,
            "slug": 'browser',
            "name": {"en": "Browser"},
            "note": None,
            "history": [h.pk for h in history],
            "history_current": history[0].pk,
            "versions": [v.pk for v in (v1, v2)],
        }
        self.assertDataEqual(response.data, expected_data)

    def test_versions_same_order(self):
        browser = self.create(Browser, slug='browser', name={'en': 'Browser'})
        v1 = self.create(Version, browser=browser, version='1.0')
        v2 = self.create(Version, browser=browser, version='2.0')
        url = reverse('browser-detail', kwargs={'pk': browser.pk})
        data = dumps({
            'browsers': {
                'links': {
                    'versions': [str(v2.pk), str(v1.pk)]
                }
            }
        })
        response = self.client.put(
            url, data=data, content_type='application/vnd.api+json',
            HTTP_ACCEPT='application/vnd.api+json')
        self.assertEqual(200, response.status_code, response.data)
        history = browser.history.all()
        expected_data = {
            "id": browser.pk,
            "slug": 'browser',
            "name": {"en": "Browser"},
            "note": None,
            "history": [h.pk for h in history],
            "history_current": history[0].pk,
            "versions": [v.pk for v in (v2, v1)],
        }
        self.assertDataEqual(response.data, expected_data)

    def test_slug_is_write_only(self):
        browser = self.create(Browser, slug='browser', name={'en': 'Browser'})
        url = reverse('browser-detail', kwargs={'pk': browser.pk})
        data = dumps({
            'browsers': {
                'slug': 'new-slug'
            }
        })
        response = self.client.put(
            url, data=data, content_type='application/vnd.api+json',
            HTTP_ACCEPT='application/vnd.api+json')
        self.assertEqual(200, response.status_code, response.data)
        history = browser.history.all()
        expected_data = {
            "id": browser.pk,
            "slug": 'browser',
            "name": {"en": "Browser"},
            "note": None,
            "history": [h.pk for h in history],
            "history_current": history[0].pk,
            "versions": [],
        }
        self.assertDataEqual(response.data, expected_data)

    def test_delete(self):
        browser = self.create(Browser, slug='firesux', name={'en': 'Firesux'})
        url = reverse('browser-detail', kwargs={'pk': browser.pk})
        response = self.client.delete(url)
        self.assertEqual(204, response.status_code, response.content)
        self.assertFalse(Browser.objects.filter(pk=browser.pk).exists())
