"""Common tool code."""
from __future__ import print_function

import argparse
import codecs
import getpass
import logging
import os.path
import string
import sys

import requests

from client import Client
from resources import CollectionChangeset

_my_dir = os.path.dirname(os.path.realpath(__file__))
_data_dir = os.path.realpath(os.path.join(_my_dir, '..', 'data'))

try:
    input = raw_input  # Get the Py2 raw_input
except NameError:
    pass  # We're in Py3


class ToolParser(argparse.ArgumentParser):
    """Parser with common options."""

    class StripTrailingSlash(argparse.Action):
        def __call__(self, parser, namespace, values, option_string=None):
            if values.endswith('/'):
                values = values[:-1]
            setattr(namespace, self.dest, values)

    def __init__(
            self, logger=None, include=None, *args, **kwargs):
        """Initialize the parser.

        Same as ArgumentParser, but with additional options:
        logger - Initialize the logger with -v/-q options
        include - list of additional options to include.  Supported:
            api - Add --api option
            user - Add --user option
            password - Add --password option
            data - Add --data option
        """
        super(ToolParser, self).__init__(*args, **kwargs)

        self.include_set = set(include or [])
        valid = set(['api', 'user', 'password', 'data'])
        if self.include_set - valid:
            raise ValueError(
                'Unknown include items: {}'.format(self.include_set - valid))

        if 'api' in self.include_set:
            self.add_argument(
                '-a', '--api',
                help='Base URL of the API (default: http://localhost:8000)',
                default="http://localhost:8000",
                action=ToolParser.StripTrailingSlash)

        if 'user' in self.include_set:
            self.add_argument(
                '-u', '--user',
                help='Username on API (default: prompt for username)')

        if 'password' in self.include_set:
            self.add_argument(
                '-p', '--password',
                help='Password on API (default: prompt for password)')

        if logger:
            self.logger = logger
            self.add_argument(
                '-v', '--verbose', action="store_true",
                help='Print extra debug information')
            self.add_argument(
                '-q', '--quiet', action="store_true",
                help='Only print warnings')

        if 'data' in self.include_set:
            self.add_argument(
                '-d', '--data', default=_data_dir,
                action=ToolParser.StripTrailingSlash,
                help='Output data folder (default: %s)' % _data_dir)

    def parse_args(self, *args, **kwargs):
        args = super(ToolParser, self).parse_args(*args, **kwargs)

        # Setup logger w/ options
        if self.logger:
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

        return args


class Tool(object):
    """A tool for working with the API."""
    logger_name = 'tools'
    parser_options = []

    def __init__(self):
        """Initialize the tool."""
        self.api = None
        self._client = None
        self.logger = logging.getLogger(self.logger_name)
        self.data = 'data'

    def cached_download(self, filename, url):
        """Download a file, then serve it from the cache."""
        path = self.data_file(filename)
        if not os.path.exists(path):
            self.logger.info("Downloading " + path)
            r = requests.get(url)
            with codecs.open(path, 'wb', 'utf8') as f:
                f.write(r.text)
        else:
            self.logger.info("Using existing " + path)

        with codecs.open(path, 'r', 'utf8') as f:
            content = f.read()
        return content

    @property
    def client(self):
        """Return an API Client."""
        assert self.api, 'Must set API first'
        if not self._client:
            self._client = Client(self.api)
        return self._client

    def confirm_changes(self, changeset):
        """Ask the user to confirm a changeset."""
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

    def data_file(self, filename):
        """Return the path to a data file."""
        return os.path.join(self.data, filename)

    def get_parser(self):
        """Construct the command line parser."""
        description = self.__doc__.split('\n')[0]
        parser = ToolParser(
            description=description, logger=self.logger,
            include=self.parser_options)
        return parser

    def get_password(self):
        """Get the password, prompting if needed."""
        if not getattr(self, 'password'):
            self.password = getpass.getpass("API password: ")
        return self.password

    def get_user(self):
        """Get the user, prompting if needed."""
        if not getattr(self, 'user'):
            self.user = input("API username: ")
        return self.user

    def init_from_command_line(self):
        """Initialize the tool from the command line."""
        parser = self.get_parser()
        args = parser.parse_args()
        for key, value in vars(args).items():
            setattr(self, key, value)
        return args

    def login(self):
        user = self.get_user()
        password = self.get_password()
        self.client.login(user, password)

    def report_changes(self, counts):
        if counts:
            self.logger.info("Changes complete. Counts:")
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
                    self.logger.info("  %s: %s" % (
                        resource_type.title(), ', '.join(c_text)))
        else:
            self.logger.info("No data uploaded.")

    def run(self, *args, **kwargs):
        """Run the tool."""
        raise NotImplementedError('run not implemented')

    def slugify(self, word, attempt=0):
        """Slugify a word, mixing in an attempt count as needed."""
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

    def sync_changes(self, api_collection, local_collection):
        """Sync changes to a remote collection from a local collection

        Returns a dictionary counting the new, changed, and deleted items,
        or an empty dictionary if no changes.
        """
        self.logger.info('Looking for changes...')
        changeset = CollectionChangeset(api_collection, local_collection)
        delta = changeset.changes

        if delta['new'] or delta['changed'] or delta['deleted']:
            self.logger.info(
                'Changes detected: %d new, %d changed, %d deleted, %d same.',
                len(delta['new']), len(delta['changed']),
                len(delta['deleted']), len(delta['same']))
            confirmed = self.confirm_changes(changeset)
            if not confirmed:
                return {}
        else:
            self.logger.info('No changes')
            return {}

        return changeset.change_original_collection()

    def unique_slugify(self, word, existing):
        slug = self.slugify(word)
        attempt = 0
        while slug in existing:
            attempt += 1
            slug = self.slugify(word, attempt)
        existing.add(slug)
        return slug
