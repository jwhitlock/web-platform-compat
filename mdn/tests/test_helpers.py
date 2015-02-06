# -*- coding: utf-8 -*-
"""Tests for jingo/jinja2 helper functions and filters."""

from __future__ import unicode_literals

from django.core.paginator import Paginator

from mdn.helpers import page_list, pagination_control
from webplatformcompat.tests.base import TestCase as BaseTestCase


class TestCase(BaseTestCase):
    def page(self, number, total):
        paginator = Paginator(range(total * 2), 2)
        return paginator.page(number)


class TestPageList(TestCase):
    def test_empty(self):
        page = self.page(1, 0)
        self.assertEqual([1], page_list(page))

    def test_two_pages(self):
        page = self.page(1, 2)
        self.assertEqual([1, 2], page_list(page))

    def test_five_pages(self):
        page = self.page(3, 5)
        self.assertEqual([1, 2, 3, 4, 5], page_list(page))

    def test_seven_pages(self):
        page = self.page(2, 7)
        self.assertEqual([1, 2, 3, 4, 5, 6, 7], page_list(page))

    def test_1_of_8_pages(self):
        page = self.page(1, 8)
        self.assertEqual([1, 2, 3, 4, 5, None, 8], page_list(page))

    def test_2_of_8_pages(self):
        page = self.page(2, 8)
        self.assertEqual([1, 2, 3, 4, 5, None, 8], page_list(page))

    def test_3_of_8_pages(self):
        page = self.page(3, 8)
        self.assertEqual([1, 2, 3, 4, 5, None, 8], page_list(page))

    def test_4_of_8_pages(self):
        page = self.page(4, 8)
        self.assertEqual([1, 2, 3, 4, 5, None, 8], page_list(page))

    def test_5_of_8_pages(self):
        page = self.page(5, 8)
        self.assertEqual([1, None, 4, 5, 6, 7, 8], page_list(page))

    def test_6_of_8_pages(self):
        page = self.page(6, 8)
        self.assertEqual([1, None, 4, 5, 6, 7, 8], page_list(page))

    def test_7_of_8_pages(self):
        page = self.page(7, 8)
        self.assertEqual([1, None, 4, 5, 6, 7, 8], page_list(page))

    def test_8_of_8_pages(self):
        page = self.page(8, 8)
        self.assertEqual([1, None, 4, 5, 6, 7, 8], page_list(page))

    def test_5_of_9_pages(self):
        page = self.page(5, 9)
        self.assertEqual([1, None, 4, 5, 6, None, 9], page_list(page))


class TestPagnationControl(TestCase):
    def test_one_page(self):
        page = self.page(1, 1)
        out = pagination_control(None, page, '/test')
        self.assertEqual("", out)

    def test_first_page(self):
        page = self.page(1, 3)
        out = pagination_control(None, page, '/test')
        expected_prev = (
            '<li class="disabled"><span aria-hidden="true">&laquo;</span>'
            '</li>')
        expected_next = (
            '<li><a href="/test?page=2" aria-label="Next">'
            '<span aria-hidden="true">&raquo;</span></a></li>')
        self.assertInHTML(expected_prev, out)
        self.assertInHTML(expected_next, out)

    def test_middle_page(self):
        page = self.page(2, 3)
        out = pagination_control(None, page, '/test')
        expected_prev = (
            '<li><a href="/test" aria-label="Previous">'
            '<span aria-hidden="true">&laquo;</span></a></li>')
        expected_next = (
            '<li><a href="/test?page=3" aria-label="Next">'
            '<span aria-hidden="true">&raquo;</span></a></li>')
        self.assertInHTML(expected_prev, out)
        self.assertInHTML(expected_next, out)

    def test_last_page(self):
        page = self.page(3, 3)
        out = pagination_control(None, page, '/test')
        expected_prev = (
            '<li><a href="/test?page=2" aria-label="Previous">'
            '<span aria-hidden="true">&laquo;</span></a></li>')
        expected_next = (
            '<li class="disabled"><span aria-hidden="true">&raquo;</span>'
            '</li>')
        self.assertInHTML(expected_prev, out)
        self.assertInHTML(expected_next, out)

    def test_deep_middle_page(self):
        page = self.page(5, 9)
        out = pagination_control(None, page, '/test')
        expected_spacer = (
            '<li class="disabled"><span aria-hidden="true">&hellip;</span>'
            '</li>')
        self.assertInHTML(expected_spacer, out)
