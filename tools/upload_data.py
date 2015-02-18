#!/usr/bin/env python

from __future__ import print_function

from collections import OrderedDict
import codecs
import getpass
import json
import logging
import os.path
import sys

from client import Client
from resources import Collection, CollectionChangeset

try:
    input = raw_input  # Get the Py2 raw_input
except NameError:
    pass  # We're in Py3

logger = logging.getLogger('tools.upload_data')

resources = [
    'browsers',
    'versions',
    'features',
    'supports',
    'specifications',
    'maturities',
    'sections',
]


def upload_data(client, base_dir='', confirm=None):
    """Upload data to the API"""
    api_collection = Collection(client)
    local_collection = Collection()

    logger.info('Reading existing data from API')
    load_api_data(api_collection)
    logger.info('Reading upload data from disk')
    load_local_data(local_collection, base_dir)

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


def load_api_data(api_collection):
    for resource in resources:
        count = api_collection.load_all(resource)
        logger.info("Downloaded %d %s.", count, resource)


def load_local_data(local_collection, base_dir):
    for resource in resources:
        filepath = os.path.join(base_dir, '%s.json' % resource)
        with codecs.open(filepath, 'r', 'utf8') as f:
            data = json.load(f, object_pairs_hook=OrderedDict)
        resource_class = local_collection.resource_by_type[resource]
        for item in data[resource]:
            obj = resource_class()
            obj.from_json_api({resource: item})
            local_collection.add(obj)


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
    description = 'Upload data to the API.'
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
        '-d', '--data', default='data',
        help='Input data folder (default: data)')
    args = parser.parse_args()

    # Setup logging
    verbose = args.verbose
    quiet = args.quiet
    console = logging.StreamHandler(sys.stderr)
    formatter = logging.Formatter('%(levelname)s - %(message)s')
    fmat = '%(levelname)s - %(message)s'
    logger_name = 'tools'
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
    data = args.data
    if data.endswith('/'):
        data = data[:-1]
    logger.info("Uploading data from %s to %s", data, api)

    # Get credentials
    user = args.user or input("API username: ")
    password = getpass.getpass("API password: ")

    # Initialize client
    client = Client(api)
    client.login(user, password)

    # Load data
    counts = upload_data(client, data, confirm_changes)

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
