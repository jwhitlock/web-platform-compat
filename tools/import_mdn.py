#!/usr/bin/env python
import time

from common import Tool
from resources import Collection


class ImportMDNData(Tool):
    """Import features from MDN, or reparse imported features."""
    logger_name = 'tools.import_mdn'
    parser_options = ['api', 'user', 'password']

    def run(self, rate=5, *args, **kwargs):
        self.login()
        collection = Collection(self.client)
        collection.load_all('features')

        # Collect feature URIs
        uris = []
        for feature in collection.get_resources('features'):
            if feature.mdn_uri and feature.mdn_uri.get('en'):
                uris.append((feature.mdn_uri['en'], feature.id.id))
        total = len(uris)
        self.logger.info('Features loaded, %d MDN pages found.', total)

        # Import from MDN, with rate limiting
        start_time = time.time()
        mdn_requests = 0
        counts = {'new': 0, 'reset': 0, 'reparsed': 0, 'unchanged': 0}
        importer_search = self.api + '/importer/search'
        log_at = 15
        logged_at = time.time()
        for uri, f_id in uris:
            response = self.client.session.get(
                importer_search, params={'url': uri})
            if 'importer/create?' in response.url:
                self.logger.info('Fetching %s...', uri)
                counts['new'] += 1
                create_url = response.url
                csrf = self.client.session.cookies['csrftoken']
                params = {
                    'url': uri,
                    'feature': f_id,
                    'csrfmiddlewaretoken': csrf,
                }
                response = self.client.session.post(create_url, params)
                mdn_requests += 1
            else:
                response.raise_for_status()
                obj_url = response.url
                assert '/importer/' in obj_url
                reparse_url = obj_url + '/reparse'
                csrf = self.client.session.cookies['csrftoken']
                params = {'csrfmiddlewaretoken': csrf}
                response = self.client.session.post(reparse_url, params)
                counts['reparsed'] += 1

            # Pause for rate limiting?
            current_time = time.time()
            if rate:
                elapsed = current_time - start_time
                target = start_time + float(mdn_requests) / rate
                current_rate = float(mdn_requests) / elapsed
                if time.time < target:
                    rest = int(target - current_time) + 1
                    self.logger.warning(
                        "%d pages fetched, %0.2f per second, target rate %d"
                        " per second.  Resting %d seconds.",
                        mdn_requests, current_rate, rate, rest)
                    time.sleep(rest)
                    logged_at = time.time()
                    current_time = time.time()

            # Log progress?
            if (logged_at + log_at) < current_time:
                processed = sum(counts.values())
                percent = int(100 * (float(processed) / total))
                self.logger.info(
                    "  Processed %d of %d MDN pages (%d%%)...",
                    processed, total, percent)
                logged_at = current_time

        return counts


if __name__ == '__main__':
    tool = ImportMDNData()
    tool.init_from_command_line()
    tool.logger.info("Loading data into {tool.api}".format(tool=tool))
    counts = tool.run()

    if counts:
        tool.logger.info("Import complete. Counts:")
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
            tool.logger.info(', '.join(c_text))
    else:
        tool.logger.info("No data uploaded.")
