#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for `web-platform-compat` fields module."""
from datetime import datetime
from pytz import UTC

from django.contrib.auth.models import User
from django.test.utils import override_settings

from webplatformcompat.cache import Cache
from webplatformcompat.history import Changeset
from webplatformcompat.models import (
    Browser, Feature, Maturity, Section, Specification, Support, Version)

from .base import TestCase


class TestCache(TestCase):
    def setUp(self):
        self.cache = Cache()
        self.login_user(groups=['change-resource'])

    def test_browser_v1_serializer(self):
        browser = self.create(Browser)
        out = self.cache.browser_v1_serializer(browser)
        expected = {
            'id': browser.id,
            'slug': u'',
            'name': {},
            'note': {},
            'history:PKList': {
                'app': u'webplatformcompat',
                'model': 'historicalbrowser',
                'pks': [browser.history.all()[0].pk],
            },
            'history_current:PK': {
                'app': u'webplatformcompat',
                'model': 'historicalbrowser',
                'pk': browser.history.all()[0].pk,
            },
            'versions:PKList': {
                'app': u'webplatformcompat',
                'model': 'version',
                'pks': [],
            },
        }
        self.assertEqual(out, expected)

    def test_browser_v1_serializer_empty(self):
        self.assertEqual(None, self.cache.browser_v1_serializer(None))

    def test_browser_v1_loader(self):
        browser = self.create(Browser)
        with self.assertNumQueries(3):
            obj = self.cache.browser_v1_loader(browser.pk)
        with self.assertNumQueries(0):
            serialized = self.cache.browser_v1_serializer(obj)
        self.assertTrue(serialized)

    def test_browser_v1_loader_not_exist(self):
        self.assertFalse(Browser.objects.filter(pk=666).exists())
        self.assertIsNone(self.cache.browser_v1_loader(666))

    def test_browser_v1_invalidator(self):
        browser = self.create(Browser)
        self.assertEqual([], self.cache.browser_v1_invalidator(browser))

    def test_changeset_v1_serializer(self):
        created = datetime(2014, 10, 29, 8, 57, 21, 806744, UTC)
        changeset = self.create(Changeset, user=self.user)
        Changeset.objects.filter(pk=changeset.pk).update(
            created=created, modified=created)
        changeset = Changeset.objects.get(pk=changeset.pk)
        out = self.cache.changeset_v1_serializer(changeset)
        expected = {
            'id': changeset.id,
            'created:DateTime': '1414573041.806744',
            'modified:DateTime': '1414573041.806744',
            'target_resource_type': '',
            'target_resource_id': 0,
            'closed': False,
            'user:PK': {
                'app': u'auth',
                'model': 'user',
                'pk': self.user.pk,
            },
            'historical_browsers:PKList': {
                'app': u'webplatformcompat',
                'model': 'historicalbrowser',
                'pks': []
            },
            'historical_features:PKList': {
                'app': u'webplatformcompat',
                'model': 'historicalfeature',
                'pks': []
            },
            'historical_maturities:PKList': {
                'app': u'webplatformcompat',
                'model': 'historicalmaturity',
                'pks': []
            },
            'historical_sections:PKList': {
                'app': u'webplatformcompat',
                'model': 'historicalsection',
                'pks': []
            },
            'historical_specifications:PKList': {
                'app': u'webplatformcompat',
                'model': 'historicalspecification',
                'pks': []
            },
            'historical_supports:PKList': {
                'app': u'webplatformcompat',
                'model': 'historicalsupport',
                'pks': []
            },
            'historical_versions:PKList': {
                'app': u'webplatformcompat',
                'model': 'historicalversion',
                'pks': []
            },
        }
        self.assertEqual(out, expected)

    def test_changeset_v1_serializer_empty(self):
        self.assertEqual(None, self.cache.changeset_v1_serializer(None))

    def test_changeset_v1_loader(self):
        changeset = self.create(Changeset, user=self.user)
        with self.assertNumQueries(8):
            obj = self.cache.changeset_v1_loader(changeset.pk)
        with self.assertNumQueries(0):
            serialized = self.cache.changeset_v1_serializer(obj)
        self.assertTrue(serialized)

    def test_changeset_v1_loader_not_exist(self):
        self.assertFalse(Changeset.objects.filter(pk=666).exists())
        self.assertIsNone(self.cache.changeset_v1_loader(666))

    def test_changeset_v1_invalidator(self):
        changeset = self.create(Changeset, user=self.user)
        self.assertEqual([], self.cache.changeset_v1_invalidator(changeset))

    def test_feature_v1_serializer(self):
        feature = self.create(
            Feature, slug='the-slug', name='{"en": "A Name"}')
        out = self.cache.feature_v1_serializer(feature)
        expected = {
            'id': feature.id,
            'slug': 'the-slug',
            'mdn_uri': {},
            'experimental': False,
            'standardized': True,
            'stable': True,
            'obsolete': False,
            'name': {"en": "A Name"},
            'descendant_count': 0,
            'supports:PKList': {
                'app': u'webplatformcompat',
                'model': 'support',
                'pks': [],
            },
            'sections:PKList': {
                'app': u'webplatformcompat',
                'model': 'section',
                'pks': [],
            },
            'parent:PK': {
                'app': u'webplatformcompat',
                'model': 'feature',
                'pk': None,
            },
            'children:PKList': {
                'app': u'webplatformcompat',
                'model': 'feature',
                'pks': [],
            },
            'descendants:PKList': {
                'app': u'webplatformcompat',
                'model': 'feature',
                'pks': [],
            },
            'history:PKList': {
                'app': u'webplatformcompat',
                'model': 'historicalfeature',
                'pks': [feature.history.all()[0].pk],
            },
            'history_current:PK': {
                'app': u'webplatformcompat',
                'model': 'historicalfeature',
                'pk': feature.history.all()[0].pk,
            },
        }
        self.assertEqual(out, expected)

    def test_feature_v1_serializer_some_descendants(self):
        feature = self.create(
            Feature, slug='the-slug', name='{"en": "A Name"}')
        child1 = self.create(Feature, slug='child1', parent=feature)
        child2 = self.create(Feature, slug='child2', parent=feature)
        child3 = self.create(Feature, slug='child3', parent=feature)
        feature = Feature.objects.get(id=feature.id)
        out = self.cache.feature_v1_serializer(feature)
        self.assertEqual(out['descendant_count'], 3)
        self.assertEqual(
            out['descendants:PKList'],
            {
                'app': u'webplatformcompat',
                'model': 'feature',
                'pks': [child1.pk, child2.pk, child3.pk]
            }
        )

    @override_settings(PAGINATE_VIEW_FEATURE=2)
    def test_feature_v1_serializer_paginated_descendants(self):
        feature = self.create(
            Feature, slug='the-slug', name='{"en": "A Name"}')
        self.create(Feature, slug='child1', parent=feature)
        self.create(Feature, slug='child2', parent=feature)
        self.create(Feature, slug='child3', parent=feature)
        feature = Feature.objects.get(id=feature.id)
        out = self.cache.feature_v1_serializer(feature)
        self.assertEqual(out['descendant_count'], 3)
        self.assertEqual(
            out['descendants:PKList'],
            {
                'app': u'webplatformcompat',
                'model': 'feature',
                'pks': []
            }
        )

    def test_feature_v1_serializer_empty(self):
        self.assertEqual(None, self.cache.feature_v1_serializer(None))

    def test_feature_v1_loader(self):
        feature = self.create(Feature)
        with self.assertNumQueries(5):
            obj = self.cache.feature_v1_loader(feature.pk)
        with self.assertNumQueries(0):
            serialized = self.cache.feature_v1_serializer(obj)
        self.assertTrue(serialized)

    def test_feature_v1_loader_not_exist(self):
        self.assertFalse(Feature.objects.filter(pk=666).exists())
        self.assertIsNone(self.cache.feature_v1_loader(666))

    def test_feature_v1_invalidator_basic(self):
        feature = self.create(Feature)
        self.assertEqual([], self.cache.feature_v1_invalidator(feature))

    def test_feature_v1_invalidator_with_relation(self):
        parent = self.create(Feature, slug='parent')
        feature = self.create(Feature, slug='child', parent=parent)
        expected = [('Feature', parent.id, False)]
        self.assertEqual(expected, self.cache.feature_v1_invalidator(feature))

    def test_maturity_v1_serializer(self):
        maturity = self.create(
            Maturity, slug='REC', name='{"en-US": "Recommendation"}')
        out = self.cache.maturity_v1_serializer(maturity)
        expected = {
            'id': maturity.id,
            'slug': 'REC',
            'name': {"en-US": "Recommendation"},
            'specifications:PKList': {
                'app': u'webplatformcompat',
                'model': 'specification',
                'pks': [],
            },
            'history:PKList': {
                'app': u'webplatformcompat',
                'model': 'historicalmaturity',
                'pks': [maturity.history.all()[0].pk],
            },
            'history_current:PK': {
                'app': u'webplatformcompat',
                'model': 'historicalmaturity',
                'pk': maturity.history.all()[0].pk,
            },
        }
        self.assertEqual(out, expected)

    def test_maturity_v1_serializer_empty(self):
        self.assertEqual(None, self.cache.maturity_v1_serializer(None))

    def test_maturity_v1_loader(self):
        maturity = self.create(Maturity)
        with self.assertNumQueries(3):
            obj = self.cache.maturity_v1_loader(maturity.pk)
        with self.assertNumQueries(0):
            serialized = self.cache.maturity_v1_serializer(obj)
        self.assertTrue(serialized)

    def test_maturity_v1_loader_not_exist(self):
        self.assertFalse(Maturity.objects.filter(pk=666).exists())
        self.assertIsNone(self.cache.maturity_v1_loader(666))

    def test_maturity_v1_invalidator(self):
        maturity = self.create(Maturity)
        self.assertEqual([], self.cache.maturity_v1_invalidator(maturity))

    def test_section_v1_serializer(self):
        maturity = self.create(
            Maturity, slug="REC", name={'en': 'Recommendation'})
        spec = self.create(
            Specification, slug='mathml2', mdn_key='MathML2',
            maturity=maturity,
            name='{"en": "MathML 2.0"}',
            uri='{"en": "http://www.w3.org/TR/MathML2/"}')
        section = self.create(
            Section, specification=spec,
            number={'en': '3.2.4'},
            name={'en': 'Number (mn)'},
            subpath={'en': 'chapter3.html#presm.mn'})
        out = self.cache.section_v1_serializer(section)
        expected = {
            'id': section.id,
            'number': {"en": '3.2.4'},
            'name': {"en": "Number (mn)"},
            'subpath': {'en': 'chapter3.html#presm.mn'},
            'note': {},
            'specification:PK': {
                'app': u'webplatformcompat',
                'model': 'specification',
                'pk': spec.pk,
            },
            'features:PKList': {
                'app': u'webplatformcompat',
                'model': 'feature',
                'pks': [],
            },
            'history:PKList': {
                'app': u'webplatformcompat',
                'model': 'historicalsection',
                'pks': [section.history.all()[0].pk],
            },
            'history_current:PK': {
                'app': u'webplatformcompat',
                'model': 'historicalsection',
                'pk': section.history.all()[0].pk,
            },
        }
        self.assertEqual(out, expected)

    def test_section_v1_serializer_empty(self):
        self.assertEqual(None, self.cache.section_v1_serializer(None))

    def test_section_v1_loader(self):
        maturity = self.create(
            Maturity, slug='WD', name={'en': 'Working Draft'})
        spec = self.create(
            Specification, slug='push_api', mdn_key='Push API',
            maturity=maturity,
            name={'en': 'Push API'},
            uri={'en': (
                'https://dvcs.w3.org/hg/push/raw-file/default/index.html')}
        )
        section = self.create(
            Section, specification=spec,
            name={'en': ''}, note={'en': 'Non standard'})
        with self.assertNumQueries(3):
            obj = self.cache.section_v1_loader(section.pk)
        with self.assertNumQueries(0):
            serialized = self.cache.section_v1_serializer(obj)
        self.assertTrue(serialized)

    def test_section_v1_loader_not_exist(self):
        self.assertFalse(Section.objects.filter(pk=666).exists())
        self.assertIsNone(self.cache.section_v1_loader(666))

    def test_section_v1_invalidator(self):
        maturity = self.create(
            Maturity, slug='WD', name={'en': 'Working Draft'})
        spec = self.create(
            Specification, slug='spec', mdn_key='Spec', maturity=maturity,
            name={'en': 'Spec'},
            uri={'en': 'http://example.com/spec.html'})
        section = self.create(
            Section, specification=spec,
            name={'en': 'A section'}, subpath={'en': '#section'})
        self.assertEqual(
            [('Specification', spec.pk, False)],
            self.cache.section_v1_invalidator(section))

    def test_specification_v1_serializer(self):
        maturity = self.create(
            Maturity, slug="REC", name={'en': 'Recommendation'})
        spec = self.create(
            Specification, slug="mathml2", mdn_key='MathML2',
            maturity=maturity,
            name='{"en": "MathML 2.0"}',
            uri='{"en": "http://www.w3.org/TR/MathML2/"}')
        history = spec.history.all()[0]
        out = self.cache.specification_v1_serializer(spec)
        expected = {
            'id': spec.id,
            'slug': 'mathml2',
            'mdn_key': 'MathML2',
            'name': {"en": "MathML 2.0"},
            'uri': {"en": "http://www.w3.org/TR/MathML2/"},
            'sections:PKList': {
                'app': u'webplatformcompat',
                'model': 'section',
                'pks': [],
            },
            'maturity:PK': {
                'app': u'webplatformcompat',
                'model': 'maturity',
                'pk': maturity.pk,
            },
            'history:PKList': {
                'app': u'webplatformcompat',
                'model': 'historicalspecification',
                'pks': [history.pk],
            },
            'history_current:PK': {
                'app': u'webplatformcompat',
                'model': 'historicalspecification',
                'pk': history.pk,
            },
        }
        self.assertEqual(out, expected)

    def test_specification_v1_serializer_empty(self):
        self.assertEqual(None, self.cache.specification_v1_serializer(None))

    def test_specification_v1_loader(self):
        maturity = self.create(
            Maturity, slug='WD', name={'en': 'Working Draft'})
        spec = self.create(
            Specification, slug='push-api', maturity=maturity,
            name={'en': 'Push API'},
            uri={'en': (
                'https://dvcs.w3.org/hg/push/raw-file/default/index.html')}
        )
        with self.assertNumQueries(3):
            obj = self.cache.specification_v1_loader(spec.pk)
        with self.assertNumQueries(0):
            serialized = self.cache.specification_v1_serializer(obj)
        self.assertTrue(serialized)

    def test_specification_v1_loader_not_exist(self):
        self.assertFalse(Specification.objects.filter(pk=666).exists())
        self.assertIsNone(self.cache.specification_v1_loader(666))

    def test_specification_v1_invalidator(self):
        maturity = self.create(
            Maturity, slug='WD', name={'en': 'Working Draft'})
        spec = self.create(
            Specification, slug='spec', maturity=maturity,
            name={'en': 'Spec'},
            uri={'en': 'http://example.com/spec.html'})
        self.assertEqual(
            [('Maturity', maturity.pk, False)],
            self.cache.specification_v1_invalidator(spec))

    def test_support_v1_serializer(self):
        browser = self.create(Browser)
        version = self.create(Version, browser=browser, version='1.0')
        feature = self.create(Feature, slug='feature')
        support = self.create(Support, version=version, feature=feature)
        out = self.cache.support_v1_serializer(support)
        expected = {
            'id': support.id,
            "support": u"yes",
            "prefix": u"",
            "prefix_mandatory": False,
            "alternate_name": u"",
            "alternate_mandatory": False,
            "requires_config": u"",
            "default_config": u"",
            "protected": False,
            "note": {},
            'version:PK': {
                'app': u'webplatformcompat',
                'model': 'version',
                'pk': version.id,
            },
            'feature:PK': {
                'app': u'webplatformcompat',
                'model': 'feature',
                'pk': feature.id,
            },
            'history:PKList': {
                'app': u'webplatformcompat',
                'model': 'historicalsupport',
                'pks': [support.history.all()[0].pk],
            },
            'history_current:PK': {
                'app': u'webplatformcompat',
                'model': 'historicalsupport',
                'pk': support.history.all()[0].pk,
            },
        }
        self.assertEqual(out, expected)

    def test_support_v1_serializer_empty(self):
        self.assertEqual(None, self.cache.support_v1_serializer(None))

    def test_support_v1_loader(self):
        browser = self.create(Browser)
        version = self.create(Version, browser=browser, version='1.0')
        feature = self.create(Feature, slug='feature')
        support = self.create(Support, version=version, feature=feature)
        with self.assertNumQueries(2):
            obj = self.cache.support_v1_loader(support.pk)
        with self.assertNumQueries(0):
            serialized = self.cache.support_v1_serializer(obj)
        self.assertTrue(serialized)

    def test_support_v1_loader_not_exist(self):
        self.assertFalse(Support.objects.filter(pk=666).exists())
        self.assertIsNone(self.cache.support_v1_loader(666))

    def test_support_v1_invalidator(self):
        browser = self.create(Browser)
        version = self.create(Version, browser=browser, version='1.0')
        feature = self.create(Feature, slug='feature')
        support = self.create(Support, version=version, feature=feature)
        expected = [
            ('Version', version.id, True),
            ('Feature', feature.id, True),
        ]
        self.assertEqual(expected, self.cache.support_v1_invalidator(support))

    def test_version_v1_serializer(self):
        browser = self.create(Browser)
        version = self.create(Version, browser=browser)
        out = self.cache.version_v1_serializer(version)
        expected = {
            'id': version.id,
            'version': u'',
            'release_day:Date': None,
            'retirement_day:Date': None,
            'status': u'unknown',
            'release_notes_uri': {},
            'note': {},
            '_order': 0,
            'browser:PK': {
                'app': u'webplatformcompat',
                'model': 'browser',
                'pk': browser.id,
            },
            'supports:PKList': {
                'app': u'webplatformcompat',
                'model': 'support',
                'pks': [],
            },
            'history:PKList': {
                'app': u'webplatformcompat',
                'model': 'historicalversion',
                'pks': [version.history.all()[0].pk],
            },
            'history_current:PK': {
                'app': u'webplatformcompat',
                'model': 'historicalversion',
                'pk': version.history.all()[0].pk,
            },
        }
        self.assertEqual(out, expected)

    def test_version_v1_serializer_empty(self):
        self.assertEqual(None, self.cache.version_v1_serializer(None))

    def test_version_v1_loader(self):
        browser = self.create(Browser)
        version = self.create(Version, browser=browser)
        with self.assertNumQueries(3):
            obj = self.cache.version_v1_loader(version.pk)
        with self.assertNumQueries(0):
            serialized = self.cache.version_v1_serializer(obj)
        self.assertTrue(serialized)

    def test_version_v1_loader_not_exist(self):
        self.assertFalse(Version.objects.filter(pk=666).exists())
        self.assertIsNone(self.cache.version_v1_loader(666))

    def test_version_v1_invalidator(self):
        browser = self.create(Browser)
        version = self.create(Version, browser=browser)
        expected = [('Browser', browser.id, True)]
        self.assertEqual(expected, self.cache.version_v1_invalidator(version))

    def test_user_v1_serializer(self):
        user = self.create(
            User, date_joined=datetime(2014, 9, 22, 8, 14, 34, 7, UTC))
        out = self.cache.user_v1_serializer(user)
        expected = {
            'id': user.id,
            'username': '',
            'date_joined:DateTime': '1411373674.000007',
            'changesets:PKList': {
                'app': 'webplatformcompat',
                'model': 'changeset',
                'pks': []
            },
            'group_names': ['change-resource'],
        }
        self.assertEqual(out, expected)

    def test_user_v1_serializer_empty(self):
        self.assertEqual(None, self.cache.user_v1_serializer(None))

    def test_user_v1_inactive(self):
        user = self.create(
            User, date_joined=datetime(2014, 9, 22, 8, 14, 34, 7, UTC),
            is_active=False)
        out = self.cache.user_v1_serializer(user)
        self.assertEqual(out, None)

    def test_user_v1_loader(self):
        user = self.create(User)
        with self.assertNumQueries(3):
            obj = self.cache.user_v1_loader(user.pk)
        with self.assertNumQueries(0):
            serialized = self.cache.user_v1_serializer(obj)
        self.assertTrue(serialized)

    def test_user_v1_loader_not_exist(self):
        self.assertFalse(User.objects.filter(pk=666).exists())
        self.assertIsNone(self.cache.user_v1_loader(666))

    def test_user_v1_invalidator(self):
        user = self.create(User)
        self.assertEqual([], self.cache.user_v1_invalidator(user))
