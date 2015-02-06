#!/usr/bin/env python

from __future__ import print_function

import getpass
import logging
import os.path
import sys
import time

from client import Client
from resources import Collection

try:
    input = raw_input  # Get the Py2 raw_input
except NameError:
    pass  # We're in Py3

logger = logging.getLogger('tools.import_mdn')
my_dir = os.path.dirname(os.path.realpath(__file__))
data_dir = os.path.realpath(os.path.join(my_dir, '..', 'data'))


def import_mdn_data(client, rate=5):
    collection = Collection(client)
    collection.load_all('features')

    # Collect feature URIs
    uris = []
    for feature in collection.get_resources('features'):
        if feature.mdn_uri and feature.mdn_uri.get('en'):
            uris.append((feature.mdn_uri['en'], feature.id.id))
    total = len(uris)
    logger.info('Features loaded, %d MDN pages found.', total)

    # Import from MDN, with rate limiting
    start_time = time.time()
    mdn_requests = 0
    counts = {'new': 0, 'reset': 0, 'reparsed': 0, 'unchanged': 0}
    importer_search = client.base_url + '/importer/search'
    log_at = 15
    logged_at = time.time()
    for uri, f_id in uris:
        response = client.session.get(importer_search, params={'url': uri})
        if 'importer/create?' in response.url:
            logger.info('Fetching %s...', uri)
            counts['new'] += 1
            create_url = response.url
            csrf = client.session.cookies['csrftoken']
            params = {
                'url': uri,
                'feature': f_id,
                'csrfmiddlewaretoken': csrf,
            }
            response = client.session.post(create_url, params)
            mdn_requests += 1
        else:
            response.raise_for_status()
            obj_url = response.url
            assert '/importer/' in obj_url
            reparse_url = obj_url + '/reparse'
            csrf = client.session.cookies['csrftoken']
            params = {'csrfmiddlewaretoken': csrf}
            response = client.session.post(reparse_url, params)
            counts['reparsed'] += 1

        # Pause for rate limiting?
        current_time = time.time()
        if rate:
            elapsed = current_time - start_time
            target = start_time + float(mdn_requests) / rate
            current_rate = float(mdn_requests) / elapsed
            if time.time < target:
                rest = int(target - current_time) + 1
                logger.warning(
                    "%d pages fetched, %0.2f per second, target rate %d per"
                    " second.  Resting %d seconds.",
                    mdn_requests, current_rate, rate, rest)
                time.sleep(rest)
                logged_at = time.time()
                current_time = time.time()

        # Log progress?
        if (logged_at + log_at) < current_time:
            processed = sum(counts.values())
            percent = int(100 * (float(processed) / total))
            logger.info(
                "  Processed %d of %d MDN pages (%d%%)...",
                processed, total, percent)
            logged_at = current_time

    return counts


if __name__ == '__main__':
    import argparse
    description = 'Import features from MDN, or reparse imported features.'
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
    counts = import_mdn_data(client)

    if counts:
        logger.info("Import complete. Counts:")
        c_new = counts.get('new', 0)
        c_reset = counts.get('reset', 0)
        c_reparsed = counts.get('reparsed', 0)
        c_unchanged = counts.get('unchanged', 0)
        c_text = []
        if c_new:
            c_text.append("%d new" % c_new)
        if c_reset:
            c_text.append("%d reset" % c_reset)
        if c_reparsed:
            c_text.append("%d reparsed" % c_reparsed)
        if c_unchanged:
            c_text.append("%d unchanged" % c_unchanged)
        if c_text:
            logger.info(', '.join(c_text))
    else:
        logger.info("No data uploaded.")
