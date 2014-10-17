#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for `web-platform-compat` validators module.
"""
from django.core.exceptions import ValidationError
from django.test import TestCase

from webplatformcompat.validators import LanguageDictValidator


class SharedLanguageDictValidatorTests(object):

    def test_success(self):
        self.validator({'en': 'English'})

    def test_string_fails(self):
        self.assertRaises(ValidationError, self.validator, 'en')

    def test_list_fails(self):
        self.assertRaises(ValidationError, self.validator, ['en'])

    def test_no_en_fails(self):
        val = {'es': 'Espanol'}
        self.assertRaises(ValidationError, self.validator, val)

    def test_int_value_fails(self):
        val = {'en': 1337}
        self.assertRaises(ValidationError, self.validator, val)

    def test_zxx_and_en_fails(self):
        val = {'en': 'English', 'zxx': 'canonical'}
        self.assertRaises(ValidationError, self.validator, val)


class TestLanguageDictValidator(SharedLanguageDictValidatorTests, TestCase):

    def setUp(self):
        self.validator = LanguageDictValidator()

    def test_zxx_fails(self):
        val = {'zxx': 'display'}
        self.assertRaises(ValidationError, self.validator, val)


class TestCanonicalDictValidator(SharedLanguageDictValidatorTests, TestCase):

    def setUp(self):
        self.validator = LanguageDictValidator(allow_canonical=True)

    def test_zxx_success(self):
        self.validator({'zxx': 'display'})
