# -*- coding: utf-8 -*-
"""Tests for MDN importer views."""

from __future__ import unicode_literals
import mock

from django.contrib.auth.models import Group
from django.core.urlresolvers import reverse

from mdn.models import FeaturePage, Issue
from webplatformcompat.models import Feature
from webplatformcompat.tests.base import TestCase


class TestFeaturePageListView(TestCase):
    def setUp(self):
        self.url = reverse('feature_page_list')

    def add_page(self):
        feature = self.create(Feature, slug='web-css-display')
        return FeaturePage.objects.create(
            url="https://developer.mozilla.org/en-US/docs/Web/CSS/display",
            feature=feature)

    def test_empty_list(self):
        response = self.client.get(self.url)
        self.assertEqual(200, response.status_code)
        pages = response.context_data['page_obj']
        self.assertEqual(0, len(pages.object_list))

    def test_populated_list(self):
        feature_page = self.add_page()
        response = self.client.get(self.url)
        self.assertEqual(200, response.status_code)
        pages = response.context_data['page_obj']
        self.assertEqual(1, len(pages.object_list))
        obj = pages.object_list[0]
        self.assertEqual(obj.id, feature_page.id)
        data_counts = [
            ('Critical errors', ('danger', 'striped'), 0, 0),
            ('Errors', ('danger',), 0, 0),
            ('Warnings', ('warning',), 0, 0),
            ('No Errors', ('success',), 0, 0),
        ]
        self.assertEqual(data_counts, response.context_data['data_counts'])
        status_counts = {'total': 1, 'data': 0, 'no_data': 0, 'other': 1}
        self.assertEqual(status_counts, response.context_data['status_counts'])

    def test_with_issue(self):
        feature_page = self.add_page()
        feature_page.issues.create(slug='halt_import', start=1, end=1)
        feature_page.status = FeaturePage.STATUS_PARSED_CRITICAL
        feature_page.save()
        response = self.client.get(self.url)
        self.assertEqual(200, response.status_code)
        data_counts = [
            ('Critical errors', ('danger', 'striped'), 1, '100.0'),
            ('Errors', ('danger',), 0, 0),
            ('Warnings', ('warning',), 0, 0),
            ('No Errors', ('success',), 0, 0),
        ]
        self.assertEqual(data_counts, response.context_data['data_counts'])
        status_counts = {'total': 1, 'data': 1, 'no_data': 0, 'other': 0}
        self.assertEqual(status_counts, response.context_data['status_counts'])

    def test_topic_filter(self):
        feature_page = self.add_page()
        FeaturePage.objects.create(
            url="https://developer.mozilla.org/en-US/docs/Other",
            feature_id=2)
        url = self.url + "?topic=docs/Web"
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)
        pages = response.context_data['page_obj']
        self.assertEqual(1, len(pages.object_list))
        obj = pages.object_list[0]
        self.assertEqual(obj.id, feature_page.id)

    def test_status_filter(self):
        feature_page = self.add_page()
        feature_page.status = FeaturePage.STATUS_PARSED_CRITICAL
        feature_page.save()
        FeaturePage.objects.create(
            url="https://developer.mozilla.org/en-US/docs/Other",
            status=FeaturePage.STATUS_PARSED,
            feature_id=2)
        url = self.url + "?status=%s" % FeaturePage.STATUS_PARSED_CRITICAL
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)
        pages = response.context_data['page_obj']
        self.assertEqual(1, len(pages.object_list))
        obj = pages.object_list[0]
        self.assertEqual(obj.id, feature_page.id)

    def test_status_other_filter(self):
        feature_page = self.add_page()
        feature_page.status = FeaturePage.STATUS_META
        feature_page.save()
        FeaturePage.objects.create(
            url="https://developer.mozilla.org/en-US/docs/Other",
            status=FeaturePage.STATUS_PARSED,
            feature_id=2)
        url = self.url + "?status=other"
        response = self.client.get(url)
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
        mock_task.assert_called_once_with(feature_page.id)


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
        self.feature = self.create(Feature, slug='web_css_float')

    def test_get(self):
        response = self.client.get(self.url)
        self.assertEqual(200, response.status_code)
        self.assertEqual("Search by URL", response.context_data['action'])

    def test_post_found(self):
        fp = FeaturePage.objects.create(
            url=self.mdn_url, feature_id=self.feature.id)
        response = self.client.get(self.url, {'url': self.mdn_url})
        next_url = reverse('feature_page_detail', kwargs={'pk': fp.id})
        self.assertRedirects(response, next_url)

    def test_post_found_with_anchor(self):
        fp = FeaturePage.objects.create(
            url=self.mdn_url, feature_id=self.feature.id)
        url = self.mdn_url + "#Browser_Compat"
        response = self.client.get(self.url, {'url': url})
        next_url = reverse('feature_page_detail', kwargs={'pk': fp.id})
        self.assertRedirects(response, next_url)

    def test_post_found_topic(self):
        FeaturePage.objects.create(
            url=self.mdn_url, feature_id=self.feature.id)
        url = "https://developer.mozilla.org/en-US/docs/Web"
        response = self.client.get(self.url, {'url': url})
        next_url = reverse('feature_page_list') + '?topic=docs/Web'
        self.assertRedirects(response, next_url)

    def test_post_found_topic_trailing_slash(self):
        FeaturePage.objects.create(
            url=self.mdn_url, feature_id=self.feature.id)
        url = "https://developer.mozilla.org/en-US/docs/Web/"
        response = self.client.get(self.url, {'url': url})
        next_url = reverse('feature_page_list') + '?topic=docs/Web'
        self.assertRedirects(response, next_url)

    def test_not_found_with_perms(self):
        self.user.groups.add(Group.objects.get(name='import-mdn'))
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
        mocked_parse.assert_called_once_with(self.fp.pk)
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
        mocked_crawl.assert_called_once_with(self.fp.pk)
        fp = FeaturePage.objects.get(id=self.fp.id)
        self.assertEqual(fp.STATUS_STARTING, fp.status)


