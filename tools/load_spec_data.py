#!/usr/bin/env python

from __future__ import print_function

import getpass
import json
import logging
import os.path
import re
import string
import sys
import urllib

import requests

try:
    input = raw_input  # Get the Py2 raw_input
except NameError:
    pass  # We're in Py3


logger = logging.getLogger('populate_data')
SPEC2_FILENAME = 'Spec2.txt'
SPEC2_URL = 'https://developer.mozilla.org/en-US/docs/Template:Spec2?raw'
SPECNAME_FILENAME = 'SpecName.txt'
SPECNAME_URL = 'https://developer.mozilla.org/en-US/docs/Template:SpecName?raw'


def get_session(base_url, user, password):
    '''Create an authenticated connection to the API'''
    session = requests.Session()
    next_path = '/api/v1/browsers'
    params = {'next': next_path}
    response = session.get(base_url + '/api-auth/login/', params=params)
    try:
        csrf = response.cookies['csrftoken']
    except KeyError:
        raise Exception("No CSRF in response", response)
    data = {
        'username': user,
        'password': password,
        'csrfmiddlewaretoken': csrf,
        'next': next_path
    }
    response = session.post(
        base_url + '/api-auth/login/', params=params, data=data)
    if response.url == base_url + next_path:
        logger.info("Logged into " + base_url)
        session.base_url = base_url
        return session
    else:
        raise Exception('Problem logging in.', response)


def verify_empty_api(session):
    '''Verify that no data is loaded into this API'''
    response = session.get(
        session.base_url + '/api/v1/specifications',
        headers={'content-type': 'application/vnd.api+json'})
    expected = {
        'specifications': [],
        'meta': {
            'pagination': {
                'specifications': {
                    'count': 0,
                    'next': None,
                    'previous': None
                }
            }
        }
    }
    actual = response.json()
    if response.json() != expected:
        raise Exception('API already has browser data', actual)


def get_template(filename, url):
    if not os.path.exists(filename):
        logger.info("Downloading " + filename)
        urllib.urlretrieve(url, filename)
    else:
        logger.info("Using existing " + filename)

    with open(filename, 'r') as f:
        template = f.read()
    return template


def load_spec_data(session, specname, spec2):
    '''Load a dictionary of specification data into the API'''
    verify_empty_api(session)
    parsed_data = parse_spec_data(specname, spec2)
    return upload_spec_data(session, parsed_data)


def parse_spec_data(specname, spec2):
    parsed_data = {
        'maturities': dict(),
        'specifications': dict(),
        'spec_slugs': set(),
    }

    parse_specname(specname, parsed_data)
    parse_spec2(spec2, parsed_data)
    return parsed_data


def parse_specname(specname, parsed_data):
    phase = 0
    mdn_key = None
    name = None
    url = None
    mdn_key_re = re.compile(r"\s+['\"](.*)['\"]\s*:\s*{")
    name_re = re.compile(r"\s+name\s*:\s*['\"](.*)['\"],?\s*$")
    url_re = re.compile(r"\s+url\s*:\s*['\"](.*)['\"],?\s*$")
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
                    slug = unique_slugify(mdn_key, parsed_data['spec_slugs'])
                    spec_id = mdn_key
                    parsed_data['specifications'][spec_id] = {
                        'slug': slug,
                        'mdn_key': mdn_key,
                        'name': {'en': name},
                        'uri': {'en': url},
                    }
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


def parse_spec2(spec2, parsed_data):
    phase = 0
    key = None
    name = None
    status_re = re.compile(r"\s+['\"](.*)['\"]\s+: ['\"](.*)['\"],?\s*$")
    mat_re = re.compile(r"\s+['\"](.*)['\"]\s*:\s*mdn\.localString\({\s*$")
    name_re = re.compile(r"\s+['\"](.*)['\"]\s*:\s*['\"](.*)['\"],?\s*$")

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
                spec = parsed_data['specifications'].get(spec_key.strip())
                if spec:
                    spec['maturity_id'] = maturity_key.strip()
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
                name[lang.strip()] = trans.strip().decode('string_escape')
            elif line.startswith('  })'):
                assert key is not None
                assert name
                mat_id = key
                parsed_data['maturities'][mat_id] = {
                    'slug': mat_id,
                    'name': name,
                }
                key = None
                name = None
        elif phase == 4:
            # Not processing rest of file
            pass
    assert phase == 4, "Spec2 didn't match expected format"


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
    return slugged[slice(50-len(suffix))] + suffix


