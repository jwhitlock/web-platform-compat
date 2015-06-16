#!/usr/bin/env python

from __future__ import print_function

from cgi import escape
from json import loads
from string import lowercase
import time

from common import Tool
from resources import Collection, Feature


class MirrorMDNFeatures(Tool):
    """Create and Update API features for MDN pages."""
    logger_name = 'tools.mirror_mdn_features'
    parser_options = ['api', 'user', 'password', 'data']
    base_mdn_domain = 'https://developer.mozilla.org'
    base_mdn_uri = base_mdn_domain + '/en-US/docs/'
    rate = 5

    def __init__(self, *args, **kwargs):
        super(MirrorMDNFeatures, self).__init__(*args, **kwargs)
        self.rate_limit_start = time.time()
        self.rate_limit_requests = 0

    def run(self, *args, **kwargs):
        self.login()
        api_collection = Collection(self.client)
        self.logger.info('Reading existing features from API')
        api_collection.load_all('features')

        # Copy feature to working local collection
        local_collection = Collection()
        local_collection.load_collection(api_collection)
        features = self.known_features(local_collection)
        feature_by_uri = dict((k[0], k[2]) for k in features)
        feature_by_slug = dict((k[1], k[2]) for k in features)
        slugs = set(feature_by_slug.keys())

        self.logger.info('Reading pages from MDN')
        mdn_uris = self.current_mdn_uris()

        new_page, needs_url, existing_page = 0, 0, 0
        for path, parent_path, raw_slug, title in mdn_uris:
            uri = self.base_mdn_domain + path
            feature = feature_by_uri.get(uri)
            if feature:
                existing_page += 1
                feature.name = self.to_trans(title)
            else:
                slug = self.unique_slugify(raw_slug, slugs)
                feature = feature_by_slug.get(slug)
                if feature:
                    # Need to add URI to feature
                    feature.mdn_uri = {'en': uri}
                    feature_by_uri[uri] = feature
                    needs_url += 1
                else:
                    if parent_path:
                        parent_uri = self.base_mdn_domain + parent_path
                        parent_feature = feature_by_uri.get(parent_uri)
                        assert parent_feature,\
                            'No feature for parent page {}'.format(parent_uri)
                        parent_id = parent_feature.id.id
                    else:
                        parent_id = None
                    feature = Feature(
                        id='_' + slug, slug=slug, mdn_uri={'en': uri},
                        name=self.to_trans(title), parent=parent_id)
                    local_collection.add(feature)
                    feature_by_uri[uri] = feature
                    feature_by_slug[slug] = feature
        self.logger.info(
            'MDN URIs gathered, %d found (%d new, %d needs url, %d existing).',
            len(mdn_uris), new_page, needs_url, existing_page)

        return self.sync_changes(api_collection, local_collection)

    def to_trans(self, text):
        """Convert text to an API translatable string.

        If it looks canonical, convert to display in a <code></code> tag.
        If it looks like English, convert to display in <div></div> tag.
        """
        if ' ' in text:
            canonical = False
        elif text[0] in lowercase:
            canonical = True
        elif text[0] == '<' and text[-1] == ">":
            canonical = True
        elif text[0] == ':':
            canonical = True
        elif text[0].endswith("()"):
            canonical = True
        else:
            canonical = False
        if canonical:
            return escape(text)
        else:
            return {'en': escape(text)}

    def current_mdn_uris(self):
        """Load potential URIs from MDN."""
        base_paths = [
            'Web', 'Navigation_timing', 'Server-sent_events', 'WebAPI',
            'WebSockets']
        headers = {'Accept': 'application/json'}

        data = []
        for base_path in base_paths:
            cache_file = base_path + "_mdn_children.json"
            mdn_uri = self.base_mdn_uri + base_path + '$children'
            children = self.cached_download(
                cache_file, mdn_uri, headers=headers, retries=60)
            data.extend(self.gather_mdn_json(loads(children)))
        return data

    def known_features(self, collection):
        """Load URIs from collection's features."""
        uris = []
        for feature in collection.get_resources('features'):
            uri = feature.mdn_uri and feature.mdn_uri.get('en')
            slug = feature.slug
            uris.append((uri, slug, feature))
        return uris

    def gather_mdn_json(self, mdn_json, parent_path=None):
        """Recursively gather data from MDN JSON."""
        path = mdn_json['url']
        title = mdn_json['title']
        slug = mdn_json['slug']
        subpages = mdn_json['subpages']
        data = [(path, parent_path, slug, title)]
        for subjson in subpages:
            data.extend(self.gather_mdn_json(subjson, path))
        return data

    def rate_limit(self):
        """Pause and return True if exceeding the rate limit."""
        self.rate_limit_requests += 1

        # Sleep if we need to wait for the rate limit
        current_time = time.time()
        if self.rate:
            elapsed = current_time - self.rate_limit_start
            target = (
                self.rate_limit_start +
                float(self.rate_limit_requests) / self.rate)
            current_rate = float(self.rate_limit_requests) / elapsed
            if current_time < target:
                rest = int(target - current_time) + 1
                self.logger.warning(
                    "%d pages fetched, %0.2f per second, target rate %d per"
                    " second.  Resting %d seconds.",
                    self.rate_limit_requests, current_rate, self.rate, rest)
                time.sleep(rest)
                return True
        return False


if __name__ == '__main__':
    tool = MirrorMDNFeatures()
    tool.init_from_command_line()
    tool.logger.info("Loading data into {tool.api}...".format(tool=tool))
    changes = tool.run()
    tool.report_changes(changes)
