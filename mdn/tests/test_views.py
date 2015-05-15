# -*- coding: utf-8 -*-
"""Tests for MDN importer views."""

from __future__ import unicode_literals
import mock

from django.core.urlresolvers import reverse

from mdn.models import FeaturePage
from webplatformcompat.models import Feature
from webplatformcompat.tests.base import TestCase


class TestFeaturePageListView(TestCase):
    def setUp(self):
        self.url = reverse('feature_page_list')

    def test_empty_list(self):
        response = self.client.get(self.url)
        self.assertEqual(200, response.status_code)
        pages = response.context_data['page_obj']
        self.assertEqual(0, len(pages.object_list))

    def test_populated_list(self):
        feature_page = FeaturePage.objects.create(
            url="https://developer.mozilla.org/en-US/docs/Web/CSS/display",
            feature_id=1)
        response = self.client.get(self.url)
        self.assertEqual(200, response.status_code)
        pages = response.context_data['page_obj']
        self.assertEqual(1, len(pages.object_list))
        obj = pages.object_list[0]
        self.assertEqual(obj.id, feature_page.id)


class TestFeaturePageCreateView(TestCase):
    def setUp(self):
        self.login_user(groups=['import-mdn', 'change-resource'])
        self.url = reverse('feature_page_create')
        self.feature = self.create(Feature)

    def test_get(self):
        response = self.client.get(self.url)
        self.assertEqual(200, response.status_code, response.content)

    def test_get_prefill_url(self):
        response = self.client.get(self.url, {'url': 'http://example.com'})
        self.assertEqual(200, response.status_code, response.content)
        self.assertContains(response, 'value="http://example.com"')

    @mock.patch('mdn.views.start_crawl.delay')
    def test_post_url(self, mock_task):
        mdn_url = (
            "https://developer.mozilla.org/en-US/docs/Web/CSS/animation-name")
        data = {
            "url": mdn_url,
            "feature": self.feature.id
        }
        response = self.client.post(self.url, data)
        self.assertEqual(302, response.status_code, response.content)
        feature_page = FeaturePage.objects.get()
        self.assertEqual(feature_page.url, mdn_url)
        self.assertEqual(feature_page.feature_id, self.feature.id)
        expected = 'http://testserver' + feature_page.get_absolute_url()
        self.assertEqual(expected, response["LOCATION"])
        mock_task.assertCalledOnce(feature_page.id)


class TestFeaturePageDetailView(TestCase):
    def test_get(self):
        feature = self.create(Feature, slug='web-css-float')
        feature_page = FeaturePage.objects.create(
            url="https://developer.mozilla.org/en-US/docs/Web/CSS/float",
            feature=feature)
        url = reverse('feature_page_detail', kwargs={'pk': feature_page.id})
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)
        obj = response.context_data['object']
        self.assertEqual(obj.id, feature_page.id)


class TestFeaturePageJSONView(TestCase):
    def test_get(self):
        feature_page = FeaturePage.objects.create(
            url="https://developer.mozilla.org/en-US/docs/Web/CSS/float",
            feature_id=741, raw_data='{"meta": {"scrape": {"issues": []}}}')
        url = reverse('feature_page_json', kwargs={'pk': feature_page.id})
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)
        self.assertEqual('application/json', response['Content-Type'])
        expected = b'{"meta": {"scrape": {"issues": []}}}'
        self.assertEqual(expected, response.content)


class TestFeaturePageSearch(TestCase):
    def setUp(self):
        self.url = reverse('feature_page_search')
        self.mdn_url = "https://developer.mozilla.org/en-US/docs/Web/CSS/float"

    def test_get(self):
        response = self.client.get(self.url)
        self.assertEqual(200, response.status_code)
        self.assertEqual("Search by URL", response.context_data['action'])

    def test_post_found(self):
        fp = FeaturePage.objects.create(
            url=self.mdn_url, feature_id=741, data='{"foo": "bar"}')
        response = self.client.get(self.url, {'url': self.mdn_url})
        next_url = reverse('feature_page_detail', kwargs={'pk': fp.id})
        self.assertRedirects(response, next_url)

    def test_not_found_with_perms(self):
        self.login_user(groups=['import-mdn'])
        response = self.client.get(self.url, {'url': self.mdn_url})
        next_url = reverse('feature_page_create') + '?url=' + self.mdn_url
        self.assertRedirects(response, next_url)

    def test_not_found_without_perms(self):
        response = self.client.get(self.url, {'url': self.mdn_url})
        next_url = reverse('feature_page_list')
        self.assertRedirects(response, next_url)


class TestFeaturePageReParseView(TestCase):

    def setUp(self):
        self.feature = self.create(Feature, slug='web-css-float')
        self.fp = FeaturePage.objects.create(
            url="https://developer.mozilla.org/en-US/docs/Web/CSS/float",
            feature=self.feature, data='{"foo": "bar"}',
            status=FeaturePage.STATUS_PARSED)
        self.url = reverse('feature_page_reparse', kwargs={'pk': self.fp.pk})

    def test_get(self):
        response = self.client.get(self.url)
        self.assertEqual(200, response.status_code)
        self.assertEqual("Re-parse MDN Page", response.context_data['action'])

    @mock.patch('mdn.views.parse_page.delay')
    def test_post(self, mocked_parse):
        response = self.client.post(self.url)
        dest_url = reverse('feature_page_detail', kwargs={'pk': self.fp.pk})
        self.assertRedirects(response, dest_url)
        mocked_parse.assertCalledOnce(self.fp.pk)
        fp = FeaturePage.objects.get(id=self.fp.id)
        self.assertEqual(fp.STATUS_PARSING, fp.status)


class TestFeaturePageResetView(TestCase):

    def setUp(self):
        self.feature = self.create(Feature, slug='web-css-float')
        self.fp = FeaturePage.objects.create(
            url="https://developer.mozilla.org/en-US/docs/Web/CSS/float",
            feature_id=self.feature.id, data='{"foo": "bar"}',
            status=FeaturePage.STATUS_PARSED)
        self.url = reverse('feature_page_reset', kwargs={'pk': self.fp.pk})

    def test_get(self):
        response = self.client.get(self.url)
        self.assertEqual(200, response.status_code)
        self.assertEqual("Reset MDN Page", response.context_data['action'])

    @mock.patch('mdn.views.start_crawl.delay')
    def test_post(self, mocked_crawl):
        response = self.client.post(self.url)
        dest_url = reverse('feature_page_detail', kwargs={'pk': self.fp.pk})
        self.assertRedirects(response, dest_url)
        mocked_crawl.assertCalledOnce(self.fp.pk)
        fp = FeaturePage.objects.get(id=self.fp.id)
        self.assertEqual(fp.STATUS_STARTING, fp.status)


class TestIssuesSummary(TestCase):
    def test_get(self):
        url = reverse('issues_summary')
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)
