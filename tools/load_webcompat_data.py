#!/usr/bin/env python
from cgi import escape
from collections import defaultdict
from json import loads
import re

from common import Tool
from resources import Collection, Browser, Version, Feature, Support


class LoadWebcompatData(Tool):
    """Initialize with data from the webcompat project."""
    logger_name = 'tools.load_webcompat_data'
    parser_options = ['api', 'user', 'password']

    def run(self, *args, **kwargs):
        self.login()

        api_collection = Collection(self.client)
        local_collection = Collection()
        compat_data = loads(self.cached_download(
            "data-human.json",
            "https://raw.githubusercontent.com/webplatform/compatibility-data"
            "/master/data-human.json"))

        self.logger.info('Reading existing feature data from API')
        for resource in ['browsers', 'versions', 'features', 'supports']:
            api_collection.load_all(resource)
        self.logger.info('Loading feature data from webplatform repository')
        self.parse_compat_data(compat_data, local_collection)

        if not self.all_data:
            self.logger.info('Selecting subset of data')
            self.select_subset(local_collection)

        return self.sync_changes(api_collection, local_collection)

    def get_parser(self):
        parser = super(LoadWebcompatData, self).get_parser()
        parser.add_argument(
            '--all-data', action="store_true",
            help='Import all the data, rather than a subset')
        return parser

    def parse_compat_data(self, compat_data, local_collection):
        local_collection.feature_slugs = set()
        for key, value in compat_data['data'].items():
            self.parse_compat_data_item(key, value, local_collection)

        # Populate the sorted versions
        browser_versions = defaultdict(list)
        for version in local_collection.get_resources_by_data_id(
                'versions').values():
            browser_versions[version.browser.id].append(version)
        for browser_id, versions in browser_versions.items():
            browser = local_collection.get('browsers', browser_id)
            browser.versions = sorted([v.id.id for v in versions])

    known_browsers = [
        "Chrome", "Firefox", "Internet Explorer", "Opera", "Safari", "Android",
        "Chrome for Android", "Chrome Mobile", "Firefox Mobile", "IE Mobile",
        "Opera Mini", "Opera Mobile", "Safari Mobile", "BlackBerry",
        "Firefox OS"]
    browser_conversions = {
        "IE Phone": "IE Mobile",
        "Chrome for Andriod": "Chrome for Android",
        "Android Browser": "Android",
        "Chrome**": "Chrome",
        "Opera*": "Opera",
        "BlackBerry Browser": "BlackBerry",
        "Internet Explorer*": "Internet Explorer",
        "IE": "Internet Explorer",
        "Firefox mobile": "Firefox Mobile",
        "Windows Phone": "IE Mobile",
        "iOS Safari": "Safari Mobile",
    }
    version_ignore = ['notes']
    support_map = {
        'y': u'yes',
        'u': u'unknown',
        'x': u'prefix',
        'n': u'no',
        'a': u'unknown',
    }
    support_prefix = {
        'Chrome': u'-webkit',
        'Safari': u'-webkit',
        'Android': u'-webkit',
        'Chrome Mobile': u'-webkit',
        'Chrome for Android': u'-webkit',
        'BlackBerry': u'-webkit',
        'Firefox': u'-moz',
        'Firefox OS': u'-moz',
        'Safari Mobile': u'-moz',
        'Firefox Mobile': u'-moz',
        'Opera': u'-o',
        'Opera Mobile': u'-o',
        'Internet Explorer': u'-ms',
    }

    def parse_compat_data_item(self, key, item, collection):
        if "breadcrumb" in item:
            assert "contents" in item
            assert "jsonselect" in item
            assert "links" in item

            # Feature heirarchy
            url = item['links'][0]["url"]
            assert url.startswith('https://developer.mozilla.org/en-US/docs/')
            mdn_subpath = url.split('en-US/docs/', 1)[1]
            path_bits = mdn_subpath.split('/')
            feature_id = ()
            for bit in path_bits:
                last_feature_id = feature_id
                feature_id += (bit,)
                if not collection.get('features', feature_id):
                    slug = self.unique_slugify(
                        '-'.join(feature_id), collection.feature_slugs)
                    collection.add(Feature(
                        id=feature_id, slug=slug, name={u'en': bit},
                        experimental=False, obsolete=False, stable=True,
                        standardized=True, mdn_uri=None,
                        parent=last_feature_id or None))
            parent_feature_id = feature_id
            parent_feature = collection.get(
                'features', parent_feature_id)
            parent_feature.mdn_uri = {u'en': url}

            for env, rows in item['contents'].items():
                assert env in ('desktop', 'mobile')
                for feature, columns in rows.items():
                    # Add feature
                    feature_id = parent_feature_id + (feature,)
                    if not collection.get('features', feature_id):
                        slug = self.unique_slugify(
                            '-'.join(feature_id),
                            collection.feature_slugs)
                        collection.add(Feature(
                            id=feature_id, slug=slug,
                            mdn_uri={u'en': url},
                            name={u'en': escape(feature)},
                            experimental=False, obsolete=False, stable=True,
                            standardized=True, parent=parent_feature_id))

                    # Add browser
                    for raw_browser, versions in columns.items():
                        browser = self.browser_conversions.get(
                            raw_browser, raw_browser)
                        assert browser in self.known_browsers, raw_browser
                        browser_id = self.known_browsers.index(browser)
                        if not collection.get('browsers', browser_id):
                            collection.add(Browser(
                                id=browser_id, slug=self.slugify(browser),
                                name={u'en': browser}, note=None))

                        version_note = versions.get('notes', {})
                        for raw_version, raw_support in versions.items():
                            # Add version
                            if raw_version in self.version_ignore:
                                continue
                            version, version_id = self.convert_version(
                                browser_id, raw_version)
                            if not collection.get('versions', version_id):
                                collection.add(Version(
                                    id=version_id, version=version,
                                    browser=browser_id, note=None,
                                    release_day=None, release_notes_uri=None,
                                    retirement_day=None, status=u'unknown'))

                            # Add support
                            support_id = (version_id, feature_id)
                            if not collection.get('supports', support_id):
                                notes = []
                                obj = Support(
                                    id=support_id, feature=feature_id,
                                    version=version_id, alternate_name=None,
                                    alternate_mandatory=False,
                                    default_config=None, note=None,
                                    prefix=None, prefix_mandatory=False,
                                    protected=False, requires_config=None)
                                obj.support = self.support_map[raw_support[0]]
                                if obj.support == 'prefix':
                                    obj.support = 'yes'
                                    obj.prefix = self.support_prefix[browser]

                                if len(raw_support) > 1:
                                    notes.append(
                                        'Original support string is "%s"'
                                        % escape(raw_support))
                                for item in version_note.items():
                                    notes.append('%s: %s' % item)

                                if notes:
                                    joined = '<br>'.join(
                                        escape(n) for n in notes)
                                    obj.note = {'en': joined}
                                if obj.prefix:
                                    obj.prefix_mandatory = True
                                collection.add(obj)
        else:
            for subkey, subitem in item.items():
                self.parse_compat_data_item(subkey, subitem, collection)

    version_re = re.compile("^[.\d]+$")

    def convert_version(self, browser_id, raw_version):
        if raw_version == '?':
            version = None
        else:
            version = raw_version
        if not version:
            version = None
            version_id = (browser_id,)
        else:
            assert self.version_re.match(version), raw_version
            bits = tuple(int(x) for x in version.split('.'))
            if len(bits) == 1:
                # Prefer 12.0 format to 12 format
                version += '.0'
                bits += (0,)
            version_id = (browser_id,) + bits
        return version, version_id

    def select_subset(self, collection):
        """Discard all but a subset of features and supports"""
        # Select features to keep
        keep_feature_ids = set()
        for feature in collection.get_resources('features'):
            if feature.mdn_uri and 'Web/CSS/c' in feature.mdn_uri['en']:
                keep_feature_ids.add(feature.id.id)
                parent = feature.parent.get()
                while parent:
                    keep_feature_ids.add(parent.id.id)
                    parent = parent.parent.get()

        # Discard unrelated supports
        for support in collection.get_resources('supports')[:]:
            if support.feature.id not in keep_feature_ids:
                collection.remove(support)

        # Discard unrelated features
        for feature in collection.get_resources('features')[:]:
            if feature.id.id not in keep_feature_ids:
                collection.remove(feature)


if __name__ == '__main__':
    tool = LoadWebcompatData()
    tool.init_from_command_line()
    how_much = 'all' if tool.all_data else 'subset of'
    tool.logger.info("Loading {} data into {}".format(how_much, tool.api))
    changes = tool.run()
    tool.report_changes(changes)