class TestIssuesDetail(TestCase):
    def setUp(self):
        self.feature = self.create(Feature, slug='web-css-float')
        self.fp = FeaturePage.objects.create(
            url="https://developer.mozilla.org/en-US/docs/Web/CSS/float",
            feature_id=self.feature.id, data='{"foo": "bar"}',
            status=FeaturePage.STATUS_PARSED)
        self.issue = Issue.objects.create(
            page=self.fp, slug="inline-text", start=10, end=20)

    def test_get_with_issues(self):
        url = reverse('issues_detail', kwargs={'slug': 'inline-text'})
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, response.context_data['count'])
        self.assertEqual([], response.context_data['headers'])

    def test_get_with_issue_parameters(self):
        self.issue.params = {'text': 'inline text'}
        self.issue.save()
        url = reverse('issues_detail', kwargs={'slug': 'inline-text'})
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)
        self.assertEqual(1, response.context_data['count'])
        self.assertEqual(['Page', 'text'], response.context_data['headers'])

    def test_get_without_issues(self):
        url = reverse('issues_detail', kwargs={'slug': 'other'})
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)
        self.assertEqual(0, response.context_data['count'])


class TestIssuesSummary(TestCase):
    def test_get(self):
        url = reverse('issues_summary')
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)


class CSVTestCase(TestCase):
    def setUp(self):
        self.feature = self.create(Feature, slug='web-css-float')
        self.fp = FeaturePage.objects.create(
            url="https://developer.mozilla.org/en-US/docs/Web/CSS/float",
            feature_id=self.feature.id, data='{"foo": "bar"}',
            status=FeaturePage.STATUS_PARSED)
        self.issue = Issue.objects.create(
            page=self.fp, slug="inline-text", start=10, end=20,
            params='{"text": "inline"}')

    def assert_csv_response(self, url, expected_lines):
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)
        csv_lines = response.content.decode('utf8').splitlines()
        self.assertEqual(expected_lines, csv_lines)


class TestIssuesDetailCSV(CSVTestCase):
    def test_get(self):
        url = reverse('issues_detail_csv', kwargs={'slug': 'inline-text'})
        full_url = 'http://testserver/importer/{}'.format(self.fp.pk)
        expected = [
            'MDN Slug,Import URL,Source Start,Source End,text',
            'docs/Web/CSS/float,{},10,20,inline'.format(full_url),
        ]
        self.assert_csv_response(url, expected)


class TestIssuesSummaryCSV(CSVTestCase):
    def test_get(self):
        url = reverse('issues_summary_csv')
        expected = [
            'Count,Issue',
            '1,inline-text',
        ]
        self.assert_csv_response(url, expected)