def unique_slugify(word, existing):
    slug = slugify(word)
    attempt = 0
    while slug in existing:
        attempt += 1
        slug = slugify(word, attempt)
    existing.add(slug)
    return slug


def upload_spec_data(session, parsed_data):
    api_ids = dict(
        (n, {}) for n in ['maturities', 'specifications'])

    logger.info("Importing specifications...")
    for specification_id in sorted(parsed_data['specifications'].keys()):
        upload_specification(session, specification_id, parsed_data, api_ids)
        if len(api_ids['specifications']) % 100 == 0:
            logger.info(
                "Imported %d specifications..." %
                len(api_ids['specifications']))

    counts = dict((n, len(api_ids[n])) for n in api_ids)
    return counts


def upload_maturity(session, maturity_id, parsed_data, api_ids):
    '''Upload a parsed maturity to the API

    Keyword Arguments:
    session - authenticated session to use for uploads
    maturity_id - ID of the maturity in parsed_data['maturities']
    parsed_data - dictionary of all the parsed data
    api_ids - dictionary of IDs of uploaded instances

    Return is the ID generated by the API
    '''
    if maturity_id not in api_ids['maturities']:
        maturity = parsed_data['maturities'][maturity_id]
        data = {
            "slug": maturity['slug'],
            "name": maturity['name']
        }
        maturity_json = json.dumps({"maturities": data})
        response = session.post(
            session.base_url + '/api/v1/maturities', data=maturity_json,
            headers={
                'content-type': 'application/vnd.api+json',
                'X-CSRFToken': session.cookies['csrftoken']})
        assert response.status_code == 201, response.content
        api_id = response.json()['maturities']['id']
        api_ids['maturities'][maturity_id] = api_id
    return api_ids['maturities'][maturity_id]


def upload_specification(session, specification_id, parsed_data, api_ids):
    '''Upload a parsed specification to the API

    Keyword Arguments:
    session - authenticated session to use for uploads
    specification_id - ID of the specification in parsed_data['specifications']
    parsed_data - dictionary of all the parsed data
    api_ids - dictionary of IDs of uploaded instances

    Return is the ID generated by the API
    '''
    if specification_id not in api_ids['specifications']:
        specification = parsed_data['specifications'][specification_id]
        if 'maturity_id' not in specification:
            logger.warning(
                'Not uploading specification "%s", no associated maturity',
                specification_id)
            return None
        maturity_id = specification['maturity_id']
        maturity_api_id = upload_maturity(
            session, maturity_id, parsed_data, api_ids)
        data = {
            "slug": specification['slug'],
            "mdn_key": specification['mdn_key'],
            "name": specification['name'],
            "uri": specification['uri'],
            "links": {
                "maturity": maturity_api_id
            }
        }
        specification_json = json.dumps({"specifications": data})
        response = session.post(
            session.base_url + '/api/v1/specifications',
            data=specification_json,
            headers={
                'content-type': 'application/vnd.api+json',
                'X-CSRFToken': session.cookies['csrftoken']})
        assert response.status_code == 201, response.content
        api_id = response.json()['specifications']['id']
        api_ids['specifications'][specification_id] = api_id
    return api_ids['specifications'][specification_id]


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
    logger_name = 'populate_data'
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
    session = get_session(api, user, password)

    # Load data
    specname = get_template(SPECNAME_FILENAME, SPECNAME_URL)
    spec2 = get_template(SPEC2_FILENAME, SPEC2_URL)
    counts = load_spec_data(session, specname, spec2)

    logger.info("Upload complete. Counts:")
    for name, count in counts.items():
        logger.info("  %s: %d" % (name, count))
