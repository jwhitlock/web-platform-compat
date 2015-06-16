#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for `web-platform-compat` fields module."""

from collections import OrderedDict

from django.core.exceptions import ValidationError
from django.test import TestCase

from rest_framework.serializers import ValidationError as DRFValidationError

from webplatformcompat.drf_fields import (
    OptionalCharField, OptionalIntegerField, TranslatedTextField)


class SharedTranslatedTextFieldTests(object):
    def test_to_representation_falsy(self):
        # Converting to serializable form, falsy becomes None
        self.assertIsNone(self.ttf.to_representation(''))

    def test_to_representation_dict(self):
        # Converting to serializable form, dicts are passed through
        data = {"key": "value"}
        self.assertEqual(data, self.ttf.to_representation(data))

    def test_to_representation_sorted_dict(self):
        # Converting to serializable form, dict is sorted, English first
        data = {'es': 'Spanish', 'en': 'English', 'ru': 'Russian'}
        expected = OrderedDict([
            ('en', 'English'),
            ('es', 'Spanish'),
            ('ru', 'Russian')])
        self.assertEqual(expected, self.ttf.to_representation(data))
        self.assertEqual(
            expected.keys(), self.ttf.to_representation(data).keys())

    def test_to_internal_value_falsy(self):
        # Converting from serialized form, false values are None
        self.assertIsNone(self.ttf.to_internal_value(''))

    def test_to_internal_value_spaces(self):
        # Converting from serialized form, spaces are None
        self.assertIsNone(self.ttf.to_internal_value('  '))

    def test_to_internal_value_json(self):
        # Converting from serialized form, JSON becomes dict
        json_in = '{"key": "value"}'
        json_out = {"key": "value"}
        self.assertEqual(json_out, self.ttf.to_internal_value(json_in))

    def test_run_validation_empty_string(self):
        self.assertRaises(DRFValidationError, self.ttf.run_validation, '')

    def test_run_validation_null(self):
        self.assertIsNone(self.ttf.run_validation(None))


class TestTranslatedTextField(SharedTranslatedTextFieldTests, TestCase):

    def setUp(self):
        self.ttf = TranslatedTextField()

    def test_to_representation_canonical(self):
        # Converting to serializable form, canonical dicts become strings
        data = {"zxx": "canonical"}
        self.assertEqual(None, self.ttf.to_representation(data))

    def test_to_internal_value_string(self):
        # Converting from serialized form, string remains string, validation
        # will raise an error
        self.assertEqual("display", self.ttf.to_internal_value('"display"'))

    def test_to_internal_value_null(self):
        self.assertEqual(None, self.ttf.to_internal_value(None))

    def test_to_internal_value_bad_json(self):
        # Converting from serialized form, bad JSON becomes ValidationError
        bad_json = "{'quotes': 'wrong ones'}"
        self.assertRaises(
            ValidationError, self.ttf.to_internal_value, bad_json)

    def test_to_internal_value_string_true(self):
        self.assertEqual('false', self.ttf.to_internal_value('false'))

    def test_to_internal_value_list(self):
        self.assertEqual('["list"]', self.ttf.to_internal_value('["list"]'))


class TestCanonTranslatedTextField(SharedTranslatedTextFieldTests, TestCase):

    def setUp(self):
        self.ttf = TranslatedTextField(allow_canonical=True)

    def test_to_representation_canonical(self):
        # Converting to serializable form, canonical dicts become strings
        data = {"zxx": "canonical"}
        self.assertEqual("canonical", self.ttf.to_representation(data))

    def test_to_internal_value_string(self):
        # Converting from serialized form, string become canonical dicts
        expected = {"zxx": "display"}
        self.assertEqual(expected, self.ttf.to_internal_value('"display"'))

    def test_to_internal_value_bad_json(self):
        # Converting from serialized form, bad JSON becomes canonical
        bad_json = "{'quotes': 'wrong ones'}"
        expected = {"zxx": "{'quotes': 'wrong ones'}"}
        self.assertEqual(expected, self.ttf.to_internal_value(bad_json))

    def test_to_internal_value_string_true(self):
        self.assertEqual({'zxx': 'false'}, self.ttf.to_internal_value('false'))

    def test_to_internal_value_list(self):
        self.assertEqual(
            {'zxx': '["list"]'}, self.ttf.to_internal_value('["list"]'))


class SharedOptionalCharFieldTests(object):
    def test_to_representation_string(self):
        self.assertEqual('foo', self.ocf.to_representation('foo'))

    def test_to_representation_empty_string(self):
        self.assertEqual(None, self.ocf.to_representation(''))

    def test_to_internal_value_string(self):
        self.assertEqual('foo', self.ocf.to_internal_value('foo'))

    def test_to_internal_value_null(self):
        self.assertEqual('', self.ocf.to_internal_value(None))

    def test_run_validation_empty_string(self):
        self.assertRaises(DRFValidationError, self.ocf.run_validation, '')

    def test_run_validation_null(self):
        self.assertEqual('', self.ocf.run_validation(None))


class TestNonOptionalCharField(SharedOptionalCharFieldTests, TestCase):
    def setUp(self):
        self.ocf = OptionalCharField(required=True)


class TestOptionalCharField(SharedOptionalCharFieldTests, TestCase):
    def setUp(self):
        self.ocf = OptionalCharField()


class SharedOptionalIntegerFieldTests(object):
    def test_to_representation_integer(self):
        self.assertEqual(123, self.oif.to_representation(123))

    def test_to_representation_zero(self):
        self.assertEqual(None, self.oif.to_representation(0))

    def test_to_internal_value_string(self):
        self.assertEqual(456, self.oif.to_internal_value('456'))

    def test_to_internal_value_integer(self):
        self.assertEqual(789, self.oif.to_internal_value(789))

    def test_to_internal_value_null(self):
        self.assertEqual(0, self.oif.to_internal_value(None))


class TestNonOptionalIntegerField(SharedOptionalIntegerFieldTests, TestCase):
    def setUp(self):
        self.oif = OptionalIntegerField(required=True)


class TestOptionalIntegerField(SharedOptionalIntegerFieldTests, TestCase):
    def setUp(self):
        self.oif = OptionalIntegerField()
