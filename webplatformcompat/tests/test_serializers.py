#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for `web-platform-compat.serializer."""

from json import dumps

from webplatformcompat.models import (
    Browser, Feature, Maturity, Section, Specification, Version)

from .base import APITestCase as BaseCase


class APITestCase(BaseCase):
    """Add integration test helpers to APITestCase."""
    longMessage = True  # Display inequalities and message parameter

    def get_via_json_api(self, url):
        """Get instance via API."""
        response = self.client.get(url, HTTP_ACCEPT='application/vnd.api+json')
        self.assertEqual(200, response.status_code, response.data)
        return response

    def update_via_json_api(self, url, data, expected_status=200):
        """Update instance via API using JSON-API formatted data."""
        json_data = dumps(data)
        content_type = 'application/vnd.api+json'
        response = self.client.put(
            url, data=json_data, content_type=content_type,
            HTTP_ACCEPT='application/vnd.api+json')
        self.assertEqual(expected_status, response.status_code, response.data)
        return response


class TestHistoricalModelSerializer(APITestCase):
    """Test common serializer functionality through BrowserSerializer."""

    def setUp(self):
        self.browser = self.create(
            Browser, slug='browser', name={'en': 'Old Name'})
        self.url = self.api_reverse('browser-detail', pk=self.browser.pk)

    def test_put_history_current(self):
        old_history_id = self.browser.history.latest('history_date').history_id
        self.browser.name = {'en': 'Browser'}
        self.browser.save()
        data = {
            'browsers': {
                'links': {
                    'history_current': str(old_history_id)
                }
            }
        }
        response = self.update_via_json_api(self.url, data)
        current_history_id = self.browser.history.all()[0].history_id
        self.assertNotEqual(old_history_id, current_history_id)
        histories = self.browser.history.all()
        self.assertEqual(3, len(histories))
        expected_data = {
            "id": self.browser.pk,
            "slug": "browser",
            "name": {"en": "Old Name"},
            "note": None,
            'history': [h.pk for h in histories],
            'history_current': current_history_id,
            'versions': [],
        }
        self.assertDataEqual(response.data, expected_data)

    def test_put_history_current_wrong_browser_fails(self):
        other_browser = self.create(
            Browser, slug='other-browser', name={'en': 'Other Browser'})
        bad_history_id = other_browser.history.all()[0].history_id
        data = {
            'browsers': {
                'slug': 'browser',
                'links': {
                    'history_current': str(bad_history_id)
                }
            }
        }
        response = self.update_via_json_api(self.url, data, 400)
        expected_data = {
            'history_current': ['Invalid history ID for this object']
        }
        self.assertDataEqual(response.data, expected_data)

    def test_put_history_same(self):
        self.browser.name = {'en': 'Browser'}
        self.browser.save()
        current_history_id = self.browser.history.all()[0].history_id
        data = {
            'browsers': {
                'links': {
                    'history_current': str(current_history_id)
                }
            }
        }
        response = self.update_via_json_api(self.url, data)
        new_history_id = self.browser.history.all()[0].history_id
        self.assertNotEqual(new_history_id, current_history_id)
        histories = self.browser.history.all()
        self.assertEqual(3, len(histories))
        expected_data = {
            "id": self.browser.pk,
            "slug": "browser",
            "name": {"en": "Browser"},
            "note": None,
            'history': [h.pk for h in histories],
            'history_current': new_history_id,
            'versions': [],
        }
        self.assertDataEqual(response.data, expected_data)


class TestBrowserSerializer(APITestCase):
    """Test BrowserSerializer through the view."""
    def setUp(self):
        self.browser = self.create(
            Browser, slug='browser', name={'en': 'Browser'})
        self.v1 = self.create(Version, browser=self.browser, version='1.0')
        self.v2 = self.create(Version, browser=self.browser, version='2.0')
        self.url = self.api_reverse('browser-detail', pk=self.browser.pk)

    def test_versions_change_order(self):
        data = {
            'browsers': {
                'links': {
                    'versions': [str(self.v2.pk), str(self.v1.pk)]
                }
            }
        }
        response = self.update_via_json_api(self.url, data)
        expected_versions = [v.pk for v in (self.v2, self.v1)]
        actual_versions = response.data['versions']
        self.assertEqual(expected_versions, actual_versions)

    def test_versions_same_order(self):
        data = {
            'browsers': {
                'links': {
                    'versions': [str(self.v1.pk), str(self.v2.pk)]
                }
            }
        }
        response = self.update_via_json_api(self.url, data)
        expected_versions = [v.pk for v in (self.v1, self.v2)]
        actual_versions = response.data['versions']
        self.assertEqual(expected_versions, actual_versions)


