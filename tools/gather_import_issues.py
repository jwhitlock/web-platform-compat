#!/usr/bin/env python

from __future__ import print_function

from collections import Counter
from json import dumps
from HTMLParser import HTMLParser
import csv
import re
import time

from common import Tool


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


class GatherImportIssues(Tool):
    """Gather import issues into CSVs."""
    logger_name = 'tools.gather_import_issues'
    parser_options = ['api', 'data']

    def run(self, by_url_csv, by_issue_csv, *args, **kwargs):
        issue_rows = self.download_issues()
        issue_counts = Counter()

        # Write by-url CSV and count issues
        by_url_writer = csv.writer(by_url_csv)
        by_url_writer.writerow([
            "MDN Slug", "Import URL", "Issue Slug", "Source Start",
            "Source End", "Params"])
        for row in issue_rows:
            err = row[2]
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

    def download_issues(self):
        """Download issues from API."""
        assert self.api, 'Must set api to API base URL'

        # Gather import links
        start = time.time()
        self.logger.info("Gathering import URLs from %s...", self.api)
        page = 1
        parser = GatherLinks()
        status = 200
        while status == 200:
            index_url = self.api + '/importer/'
            index_resp = self.client.session.get(
                index_url, params={'page': page})
            status = index_resp.status_code
            if status == 200:
                parser.feed(index_resp.text)
                page += 1
        import_urls = parser.get_urls()
        total_urls = len(import_urls)
        end = time.time()
        self.logger.info(
            "Found %d import URLs in %0.1fs", total_urls, end - start)

        # Gather issues
        issue_rows = []
        start = time.time()
        for url_count, raw_url in enumerate(import_urls):
            url = self.api + raw_url
            human_import_url = url.replace('.json', '')
            resp = self.client.session.get(url)
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
                    (mdn_slug, human_import_url, issue_slug, start_pos,
                     end_pos, params))
            end = time.time()
            if (end - start) > 15:
                percent = (
                    100.0 * (1 - (total_urls - url_count + 1.0) / total_urls))
                self.logger.info(
                    "Found %d issues in %d imports (%d%%)",
                    len(issue_rows), url_count + 1, percent)
                start = time.time()

        return issue_rows


if __name__ == '__main__':
    tool = GatherImportIssues()
    tool.init_from_command_line()
    tool.logger.info("Loading import issues from {tool.api}".format(tool=tool))

    counts = {}
    by_url_csv = None
    by_issue_csv = None
    by_url_file = tool.data_file('import_issues_by_url.csv')
    by_issue_file = tool.data_file('import_issue_counts.csv')
    try:
        by_url_csv = open(by_url_file, "wb")
        by_issue_csv = open(by_issue_file, "wb")
        counts = tool.run(by_url_csv, by_issue_csv)
    finally:
        if by_issue_csv:
            by_issue_csv.close()
        if by_url_csv:
            by_url_csv.close()

    if counts:
        c_unique = counts.get('unique', 0)
        c_total = counts.get('total', 0)
        tool.logger.info(
            "Issues collected: %d unique (%d total)", c_unique, c_total)
        tool.logger.info("Issue details in %s", by_url_file)
        tool.logger.info("Issue counts in %s", by_issue_file)
    else:
        tool.logger.info("No issues found.")
