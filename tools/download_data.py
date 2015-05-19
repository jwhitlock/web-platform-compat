#!/usr/bin/env python
import codecs
import json

from common import Tool


class DownloadData(Tool):
    """Download data from the API."""
    logger_name = 'tools.download_data'
    parser_options = ['api', 'data']

    def run(self, *args, **kwargs):
        counts = {}
        resources = [
            'browsers', 'versions', 'features', 'supports', 'specifications',
            'maturities', 'sections']
        for resource in resources:
            # Get data from API
            data = self.client.get_resource_collection(resource)
            self.logger.info(
                "Downloaded {} {}".format(len(data[resource]), resource))
            counts[resource] = len(data[resource])

            # Remove history relations
            for item in data[resource]:
                del item['links']['history']
                del item['links']['history_current']
            if 'links' in data:
                del data['links'][resource + '.history']
                del data['links'][resource + '.history_current']

            # Write to a file
            filepath = self.data_file('{}.json'.format(resource))
            with codecs.open(filepath, 'w', 'utf8') as f:
                json.dump(data, f, indent=4, separators=(',', ': '))
        return counts


if __name__ == '__main__':
    tool = DownloadData()
    tool.init_from_command_line()
    tool.logger.info(
        "Downloading data from {tool.api} to {tool.data}".format(tool=tool))
    counts = tool.run()
    if counts:
        tool.logger.info("Download complete.")
    else:
        tool.logger.info("No data downloaded.")
