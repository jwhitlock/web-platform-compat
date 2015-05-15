#!/usr/bin/env python

from __future__ import print_function

from collections import Counter
from json import dumps
from HTMLParser import HTMLParser
import csv
import logging
import os.path
import re
import sys
import time

from client import Client

logger = logging.getLogger('tools.gather_import_issues')
my_dir = os.path.dirname(os.path.realpath(__file__))
data_dir = os.path.realpath(os.path.join(my_dir, '..', 'data'))
BY_URL_CSV_FILENAME = os.path.join(data_dir, 'import_issues_by_url.csv')
BY_ERRORS_CSV_FILENAME = os.path.join(data_dir, 'import_issue_counts.csv')


class GatherLinks(HTMLParser):
    re_url = re.compile(r'^/importer/(?P<num>\d+)$')

    def __init__(self, *args, **kwargs):
        self.import_ids = set()
        HTMLParser.__init__(self, *args, **kwargs)

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            for attr, value in attrs:
                if attr == 'href':
                    m = self.re_url.match(value)
                    if m:
                        self.import_ids.add(int(m.group("num")))

    def get_urls(self):
        return ["/importer/%d.json" % i for i in sorted(self.import_ids)]


def gather_import_issues(client, by_url_csv, by_issue_csv):
    issue_rows = download_issues(client)
    issue_counts = Counter()

    # Write by-url CSV and count issues
    by_url_writer = csv.writer(by_url_csv)
    by_url_writer.writerow(
        ["MDN Slug", "Import URL", "Issue Slug", "Source Start", "Source End",
         "Params"])
    for row in issue_rows:
        err = row[4]
        issue_counts[err] += 1
        by_url_writer.writerow(row)

    # Write by_issue CSV
    by_issue_writer = csv.writer(by_issue_csv)
    by_issue_writer.writerow(["Count", "Issue"])
    for err, count in issue_counts.most_common():
        by_issue_writer.writerow((count, err))

    return {
        'total': len(issue_rows),
        'unique': len(issue_counts),
    }


def download_issues(client):
    # Gather import links
    start = time.time()
    logger.info("Gathering import URLs from %s...", client.base_url)
    page = 1
    parser = GatherLinks()
    status = 200
    while status == 200:
        index_url = client.base_url + '/importer/'
        index_resp = client.session.get(index_url, params={'page': page})
        status = index_resp.status_code
        if status == 200:
            parser.feed(index_resp.text)
            page += 1
    import_urls = parser.get_urls()
    total_urls = len(import_urls)
    end = time.time()
    logger.info("Found %d import URLs in %0.1fs", total_urls, end - start)

    # Gather issues
    issue_rows = []
    start = time.time()
    for url_count, raw_url in enumerate(import_urls):
        url = client.base_url + raw_url
        human_import_url = url.replace('.json', '')
        resp = client.session.get(url)
        resp.raise_for_status()
        resp_json = resp.json()
        mdn_uri = resp_json['features']['mdn_uri']['en']
        mdn_prefix = 'https://developer.mozilla.org/en-US/docs/'
        assert mdn_uri.startswith(mdn_prefix)
        mdn_slug = mdn_uri.replace(mdn_prefix, '', 1)
        issues = resp_json['meta']['scrape']['issues']
        for issue in issues:
            assert isinstance(issue, list)
            issue_slug, start_pos, end_pos, raw_params = issue
            params = dumps(raw_params)
            issue_rows.append(
                (mdn_slug, human_import_url, issue_slug, start_pos, end_pos,
                 params))
        end = time.time()
        if (end - start) > 15:
            percent = 100.0 * (1 - (total_urls - url_count + 1.0) / total_urls)
            logger.info(
                "Found %d issues in %d imports (%d%%)",
                len(issue_rows), url_count + 1, percent)
            start = time.time()

    return issue_rows


if __name__ == '__main__':
    import argparse
    description = 'Gather import issues into CSVs.'
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        '-a', '--api',
        help='Base URL of the API (default: http://localhost:8000)',
        default="http://localhost:8000")
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
    logger.info("Loading importer issues from %s" % api)

    # Initialize client
    client = Client(api)

    # Gather issues and write to CSVs
    counts = {}
    by_url_csv = None
    by_issue_csv = None
    try:
        by_url_csv = open(BY_URL_CSV_FILENAME, "wb")
        by_issue_csv = open(BY_ERRORS_CSV_FILENAME, "wb")
        counts = gather_import_issues(client, by_url_csv, by_issue_csv)
    finally:
        if by_issue_csv:
            by_issue_csv.close()
        if by_url_csv:
            by_url_csv.close()

    if counts:
        c_unique = counts.get('unique', 0)
        c_total = counts.get('total', 0)
        logger.info(
            "Issues collected: %d unique (%d total)", c_unique, c_total)
        logger.info("Issue details in %s", BY_URL_CSV_FILENAME)
        logger.info("Issue counts in %s", BY_ERRORS_CSV_FILENAME)
    else:
        logger.info("No issues found.")
