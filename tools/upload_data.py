#!/usr/bin/env python
from collections import OrderedDict
import codecs
import json

from common import Tool
from resources import Collection


class UploadData(Tool):
    """Upload data to the API."""
    logger_name = 'tools.upload_data'
    parser_options = ['api', 'user', 'password', 'data']

    def run(self, *args, **kwargs):
        self.login()
        api_collection = Collection(self.client)
        local_collection = Collection()
        resources = [
            'browsers', 'versions', 'features', 'supports', 'specifications',
            'maturities', 'sections']

        self.logger.info('Reading existing data from API')
        for resource in resources:
            count = api_collection.load_all(resource)
            self.logger.info("Downloaded %d %s.", count, resource)

        self.logger.info('Reading upload data from disk')
        for resource in resources:
            filepath = self.data_file('{}.json'.format(resource))
            with codecs.open(filepath, 'r', 'utf8') as f:
                data = json.load(f, object_pairs_hook=OrderedDict)
            resource_class = local_collection.resource_by_type[resource]
            for item in data[resource]:
                obj = resource_class()
                obj.from_json_api({resource: item})
                local_collection.add(obj)

        return self.sync_changes(api_collection, local_collection)

    def get_parser(self):
        parser = super(UploadData, self).get_parser()
        parser.add_argument(
            '--noinput', action="store_true",
            help='Upload any changes without prompting the user for input')
        return parser

    def confirm_changes(self, changeset):
        if self.noinput:
            return True
        else:
            return super(UploadData, self).confirm_changes(changeset)


if __name__ == '__main__':
    tool = UploadData()
    tool.init_from_command_line()
    tool.logger.info(
        "Uploading data from {tool.data} to {tool.api}".format(tool=tool))
    if tool.noinput and not (tool.user and tool.password):
        raise Exception("--noinput requires --user and --password")
    changes = tool.run()
    tool.report_changes(changes)
