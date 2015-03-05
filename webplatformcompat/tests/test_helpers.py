# -*- coding: utf-8 -*-
"""Tests for jingo/jinja2 helper functions and filters."""

from __future__ import unicode_literals

from django.test import override_settings
from jinja2 import Markup

from webplatformcompat.helpers import (
    is_debug, pick_translation, trans_span, trans_str)

from .base import TestCase


class TestPickTranslation(TestCase):
    def setUp(self):
        self.context = {'lang': 'en'}
        self.trans_obj = {
            'en': 'English',
            'es': 'Español',
        }

    def test_empty(self):
        result = pick_translation(self.context, {})
        self.assertEqual(('', None), result)

    def test_canonical(self):
        result = pick_translation(self.context, 'canonical string')
        self.assertEqual(('canonical string', None), result)

    def test_canonical_html(self):
        result = pick_translation(self.context, '<input>')
        self.assertEqual(('<input>', None), result)

    def test_match_en(self):
        result = pick_translation(self.context, self.trans_obj)
        self.assertEqual(('English', 'en'), result)

    def test_match_es(self):
        self.context['lang'] = 'es'
        result = pick_translation(self.context, self.trans_obj)
        self.assertEqual(('Español', 'es'), result)

    def test_no_match(self):
        self.context['lang'] = 'ru'
        result = pick_translation(self.context, self.trans_obj)
        self.assertEqual(('English', 'en'), result)


class TestTransSpan(TestCase):
    def setUp(self):
        self.context = {'lang': 'en'}
        self.trans_obj = {
            'en': 'English',
            'es': 'Español',
        }

    def test_empty(self):
        result = trans_span(self.context, {})
        self.assertEqual(Markup(''), result)

    def test_canonical(self):
        result = trans_span(self.context, 'canonical string')
        self.assertEqual('<code>canonical string</code>', result)
        self.assertIsInstance(result, Markup)

    def test_canonical_html(self):
        result = trans_span(self.context, '<input>')
        self.assertEqual('<code>&lt;input&gt;</code>', result)
        self.assertIsInstance(result, Markup)

    def test_match_en(self):
        result = trans_span(self.context, self.trans_obj)
        self.assertEqual('English', result)
        self.assertIsInstance(result, Markup)

    def test_match_es(self):
        self.context['lang'] = 'es'
        result = trans_span(self.context, self.trans_obj)
        self.assertEqual('Español', result)
        self.assertIsInstance(result, Markup)

    def test_no_match(self):
        self.context['lang'] = 'ru'
        result = trans_span(self.context, self.trans_obj)
        self.assertEqual('<span lang="en">English</span>', result)
        self.assertIsInstance(result, Markup)


class TestTransStr(TestCase):
    def setUp(self):
        self.context = {'lang': 'en'}
        self.trans_obj = {
            'en': 'English',
            'es': 'Español',
        }

    def test_empty(self):
        result = trans_str(self.context, {})
        self.assertEqual('', result)

    def test_canonical(self):
        result = trans_str(self.context, 'canonical string')
        self.assertEqual('canonical string', result)

    def test_canonical_html(self):
        result = trans_str(self.context, '<input>')
        self.assertEqual('<input>', result)

    def test_match_en(self):
        result = trans_str(self.context, self.trans_obj)
        self.assertEqual('English', result)

    def test_match_es(self):
        self.context['lang'] = 'es'
        result = trans_str(self.context, self.trans_obj)
        self.assertEqual('Español', result)

    def test_no_match(self):
        self.context['lang'] = 'ru'
        result = trans_str(self.context, self.trans_obj)
        self.assertEqual('English', result)


class TestDebug(TestCase):

    @override_settings(DEBUG=True)
    def test_debug_on(self):
        self.assertTrue(is_debug())

    @override_settings(DEBUG=False)
    def test_debug_off(self):
        self.assertFalse(is_debug())
