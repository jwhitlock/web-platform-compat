# -*- coding: utf-8 -*-
"""Tests for bcauth."""

from __future__ import unicode_literals

import mock

from webplatformcompat.tests.base import TestCase
from .helpers import providers_media_js, provider_login_url


class TestProvidersMediaJS(TestCase):
    def setUp(self):
        self.patcher = mock.patch(
            'bcauth.helpers.providers.registry.get_list')
        self.mocked_get_list = self.patcher.start()
        self.context = {'request': 'fake request'}

    def tearDown(self):
        self.mocked_get_list.stop()

    def test_empty(self):
        self.mocked_get_list.return_value = []
        actual = providers_media_js(self.context)
        self.assertEqual('', actual)

    def test_provider(self):
        mock_provider = mock.Mock(spec_set=['media_js'])
        fake_js = '<script>some.JS();</script>'
        mock_provider.media_js.return_value = fake_js
        self.mocked_get_list.return_value = [mock_provider]
        actual = providers_media_js(self.context)
        self.assertEqual(fake_js, actual)
        mock_provider.media_js.assertCalledOnce(self.context['request'])


class TestProviderLoginUrl(TestCase):
    def setUp(self):
        self.patcher = mock.patch(
            'bcauth.helpers.providers.registry.by_id')
        self.mocked_by_id = self.patcher.start()
        self.context = {'request': 'fake request'}
        self.provider = mock.Mock(spec_set=['get_login_url'])
        self.fake_url = 'http://example.com/AUTH'
        self.provider.get_login_url.return_value = self.fake_url
        self.mocked_by_id.return_value = self.provider

        self.request = mock.Mock(spec_set=['POST', 'GET', 'get_full_path'])
        self.request.POST = {}
        self.request.GET = {}
        self.request.get_full_path.side_effect = Exception('Not Called')

    def tearDown(self):
        self.mocked_by_id.stop()

    def test_basic(self):
        actual = provider_login_url(self.request, 'provider', 'process')
        self.assertEqual(actual, self.fake_url)
        self.provider.get_login_url.assert_called_once_with(
            self.request, process='process')

    def test_scope(self):
        actual = provider_login_url(
            self.request, 'provider', 'process', scope='SCOPE')
        self.assertEqual(actual, self.fake_url)
        self.provider.get_login_url.assert_called_once_with(
            self.request, process='process', scope='SCOPE')

    def test_auth_params(self):
        actual = provider_login_url(
            self.request, 'provider', 'process', auth_params={'foo': 'BAR'})
        self.assertEqual(actual, self.fake_url)
        self.provider.get_login_url.assert_called_once_with(
            self.request, process='process', auth_params={'foo': 'BAR'})

    def test_explicit_next(self):
        actual = provider_login_url(
            self.request, 'provider', 'process', next="/next")
        self.assertEqual(actual, self.fake_url)
        self.provider.get_login_url.assert_called_once_with(
            self.request, process='process', next="/next")

    def test_post_next(self):
        self.request.POST['next'] = '/post'
        self.request.GET['next'] = '/get'
        actual = provider_login_url(self.request, 'provider', 'process')
        self.assertEqual(actual, self.fake_url)
        self.provider.get_login_url.assert_called_once_with(
            self.request, process='process', next="/post")

    def test_get_next(self):
        self.request.GET['next'] = '/get'
        actual = provider_login_url(self.request, 'provider', 'process')
        self.assertEqual(actual, self.fake_url)
        self.provider.get_login_url.assert_called_once_with(
            self.request, process='process', next="/get")

    def test_redirect_next(self):
        self.request.get_full_path.side_effect = None
        self.request.get_full_path.return_value = 'http://example.com/full'
        actual = provider_login_url(self.request, 'provider', 'redirect')
        self.assertEqual(actual, self.fake_url)
        self.provider.get_login_url.assert_called_once_with(
            self.request, process='redirect', next="http://example.com/full")
