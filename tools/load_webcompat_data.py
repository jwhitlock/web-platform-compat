#!/usr/bin/env python

from __future__ import print_function

from cgi import escape
from collections import defaultdict
import codecs
import getpass
import json
import logging
import os.path
import re
import string
import sys

import requests

from client import Client
from resources import (
    Collection, CollectionChangeset, Browser, Version, Feature, Support)

try:
    input = raw_input  # Get the Py2 raw_input
except NameError:
    pass  # We're in Py3


logger = logging.getLogger('tools.load_webcompat_data')
my_dir = os.path.dirname(os.path.realpath(__file__))
data_dir = os.path.realpath(os.path.join(my_dir, '..', 'data'))
COMPAT_DATA_FILENAME = os.path.join(data_dir, "data-human.json")
COMPAT_DATA_URL = (
    "https://raw.githubusercontent.com/webplatform/compatibility-data"
    "/master/data-human.json")
known_browsers = [
    "Chrome",
    "Firefox",
    "Internet Explorer",
    "Opera",
    "Safari",
    "Android",
    "Chrome for Android",
    "Chrome Mobile",
    "Firefox Mobile",
    "IE Mobile",
    "Opera Mini",
    "Opera Mobile",
    "Safari Mobile",
    "BlackBerry",
    "Firefox OS",
]
version_re = re.compile("^[.\d]+$")


def get_compat_data(filename, url):
    if not os.path.exists(filename):
        logger.info("Downloading " + filename)
        r = requests.get(url)
        with codecs.open(filename, 'wb', 'utf8') as f:
            f.write(r.text)
    else:
        logger.info("Using existing " + filename)

    with codecs.open(filename, 'r', 'utf8') as f:
        compat_data = json.load(f)
    return compat_data


def load_compat_data(client, compat_data, all_data=False, confirm=None):
    """Load a dictionary of compatiblity data into the API"""
    api_collection = Collection(client)
    local_collection = Collection()

    logger.info('Reading existing feature data from API')
    load_api_feature_data(api_collection)
    logger.info('Loading feature data from webplatform repository')
    parse_compat_data(compat_data, local_collection)

    if not all_data:
        logger.info('Selecting subset of data')
        select_subset(local_collection)

    logger.info('Looking for changes...')
    changeset = CollectionChangeset(api_collection, local_collection)
    delta = changeset.changes

    if delta['new'] or delta['changed'] or delta['deleted']:
        logger.info(
            'Changes detected: %d new, %d changed, %d deleted, %d same.',
            len(delta['new']), len(delta['changed']), len(delta['deleted']),
            len(delta['same']))
        if confirm:
            confirmed = confirm(client, changeset)
        else:
            confirmed = True
        if not confirmed:
            return {}
    else:
        logger.info('No changes')
        return {}

    counts = changeset.change_original_collection()
    return counts


def load_api_feature_data(api_collection):
    api_collection.load_all('browsers')
    api_collection.load_all('versions')
    api_collection.load_all('features')
    api_collection.load_all('supports')


def parse_compat_data(compat_data, local_collection):
    local_collection.feature_slugs = set()
    for key, value in compat_data['data'].items():
        parse_compat_data_item(key, value, local_collection)

    # Populate the sorted versions
    browser_versions = defaultdict(list)
    for version in local_collection.get_resources_by_data_id(
            'versions').values():
        browser_versions[version.browser.id].append(version)
    for browser_id, versions in browser_versions.items():
        browser = local_collection.get('browsers', browser_id)
        browser.versions = sorted([v.id.id for v in versions])


def slugify(word, attempt=0):
    raw = word.lower().encode('utf-8')
    out = []
    acceptable = string.ascii_lowercase + string.digits + '_-'
    for c in raw:
        if c in acceptable:
            out += str(c)
        else:
            out += '_'
    slugged = ''.join(out)
    while '__' in slugged:
        slugged = slugged.replace('__', '_')
    if attempt:
        suffix = str(attempt)
    else:
        suffix = ""
    with_suffix = slugged[slice(50 - len(suffix))] + suffix
    return with_suffix.decode('utf-8')


