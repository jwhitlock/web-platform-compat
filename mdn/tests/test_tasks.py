"""Tests for mdn/tasks.py."""

from __future__ import unicode_literals
from json import dumps
import mock


from mdn.models import FeaturePage

from mdn.tasks import (
    start_crawl, fetch_meta, fetch_all_translations, fetch_translation,
    parse_page)
from webplatformcompat.models import Feature
from webplatformcompat.tests.base import TestCase


class TestStartCrawlTask(TestCase):
    def setUp(self):
        self.feature = self.create(Feature, slug='web-css-float')
        self.fp = FeaturePage.objects.create(
            feature=self.feature, status=FeaturePage.STATUS_STARTING,
            url="https://developer.mozilla.org/en-US/docs/Web/CSS/float")
        self.patcher_fetch_meta = mock.patch('mdn.tasks.fetch_meta.delay')
        self.mocked_fetch_meta = self.patcher_fetch_meta.start()
        self.mocked_fetch_meta.side_effect = Exception('Not Called')
        self.patcher_fetch_all = mock.patch(
            'mdn.tasks.fetch_all_translations.delay')
        self.mocked_fetch_all = self.patcher_fetch_all.start()
        self.mocked_fetch_all.side_effect = Exception('Not Called')

    def tearDown(self):
        self.patcher_fetch_meta.stop()
        self.patcher_fetch_all.stop()

    def test_no_meta(self):
        self.mocked_fetch_meta.side_effect = None
        start_crawl(self.fp.id)

        fp = FeaturePage.objects.get(id=self.fp.id)
        self.assertEqual(fp.STATUS_META, fp.status)
        self.mocked_fetch_meta.assertCalledOnce(fp.id)

    def test_meta_fetching(self):
        meta = self.fp.meta()
        meta.status = meta.STATUS_FETCHING
        meta.save()
        start_crawl(self.fp.id)

        fp = FeaturePage.objects.get(id=self.fp.id)
        self.assertEqual(fp.STATUS_META, fp.status)

    def test_meta_fetched(self):
        meta = self.fp.meta()
        meta.status = meta.STATUS_FETCHED
        meta.save()
        self.mocked_fetch_all.side_effect = None
        start_crawl(self.fp.id)

        fp = FeaturePage.objects.get(id=self.fp.id)
        self.assertEqual(fp.STATUS_PAGES, fp.status)
        self.mocked_fetch_all.assertCalledOnce(fp.id)

    def test_meta_error(self):
        meta = self.fp.meta()
        meta.status = meta.STATUS_ERROR
        meta.raw = "META ERROR"
        meta.save()
        start_crawl(self.fp.id)

        fp = FeaturePage.objects.get(id=self.fp.id)
        self.assertEqual(fp.STATUS_ERROR, fp.status)


class TestFetchMetaTask(TestCase):
    def setUp(self):
        self.feature = self.create(Feature, slug='web-css-float')
        self.fp = FeaturePage.objects.create(
            feature=self.feature, status=FeaturePage.STATUS_META,
            url="https://developer.mozilla.org/en-US/docs/Web/CSS/float")
        self.patcher_fetch_all = mock.patch(
            'mdn.tasks.fetch_all_translations.delay')
        self.mocked_fetch_all = self.patcher_fetch_all.start()
        self.mocked_fetch_all.side_effect = Exception('Not Called')
        self.patcher_get = mock.patch('mdn.tasks.requests.get')
        self.mocked_get = self.patcher_get.start()
        self.mocked_get.return_value = mock.Mock(
            spec_set=['status_code', 'json', 'text', 'raise_for_status'])
        self.response = self.mocked_get.return_value
        self.response.status_code = 200
        self.response.json.side_effect = Exception('Not Called')
        self.response.text = ""
        self.response.raise_for_status.side_effect = Exception('Not Called')

    def tearDown(self):
        self.patcher_fetch_all.stop()
        self.patcher_get.stop()

    def test_good_call(self):
        data = {
            'locale': 'en-US',
            'url': '/en-US/docs/Web/CSS/display',
            'translations': [{
                'locale': 'es',
                'url': '/es/docs/Web/CSS/display',
            }],
        }
        self.response.json.side_effect = None
        self.response.json.return_value = data
        self.mocked_fetch_all.side_effect = None

        fetch_meta(self.fp.id)
        fp = FeaturePage.objects.get(id=self.fp.id)
        self.assertEqual(fp.STATUS_PAGES, fp.status)
        self.assertEqual([], fp.data['meta']['scrape']['issues'])
        meta = fp.meta()
        self.assertEqual(meta.STATUS_FETCHED, meta.status)
        self.assertEqual(data, meta.data())
        self.mocked_fetch_all.assertCalledOnce(self.fp.id)

    def test_not_found(self):
        self.response.status_code = 404
        self.response.text = 'Not Found'
        self.response.raise_for_status.side_effect = RuntimeError('Was Called')

        self.assertRaises(RuntimeError, fetch_meta, self.fp.id)
        fp = FeaturePage.objects.get(id=self.fp.id)
        self.assertEqual(fp.STATUS_ERROR, fp.status)
        meta = fp.meta()
        issues = [[
            'failed_download', 0, 0,
            {'url': meta.url(), 'status': 404, 'content': 'Not Found'}]]
        self.assertEqual(issues, fp.data['meta']['scrape']['issues'])
        self.assertEqual(meta.STATUS_ERROR, meta.status)
        self.assertEqual('Status 404, Content:\nNot Found', meta.raw)

    def test_not_json(self):
        self.response.json.side_effect = ValueError('Not JSON')
        text = "I'm not JSON"
        self.response.text = text

        self.assertRaises(ValueError, fetch_meta, self.fp.id)
        fp = FeaturePage.objects.get(id=self.fp.id)
        self.assertEqual(fp.STATUS_ERROR, fp.status)
        issues = [[
            'bad_json', 0, 0, {'url': fp.url + '$json', 'content': text}]]
        self.assertEqual(issues, fp.data['meta']['scrape']['issues'])
        meta = fp.meta()
        self.assertEqual(meta.STATUS_ERROR, meta.status)
        self.assertEqual("Response is not JSON:\n" + text, meta.raw)


