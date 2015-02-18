#!/usr/bin/env python

from __future__ import print_function

import codecs
import getpass
import logging
import os.path
import re
import string
import sys

import requests

from client import Client
from resources import Collection, CollectionChangeset, Maturity, Specification

try:
    input = raw_input  # Get the Py2 raw_input
except NameError:
    pass  # We're in Py3

logger = logging.getLogger('tools.load_spec_data')
my_dir = os.path.dirname(os.path.realpath(__file__))
data_dir = os.path.realpath(os.path.join(my_dir, '..', 'data'))
SPEC2_FILENAME = os.path.join(data_dir, 'Spec2.txt')
SPEC2_URL = 'https://developer.mozilla.org/en-US/docs/Template:Spec2?raw'
SPECNAME_FILENAME = os.path.join(data_dir, 'SpecName.txt')
SPECNAME_URL = 'https://developer.mozilla.org/en-US/docs/Template:SpecName?raw'


def get_template(filename, url):
    if not os.path.exists(filename):
        logger.info("Downloading " + filename)
        r = requests.get(url)
        with codecs.open(filename, 'wb', 'utf8') as f:
            f.write(r.text)
    else:
        logger.info("Using existing " + filename)

    with codecs.open(filename, 'r', 'utf8') as f:
        template = f.read()
    return template


def load_spec_data(client, specname, spec2, confirm=None):
    """Load a dictionary of specification data into the API"""
    api_collection = Collection(client)
    local_collection = Collection()

    logger.info('Reading existing spec data from API')
    load_api_spec_data(api_collection)
    logger.info('Reading spec data from MDN templates')
    parse_spec_data(specname, spec2, api_collection, local_collection)

    # Load API sections into local collection
    local_collection.override_ids_to_match(api_collection)
    local_specs = local_collection.get_resources('specifications')
    for local_spec in local_specs:
        api_spec = api_collection.get('specifications', local_spec.id.id)
        if api_spec:
            local_spec.sections = api_spec.sections.ids

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


def load_api_spec_data(api_collection):
    api_collection.load_all('maturities')
    api_collection.load_all('specifications')


def parse_spec_data(specname, spec2, api_collection, local_collection):
    parse_specname(specname, api_collection, local_collection)
    parse_spec2(spec2, local_collection)


def parse_specname(specname, api_collection, local_collection):
    phase = 0
    mdn_key = None
    name = None
    url = None
    slugs = set([
        s.slug for s in api_collection.get_resources('specifications')])
    mdn_key_re = re.compile(r"\s+['\"](.*)['\"]\s*:\s*{")
    name_re = re.compile(r"\s+name\s*:\s*['\"](.*)['\"],?\s*$")
    url_re = re.compile(r"\s+url\s*:\s*['\"](.*)['\"],?\s*$")
    api_specs = api_collection.get_resources_by_data_id('specifications')

    for line in specname.split('\n'):
        if phase == 0:
            # Looking for start of specList
            if line.startswith('var specList = {'):
                phase = 1
        elif phase == 1:
            # Inside specList
            if line.startswith('}'):
                phase = 2
            elif mdn_key_re.match(line):
                assert mdn_key is None
                mdn_key = mdn_key_re.match(line).group(1).strip()
            elif name_re.match(line):
                assert name is None
                name = name_re.match(line).group(1).strip()
            elif url_re.match(line):
                assert url is None
                url = url_re.match(line).group(1).strip()
            elif line.startswith('    }'):
                assert mdn_key is not None
                assert name is not None
                assert url is not None
                if url.startswith('http'):
                    api_spec = api_specs.get(('specifications', mdn_key))
                    if api_spec:
                        slug = api_spec.slug
                    else:
                        slug = unique_slugify(mdn_key, slugs)
                    spec = Specification(
                        id="_" + slug, slug=slug, mdn_key=mdn_key,
                        name={u'en': name}, uri={u'en': url}, sections=[])
                    local_collection.add(spec)
                else:
                    logger.warning(
                        'Discarding specification "%s" with url "%s"',
                        mdn_key, url)
                mdn_key = None
                name = None
                url = None
            else:
                raise Exception('Unparsed line:', line)
        elif phase == 2:
            # Not processing rest of SpecName, including dupe lines
            pass
    assert phase == 2, "SpecName didn't match expected format"


def parse_spec2(specname, local_collection):
    phase = 0
    key = None
    name = None
    status_re = re.compile(r"\s+['\"](.*)['\"]\s+: ['\"](.*)['\"],?\s*$")
    mat_re = re.compile(r"\s+['\"](.*)['\"]\s*:\s*mdn\.localString\({\s*$")
    name_re = re.compile(r"\s+['\"](.*)['\"]\s*:\s*['\"](.*)['\"],?\s*$")
    local_specs = local_collection.get_resources_by_data_id('specifications')

    for line in spec2.split('\n'):
        if phase == 0:
            # Looking for start of status
            if line.startswith('var status = {'):
                phase = 1
        elif phase == 1:
            # Inside status
            if line.startswith('}'):
                phase = 2
            elif status_re.match(line):
                spec_key, maturity_key = status_re.match(line).groups()
                spec = local_specs.get(('specifications', spec_key))
                if spec:
                    spec.maturity = maturity_key
                else:
                    logger.warning(
                        'Skipping maturity for unknown spec "%s"', spec_key)
            else:
                raise Exception('Unparsed line:', line)
        elif phase == 2:
            # Skiping dupe lines, looking for var label
            if line.startswith('var label = {'):
                phase = 3
        elif phase == 3:
            if line.startswith('}'):
                phase = 4
            elif mat_re.match(line):
                assert key is None
                key = mat_re.match(line).group(1).strip()
                name = {}
            elif name_re.match(line):
                assert key is not None
                assert name is not None
                lang, trans = name_re.match(line).groups()
                if lang == 'en-US':
                    lang = 'en'
                assert lang not in name
                text = trans.strip().replace('\\\\', '&#92;')
                text = text.replace('\\', '').replace('&#92;', '\\')
                name[lang.strip()] = text
            elif line.startswith('  })'):
                assert key is not None
                assert name
                specs = local_collection.filter(
                    'specifications', maturity=key)
                if specs:
                    maturity = Maturity(id=key, slug=key, name=name)
                    local_collection.add(maturity)
                else:
                    logger.warning('Skipping unused maturity "%s"', key)
                key = None
                name = None
        elif phase == 4:
            # Not processing rest of file
            pass
    assert phase == 4, "Spec2 didn't match expected format"

    # Remove Specs without maturities
    immature_specs = local_collection.filter('specifications', maturity=None)
    for spec in immature_specs:
        logger.warning('Skipping spec with no maturity "%s"', spec.name['en'])
        local_collection.remove(spec)


def slugify(word, attempt=0):
    # TODO: replace with mdn.scrape.slugify
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
    return slugged[slice(50 - len(suffix))] + suffix


def unique_slugify(word, existing):
    slug = slugify(word)
    attempt = 0
    while slug in existing:
        attempt += 1
        slug = slugify(word, attempt)
    existing.add(slug)
    return slug


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
    description = 'Initialize with specification data from MDN.'
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
    logger.info("Loading data into %s" % api)

    # Get credentials
    user = args.user or input("API username: ")
    password = getpass.getpass("API password: ")

    # Initialize client
    client = Client(api)
    client.login(user, password)

    # Load data
    specname = get_template(SPECNAME_FILENAME, SPECNAME_URL)
    spec2 = get_template(SPEC2_FILENAME, SPEC2_URL)
    counts = load_spec_data(client, specname, spec2, confirm_changes)

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