def unique_slugify(word, existing):
    slug = slugify(word)
    attempt = 0
    while slug in existing:
        attempt += 1
        slug = slugify(word, attempt)
    existing.add(slug)
    return slug


def parse_compat_data_item(key, item, local_collection):
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
    version_ignore = [
        'notes',
    ]
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
            if not local_collection.get('features', feature_id):
                slug = unique_slugify(
                    '-'.join(feature_id), local_collection.feature_slugs)
                local_collection.add(Feature(
                    id=feature_id, slug=slug, name={u'en': bit},
                    experimental=False, obsolete=False, stable=True,
                    standardized=True, mdn_uri=None,
                    parent=last_feature_id or None))
        parent_feature_id = feature_id
        parent_feature = local_collection.get('features', parent_feature_id)
        parent_feature.mdn_uri = {u'en': url}

        for env, rows in item['contents'].items():
            assert env in ('desktop', 'mobile')
            for feature, columns in rows.items():
                # Add feature
                feature_id = parent_feature_id + (feature,)
                if not local_collection.get('features', feature_id):
                    slug = unique_slugify(
                        '-'.join(feature_id), local_collection.feature_slugs)
                    local_collection.add(Feature(
                        id=feature_id, slug=slug,
                        mdn_uri={u'en': url}, name={u'en': escape(feature)},
                        experimental=False, obsolete=False, stable=True,
                        standardized=True, parent=parent_feature_id))

                # Add browser
                for raw_browser, versions in columns.items():
                    browser = browser_conversions.get(raw_browser, raw_browser)
                    assert browser in known_browsers, raw_browser
                    browser_id = known_browsers.index(browser)
                    if not local_collection.get('browsers', browser_id):
                        local_collection.add(Browser(
                            id=browser_id, slug=slugify(browser),
                            name={u'en': browser}, note=None))

                    version_note = versions.get('notes', {})
                    for raw_version, raw_support in versions.items():
                        # Add version
                        if raw_version in version_ignore:
                            continue
                        version, version_id = convert_version(
                            browser_id, raw_version)
                        if not local_collection.get('versions', version_id):
                            local_collection.add(Version(
                                id=version_id, version=version,
                                browser=browser_id, note=None,
                                release_day=None, release_notes_uri=None,
                                retirement_day=None, status=u'unknown'))

                        # Add support
                        support_id = (version_id, feature_id)
                        if not local_collection.get('supports', support_id):
                            notes = []
                            obj = Support(
                                id=support_id, feature=feature_id,
                                version=version_id, alternate_name=None,
                                alternate_mandatory=False,
                                default_config=None, footnote=None,
                                note=None, prefix=None, prefix_mandatory=False,
                                protected=False, requires_config=None)
                            obj.support = support_map[raw_support[0]]
                            if obj.support == 'prefix':
                                obj.support = 'yes'
                                obj.prefix = support_prefix[browser]

                            if len(raw_support) > 1:
                                notes.append(
                                    'Original support string is "%s"'
                                    % escape(raw_support))
                            for item in version_note.items():
                                notes.append('%s: %s' % item)

                            if notes:
                                joined = '<br>'.join(escape(n) for n in notes)
                                obj.note = {'en': joined}
                            if obj.prefix:
                                obj.prefix_mandatory = True
                            local_collection.add(obj)
    else:
        for subkey, subitem in item.items():
            parse_compat_data_item(subkey, subitem, local_collection)


def convert_version(browser_id, raw_version):
    if raw_version == '?':
        version = None
    else:
        version = raw_version
    if not version:
        version = None
        version_id = (browser_id,)
    else:
        assert version_re.match(version), raw_version
        bits = tuple(int(x) for x in version.split('.'))
        if len(bits) == 1:
            # Prefer 12.0 format to 12 format
            version += '.0'
            bits += (0,)
        version_id = (browser_id,) + bits
    return version, version_id