class TestFetchAllTranslationsTask(TestCase):
    def setUp(self):
        self.feature = self.create(Feature, slug='web-css-display')
        self.fp = FeaturePage.objects.create(
            feature=self.feature, status=FeaturePage.STATUS_PAGES,
            url="https://developer.mozilla.org/en-US/docs/Web/CSS/float")
        meta = self.fp.meta()
        meta.status = meta.STATUS_FETCHED
        meta.raw = dumps({
            'locale': 'en-US',
            'url': '/en-US/docs/Web/CSS/display',
            'translations': [{
                'locale': 'es',
                'url': '/es/docs/Web/CSS/display',
            }],
        })
        meta.save()

        self.patcher_fetch_trans = mock.patch(
            'mdn.tasks.fetch_translation.delay')
        self.mocked_fetch_trans = self.patcher_fetch_trans.start()
        self.mocked_fetch_trans.side_effect = Exception('Not Called')
        self.patcher_parse_page = mock.patch('mdn.tasks.parse_page.delay')
        self.mocked_parse_page = self.patcher_parse_page.start()
        self.mocked_parse_page.side_effect = Exception('Not Called')

    def tearDown(self):
        self.patcher_fetch_trans.stop()
        self.patcher_parse_page.stop()

    def test_fetch_all_start(self):
        self.mocked_fetch_trans.side_effect = None

        fetch_all_translations(self.fp.id)
        fp = FeaturePage.objects.get(id=self.fp.id)
        self.assertEqual(fp.STATUS_PAGES, fp.status)
        self.mocked_fetch_trans.assertCalledOnce(self.fp.id, 'en-US')
        self.mocked_fetch_trans.assertCalledOnce(self.fp.id, 'es')

    def test_fetch_all_in_progress(self):
        for t in self.fp.translations():
            t.status = t.STATUS_FETCHING
            t.save()

        fetch_all_translations(self.fp.id)
        fp = FeaturePage.objects.get(id=self.fp.id)
        self.assertEqual(fp.STATUS_PAGES, fp.status)

    def test_fetch_all_complete(self):
        for t in self.fp.translations():
            t.status = t.STATUS_FETCHED
            t.save()
        self.mocked_parse_page.side_effect = None

        fetch_all_translations(self.fp.id)
        fp = FeaturePage.objects.get(id=self.fp.id)
        self.assertEqual(fp.STATUS_PARSING, fp.status)
        self.mocked_parse_page.assertCalledOnce(self.fp.id)

    def test_fetch_one_issue(self):
        t = self.fp.translations()[-1]
        t.status = t.STATUS_ERROR
        t.raw = "Status 500, Content:\nServer Error"
        t.save()

        fetch_all_translations(self.fp.id)
        fp = FeaturePage.objects.get(id=self.fp.id)
        self.assertEqual(fp.STATUS_ERROR, fp.status)


