#!/usr/bin/env python
from __future__ import print_function

import re
import random
import webbrowser

from common import Tool

try:
    input = raw_input  # Py2?
except NameError:
    pass  # Nope Py3

re_url = re.compile(r'\s*"url":\s"([^"]*)"')


class SampleMDN(Tool):
    """Open a random MDN URL scraped from the webcompat project."""
    logger_name = 'tools.sample_mdn'

    def run(self, *args, **kwargs):
        count = 0
        urls = self.get_urls()
        while True:
            url = random.choice(urls)
            self.logger.info("%d: %s", count, url)
            count += 1
            webbrowser.open(url + '#Specifications')
            x = input("Enter to continue, or q+Enter to quit: ")

            if x == 'q':
                break

        self.logger.info("%d URLs visited" % count)
        return count

    def get_urls(self):
        data_human = self.cached_download(
            'data-human.json',
            "https://raw.githubusercontent.com/webplatform/compatibility-data"
            "/master/data-human.json")

        urls = []
        for raw_line in data_human.split('\n'):
            line = raw_line.strip()
            match = re_url.match(line)
            if match:
                url = match.group(1)
                urls.append(url)
        return urls


if __name__ == '__main__':
    tool = SampleMDN()
    tool.init_from_command_line()
    tool.run()