def select_subset(local_collection):
    """Discard all but a subset of features and supports"""
    # Select features to keep
    keep_feature_ids = set()
    for feature in local_collection.get_resources('features'):
        if feature.mdn_uri and 'Web/CSS/c' in feature.mdn_uri['en']:
            keep_feature_ids.add(feature.id.id)
            parent = feature.parent.get()
            while parent:
                keep_feature_ids.add(parent.id.id)
                parent = parent.parent.get()

    # Discard unrelated supports
    for support in local_collection.get_resources('supports')[:]:
        if support.feature.id not in keep_feature_ids:
            local_collection.remove(support)

    # Discard unrelated features
    for feature in local_collection.get_resources('features')[:]:
        if feature.id.id not in keep_feature_ids:
            local_collection.remove(feature)


def confirm_changes(client, changeset):
    while True:
        choice = input("Make these changes? (Y/N/D for details) ")
        if choice.upper() == 'Y':
            return True
        elif choice.upper() == 'N':
            return False
        elif choice.upper() == 'D':
            print(changeset.summarize())
        else:
            print("Please type Y or N or D.")


if __name__ == '__main__':
    import argparse
    description = 'Initialize with compatibility data from webcompat project.'
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        '-a', '--api',
        help='Base URL of the API (default: http://localhost:8000)',
        default="http://localhost:8000")
    parser.add_argument(
        '-u', '--user',
        help='Username on API (default: prompt for username)')
    parser.add_argument(
        '-v', '--verbose', action="store_true",
        help='Print extra debug information')
    parser.add_argument(
        '-q', '--quiet', action="store_true",
        help='Only print warnings')
    parser.add_argument(
        '--all-data', action="store_true",
        help='Import all the data, rather than a subset')
    args = parser.parse_args()

    # Setup logging
    verbose = args.verbose
    quiet = args.quiet
    console = logging.StreamHandler(sys.stderr)
    formatter = logging.Formatter('%(levelname)s - %(message)s')
    logger_name = 'tools'
    fmat = '%(levelname)s - %(message)s'
    if quiet:
        level = logging.WARNING
    elif verbose:
        level = logging.DEBUG
        logger_name = ''
        fmat = '%(name)s - %(levelname)s - %(message)s'
    else:
        level = logging.INFO
    formatter = logging.Formatter(fmat)
    console.setLevel(level)
    console.setFormatter(formatter)
    logger = logging.getLogger(logger_name)
    logger.setLevel(level)
    logger.addHandler(console)

    # Parse arguments
    api = args.api
    if api.endswith('/'):
        api = api[:-1]
    all_data = args.all_data
    logger.info(
        "Loading %s data into %s",
        'all' if all_data else 'subset of', api)

    # Get credentials
    user = args.user or input("API username: ")
    password = getpass.getpass("API password: ")

    # Initialize client
    client = Client(api)
    client.login(user, password)

    # Load data
    compat_data = get_compat_data(COMPAT_DATA_FILENAME, COMPAT_DATA_URL)
    counts = load_compat_data(
        client, compat_data, all_data=all_data, confirm=confirm_changes)

    if counts:
        logger.info("Changes complete. Counts:")
        for resource_type, changes in counts.items():
            c_new = changes.get('new', 0)
            c_deleted = changes.get('deleted', 0)
            c_changed = changes.get('changed', 0)
            c_text = []
            if c_new:
                c_text.append("%d new" % c_new)
            if c_deleted:
                c_text.append("%d deleted" % c_deleted)
            if c_changed:
                c_text.append("%d changed" % c_changed)
            if c_text:
                logger.info("  %s: %s" % (
                    resource_type.title(), ', '.join(c_text)))
    else:
        logger.info("No data uploaded.")
