# -*- coding: utf-8 -*-
"""Tests for MDN importer models."""

from __future__ import unicode_literals
from json import dumps

from django.core.exceptions import ValidationError
from django.utils.six import text_type

from mdn.models import (
    validate_mdn_url, FeaturePage, PageMeta, TranslatedContent)
from webplatformcompat.models import Feature
from webplatformcompat.tests.base import TestCase


class TestValidateMdnUrl(TestCase):
    def setUp(self):
        self.url = "https://developer.mozilla.org/en-US/docs/Web/CSS/float"

    def test_OK(self):
        validate_mdn_url(self.url)

    def test_raw(self):
        url = self.url + '?raw'
        self.assertRaises(ValidationError, validate_mdn_url, url)

    def test_json(self):
        url = self.url + '$json'
        self.assertRaises(ValidationError, validate_mdn_url, url)

    def test_anchor(self):
        url = self.url + '#Specifications'
        self.assertRaises(ValidationError, validate_mdn_url, url)

    def test_bad_domain(self):
        url = "http://docs.webplatform.org/wiki/html/elements/ruby"
        self.assertRaises(ValidationError, validate_mdn_url, url)


class TestFeaturePageModel(TestCase):
    def setUp(self):
        self.feature = self.create(Feature, slug='web-css-float')
        self.fp = FeaturePage.objects.create(
            url="https://developer.mozilla.org/en-US/docs/Web/CSS/float",
            feature=self.feature, status=FeaturePage.STATUS_META)
        self.metadata = {
            "locale": "en-US",
            "url": "https://developer.mozilla.org/en-US/docs/Web/CSS/float",
            "translations": [{
                "locale": "de",
                "url": "https://developer.mozilla.org/de/docs/Web/CSS/float",
            }],
        }

    def test_domain(self):
        self.assertEqual("https://developer.mozilla.org", self.fp.domain())

    def test_str(self):
        expected = "Fetching Metadata for Web/CSS/float"
        self.assertEqual(expected, str(self.fp))

    def test_meta_new(self):
        meta = self.fp.meta()
        self.assertEqual('/en-US/docs/Web/CSS/float$json', meta.path)
        self.assertEqual(meta.STATUS_STARTING, meta.status)

    def test_meta_existing(self):
        pm = PageMeta.objects.create(page=self.fp, path='/foo/path')
        meta = self.fp.meta()
        self.assertEqual(pm, meta)

    def test_translations_no_meta(self):
        translations = self.fp.translations()
        self.assertEqual(0, len(translations))

    def test_translations_new(self):
        PageMeta.objects.create(
            page=self.fp, path='/foo/path', status=PageMeta.STATUS_FETCHED,
            raw=dumps(self.metadata))
        t1, t2 = self.fp.translations()
        self.assertEqual('en-US', t1.locale)
        self.assertEqual('de', t2.locale)

    def setup_content(self):
        PageMeta.objects.create(
            page=self.fp, path='/foo/path', status=PageMeta.STATUS_FETCHED,
            raw=dumps(self.metadata))
        TranslatedContent.objects.create(
            page=self.fp, locale='en', path='/foo/en/path',
            status=PageMeta.STATUS_FETCHED, raw="Black, White, Yellow, Red")
        TranslatedContent.objects.create(
            page=self.fp, locale='de', path='/foo/de/path',
            status=PageMeta.STATUS_ERROR, raw="Schwarz, Weiß, Gelb, Rot")

    def test_reset(self):
        self.setup_content()
        self.fp.reset()
        meta = self.fp.meta()
        self.assertEqual(meta.status, PageMeta.STATUS_STARTING)
        t_en = TranslatedContent.objects.get(page=self.fp, locale='en')
        self.assertEqual(t_en.status, PageMeta.STATUS_STARTING)
        t_de = TranslatedContent.objects.get(page=self.fp, locale='de')
        self.assertEqual(t_de.status, PageMeta.STATUS_STARTING)

    def test_reset_without_clear(self):
        self.setup_content()
        self.fp.reset(False)
        meta = self.fp.meta()
        self.assertEqual(meta.status, PageMeta.STATUS_STARTING)
        t_en = TranslatedContent.objects.get(page=self.fp, locale='en')
        self.assertEqual(t_en.status, PageMeta.STATUS_FETCHED)
        t_de = TranslatedContent.objects.get(page=self.fp, locale='de')
        self.assertEqual(t_de.status, PageMeta.STATUS_STARTING)

    def test_get_data_existing(self):
        self.fp.raw_data = '{"foo": "bar"}'
        self.assertEqual({"foo": "bar"}, self.fp.data)

    def test_get_data_none(self):
        self.fp.raw_data = None
        self.assertEqual(
            ['features', 'linked', 'meta'],
            list(self.fp.data.keys()))

    def test_get_data_empty(self):
        self.fp.raw_data = ''
        self.assertEqual(
            ['features', 'linked', 'meta'],
            list(self.fp.data.keys()))

    def test_add_error(self):
        error = "This is an error"
        self.fp.add_error(error)
        self.assertEqual(
            ['<pre>This is an error</pre>'],
            self.fp.data['meta']['scrape']['errors'])

    def test_add_error_safe(self):
        error = "This is an error"
        self.fp.add_error(error, True)
        self.assertEqual(
            ['This is an error'],
            self.fp.data['meta']['scrape']['errors'])

    def test_add_duplicate_error(self):
        error = "Duplicate error"
        self.fp.add_error(error)
        self.fp.add_error(error)
        self.assertEqual(
            ['<pre>Duplicate error</pre>'],
            self.fp.data['meta']['scrape']['errors'])