class TestFetchTranslationTask(TestCase):
    def setUp(self):
        self.feature = self.create(Feature, slug='web-css-display')
        self.fp = FeaturePage.objects.create(
            feature=self.feature, status=FeaturePage.STATUS_PAGES,
            url='https://developer.mozilla.org/en-US/docs/Web/CSS/display')
        meta = self.fp.meta()
        meta.status = meta.STATUS_FETCHED
        meta.raw = dumps({
            'locale': 'en-US',
            'url': '/en-US/docs/Web/CSS/display',
            'translations': [{
                'locale': 'es',
                'url': '/es/docs/Web/CSS/display',
            }],
        })
        meta.save()
        self.fp.translatedcontent_set.create(locale='en-US')
        self.fp.translatedcontent_set.create(locale='es')

        self.patcher_fetch_all = mock.patch(
            'mdn.tasks.fetch_all_translations.delay')
        self.mocked_fetch_all = self.patcher_fetch_all.start()
        self.mocked_fetch_all.side_effect = Exception('Not Called')
        self.patcher_get = mock.patch('mdn.tasks.requests.get')
        self.mocked_get = self.patcher_get.start()
        self.mocked_get.return_value = mock.Mock(
            spec_set=['status_code', 'text', 'raise_for_status'])
        self.response = self.mocked_get.return_value
        self.response.status_code = 200
        self.response.text = "Some page text"
        self.response.raise_for_status.side_effect = Exception('Not Called')

    def tearDown(self):
        self.patcher_fetch_all.stop()
        self.patcher_get.stop()

    def test_good_call(self):
        self.mocked_fetch_all.side_effect = None

        fetch_translation(self.fp.id, 'en-US')
        fp = FeaturePage.objects.get(id=self.fp.id)
        self.assertEqual(fp.STATUS_PAGES, fp.status)
        trans = fp.translatedcontent_set.get(locale='en-US')
        self.assertEqual(trans.STATUS_FETCHED, trans.status)
        self.mocked_fetch_all.assertCalledOnce(self.fp.id)

    def test_parsing(self):
        self.fp.status = self.fp.STATUS_PARSING
        self.fp.save()
        t = self.fp.translatedcontent_set.get(locale='en-US')
        t.status = t.STATUS_FETCHED
        t.save()

        fetch_translation(self.fp.id, 'en-US')
        fp = FeaturePage.objects.get(id=self.fp.id)
        self.assertEqual(fp.STATUS_PARSING, fp.status)
        trans = fp.translatedcontent_set.get(locale='en-US')
        self.assertEqual(trans.STATUS_FETCHED, trans.status)

    def test_parsed(self):
        self.fp.status = self.fp.STATUS_PARSING
        self.fp.save()
        t = self.fp.translatedcontent_set.get(locale='en-US')
        t.status = t.STATUS_FETCHED
        t.save()

        fetch_translation(self.fp.id, 'en-US')
        fp = FeaturePage.objects.get(id=self.fp.id)
        self.assertEqual(fp.STATUS_PARSING, fp.status)
        trans = fp.translatedcontent_set.get(locale='en-US')
        self.assertEqual(trans.STATUS_FETCHED, trans.status)

    def test_not_found(self):
        self.response.status_code = 404
        self.response.text = 'Not Found'
        self.response.raise_for_status.side_effect = RuntimeError('Was Called')

        self.assertRaises(RuntimeError, fetch_translation, self.fp.id, 'es')
        fp = FeaturePage.objects.get(id=self.fp.id)
        self.assertEqual(fp.STATUS_ERROR, fp.status)
        trans = fp.translatedcontent_set.get(locale='es')
        self.assertEqual(trans.STATUS_ERROR, trans.status)
        expected_msg = "Status 404, Content:\nNot Found"
        self.assertEqual(expected_msg, trans.raw)
        url = trans.url() + '?raw'
        issue = [[
            'failed_download', 0, 0,
            {'url': url, 'status': 404, 'content': 'Not Found'}]]
        self.assertEqual(issue, fp.data['meta']['scrape']['issues'])


class TestParsePageTask(TestCase):

    @mock.patch('mdn.tasks.scrape_feature_page')
    def test_call(self, mock_scrape):
        fp = FeaturePage.objects.create(
            feature_id=666, status=FeaturePage.STATUS_PARSING)
        parse_page(fp.id)
        mock_scrape.assertCalledOnce(fp.id)

    @mock.patch('mdn.tasks.scrape_feature_page')
    def test_exception(self, mock_scrape):
        mock_scrape.side_effect = ValueError("Unexpected error")
        feature = self.create(Feature, slug="the-slug")
        fp = FeaturePage.objects.create(
            feature=feature, status=FeaturePage.STATUS_PARSING)
        self.assertRaises(ValueError, parse_page, fp.id)
        mock_scrape.assertCalledOnce(fp.id)
        fp = FeaturePage.objects.get(id=fp.id)
        issues = fp.data['meta']['scrape']['issues']
        self.assertEqual(1, len(issues))
        self.assertEqual('exception', issues[0][0])