class TestFeatureSerializer(APITestCase):
    """Test FeatureSerializer through the view."""

    def setUp(self):
        self.parent = self.create(Feature, slug='parent')
        self.feature = self.create(Feature, slug='feature', parent=self.parent)
        self.child1 = self.create(Feature, slug='child1', parent=self.feature)
        self.child2 = self.create(Feature, slug='child2', parent=self.feature)
        self.url = self.api_reverse('feature-detail', pk=self.feature.pk)

    def test_original_order(self):
        response = self.get_via_json_api(self.url)
        expected_children = [v.pk for v in (self.child1, self.child2)]
        actual_children = response.data['children']
        self.assertEqual(expected_children, actual_children)

    def test_children_change_order(self):
        data = {
            'features': {
                'links': {
                    'children': [str(self.child2.pk), str(self.child1.pk)]
                }
            }
        }
        response = self.update_via_json_api(self.url, data)
        expected_children = [v.pk for v in (self.child2, self.child1)]
        actual_children = response.data['children']
        self.assertEqual(expected_children, actual_children)

    def test_children_same_order(self):
        data = {
            'features': {
                'links': {
                    'children': [str(self.child1.pk), str(self.child2.pk)]
                }
            }
        }
        response = self.update_via_json_api(self.url, data)
        expected_children = [v.pk for v in (self.child1, self.child2)]
        actual_children = response.data['children']
        self.assertEqual(expected_children, actual_children)

    def test_children_remove_element_fails(self):
        data = {
            'features': {
                'links': {
                    'children': [str(self.child1.pk)]
                }
            }
        }
        response = self.update_via_json_api(
            self.url, data, expected_status=400)
        expected_error = ['All child features must be included in children.']
        actual_error = response.data['children']
        self.assertEqual(expected_error, actual_error)

    def test_children_add_element_fails(self):
        new_child = self.create(Feature, slug='nkotb')
        data = {
            'features': {
                'links': {
                    'children': [
                        str(self.child1.pk),
                        str(self.child2.pk),
                        str(new_child.pk)]
                }
            }
        }
        response = self.update_via_json_api(
            self.url, data, expected_status=400)
        expected_error = ['Set child.parent to add a child feature.']
        actual_error = response.data['children']
        self.assertEqual(expected_error, actual_error)


class TestSpecificationSerializer(APITestCase):
    """Test SpecificationSerializer through the view."""

    def setUp(self):
        maturity = self.create(
            Maturity, slug='WD', name={'en': 'Working Draft'})
        self.spec = self.create(
            Specification, maturity=maturity, slug="css3-animations",
            mdn_key='CSS3 Animations',
            name={'en': "CSS Animations"},
            uri={'en': 'http://dev.w3.org/csswg/css-animations/'})
        self.s46 = self.create(
            Section, specification=self.spec,
            name={'en': "The 'animation-direction' property"},
            subpath={'en': "#animation-direction"})
        self.s45 = self.create(
            Section, specification=self.spec,
            name={'en': "The 'animation-iteration-count' property"},
            subpath={'en': "#animation-iteration-count"})
        self.url = self.api_reverse('specification-detail', pk=self.spec.pk)

    def test_update_without_sections(self):
        data = {
            'specifications': {
                'name': {'en': 'CSS3 Animations'}
            }
        }
        self.update_via_json_api(self.url, data)
        spec = Specification.objects.get(id=self.spec.id)
        self.assertEqual({'en': 'CSS3 Animations'}, spec.name)

    def test_sections_change_order(self):
        data = {
            'specifications': {
                'links': {
                    'sections': [str(self.s45.pk), str(self.s46.pk)]
                }
            }
        }
        response = self.update_via_json_api(self.url, data)
        expected_sections = [self.s45.pk, self.s46.pk]
        actual_sections = response.data['sections']
        self.assertEqual(expected_sections, actual_sections)

    def test_sections_same_order(self):
        data = {
            'specifications': {
                'links': {
                    'sections': [str(self.s46.pk), str(self.s45.pk)]
                }
            }
        }
        response = self.update_via_json_api(self.url, data)
        expected_sections = [self.s46.pk, self.s45.pk]
        actual_sections = response.data['sections']
        self.assertEqual(expected_sections, actual_sections)

    def test_set_and_revert_maturity(self):
        old_maturity_id = self.spec.maturity.id
        old_history_id = self.spec.history.all()[0].history_id
        new_maturity = self.create(
            Maturity, slug='FD', name={'en': 'Final Draft'})
        data_set_maturity = {
            'specifications': {
                'links': {
                    'maturity': str(new_maturity.id)
                }
            }
        }
        response = self.update_via_json_api(self.url, data_set_maturity)
        self.assertEqual(response.data['maturity'], new_maturity.id)

        data_revert = {
            'specifications': {
                'links': {
                    'history_current': old_history_id
                }
            }
        }
        response = self.update_via_json_api(self.url, data_revert)
        self.assertEqual(response.data['maturity'], old_maturity_id)


class TestUserSerializer(APITestCase):
    """Test UserSerializer through the view."""
    def test_get(self):
        self.login_user()
        url = self.api_reverse('user-detail', pk=self.user.pk)
        response = self.get_via_json_api(url)
        actual_data = response.data
        self.assertEqual(0, actual_data['agreement'])
        self.assertEqual(['change-resource'], actual_data['permissions'])


class TestHistoricalFeatureSerializer(APITestCase):
    """Test HistoricalFeatureSerializer, which has archive fields."""
    def test_get_history_no_parent(self):
        feature = self.create(
            Feature, slug="the_feature", name={"en": "The Feature"})
        history = feature.history.all()[0]
        url = self.api_reverse('historicalfeature-detail', pk=history.pk)
        response = self.get_via_json_api(url)
        actual_sections = response.data['features']['links']['sections']
        self.assertEqual([], actual_sections)
        actual_parent = response.data['features']['links']['parent']
        self.assertIsNone(actual_parent)

    def test_get_history_sections_parent(self):
        parent = self.create(
            Feature, slug="the_parent", name={"en": "The Parent"})
        feature = self.create(
            Feature, slug="the_feature", name={"en": "The Feature"},
            parent=parent)
        history = feature.history.all()[0]
        url = self.api_reverse('historicalfeature-detail', pk=history.pk)
        response = self.get_via_json_api(url)
        expected_parent = str(parent.pk)
        actual_parent = response.data['features']['links']['parent']
        self.assertEqual(expected_parent, actual_parent)