class TestPageMetaModel(TestCase):
    def setUp(self):
        fp = FeaturePage(
            url="https://developer.mozilla.org/en-US/docs/Web/CSS/display",
            feature_id=666,
            status=FeaturePage.STATUS_PARSED)
        self.meta = PageMeta(page=fp, path="/de/docs/Web/CSS/display")

    def test_str(self):
        expected = u'/de/docs/Web/CSS/display retrieved 0\xa0minutes ago'
        self.assertEqual(expected, text_type(self.meta))

    def test_url(self):
        expected = "https://developer.mozilla.org/de/docs/Web/CSS/display"
        self.assertEqual(expected, self.meta.url())

    def test_data_fetched(self):
        data = {'foo': 'bar'}
        self.meta.status = self.meta.STATUS_FETCHED
        self.meta.raw = dumps(data)
        self.assertEqual(data, self.meta.data())

    def test_locale_paths_new(self):
        self.assertEqual([], self.meta.locale_paths())

    def test_locale_paths_fetched(self):
        data = {
            'locale': 'en-US',
            'url': 'https://developer.mozilla.org/en-US/docs/Web/CSS/display',
            'translations': [{
                'locale': 'es',
                'url': 'https://developer.mozilla.org/es/docs/Web/CSS/display',
            }],
        }
        self.meta.status = self.meta.STATUS_FETCHED
        self.meta.raw = dumps(data)
        expected = [
            ('en-US',
             'https://developer.mozilla.org/en-US/docs/Web/CSS/display'),
            ('es', 'https://developer.mozilla.org/es/docs/Web/CSS/display'),
        ]
        self.assertEqual(expected, self.meta.locale_paths())


class TestTranslatedContentModel(TestCase):
    def setUp(self):
        fp = FeaturePage(
            url="https://developer.mozilla.org/en-US/docs/Web/CSS/float",
            feature_id=666,
            status=FeaturePage.STATUS_PARSED)
        self.c = TranslatedContent(
            page=fp,
            locale="de",
            path="/de/docs/Web/CSS/float")

    def test_str(self):
        expected = u'/de/docs/Web/CSS/float retrieved 0\xa0minutes ago'
        self.assertEqual(expected, text_type(self.c))

    def test_url(self):
        expected = "https://developer.mozilla.org/de/docs/Web/CSS/float"
        self.assertEqual(expected, self.c.url())
