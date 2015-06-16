#!/usr/bin/env python
"""Client for accessing the API

This is a baby step toward a generally useful client.  As it matures, it may
grow features and get moved to its own repo.
"""

from __future__ import print_function, unicode_literals

from collections import OrderedDict
from json import dumps
from time import time
import logging

import requests

logger = logging.getLogger('tools.client')


class APIException(Exception):
    """Errors returned from API"""
    pass


class Client(object):
    """Client for talking to the web-platform-compat API."""

    def __init__(self, base_url):
        self.base_url = base_url
        self._session = None
        self.csrftoken = None
        self.changeset = None

    @property
    def session(self):
        """Return the session, creating if needed"""
        if not self._session:
            self._session = requests.Session()
        return self._session

    def url(self, resource_type, resource_id=None):
        """Build the URL for a resource."""
        url = self.base_url + '/api/v1/' + resource_type
        if resource_id:
            url += '/' + resource_id
        return url

    def request(
            self, method, resource_type, resource_id=None, params=None,
            data=None, json_params=None):
        """Request data from the API"""
        start = time()
        url = self.url(resource_type, resource_id)

        # Setup parameters
        params = params or {}
        headers = {'content-type': 'application/vnd.api+json'}
        modify_methods = ('PUT', 'PATCH')
        delete_methods = ('DELETE',)
        create_methods = ('POST',)
        change_methods = modify_methods + delete_methods + create_methods
        if method in change_methods and self.csrftoken:
            headers['X-CSRFToken'] = self.csrftoken
        if method in change_methods and self.changeset:
            params['changeset'] = self.changeset
        if method in create_methods:
            expected_statuses = [201]
        elif method in delete_methods:
            expected_statuses = [204, 404]
        else:
            expected_statuses = [200]
        if data:
            data_json = dumps(data)
        else:
            data_json = None

        # Make the request
        rfunc = getattr(self.session, method.lower())
        response = rfunc(url, params=params, data=data_json, headers=headers)
        if response.status_code not in expected_statuses:
            raise APIException(
                '%s %s: Unexpected response' % (method, url),
                response.status_code, response.content)

        end = time()
        logger.debug('%s %s completed in %0.1fs', method, url, end - start)
        kwargs = json_params or {}
        try:
            return response.json(**kwargs)
        except ValueError:
            # 204 Gone is empty, maybe others
            return response.text

    def login(self, user, password, next_path='/api/v1/browsers'):
        """Log into the API."""
        # Get login page
        params = {'next': next_path}
        url = self.base_url + '/api-auth/login/'
        response = self.session.get(url, params=params)
        csrf = response.cookies['csrftoken']

        # Post user credentials
        data = {
            'username': user,
            'password': password,
            'csrfmiddlewaretoken': csrf,
            'next': next_path
        }
        self.session.headers['referer'] = url
        response = self.session.post(
            self.base_url + '/api-auth/login/', params=params, data=data)
        if response.url == self.base_url + next_path:
            logger.info("Logged into " + self.base_url)
            self.csrftoken = self.session.cookies['csrftoken']
        else:
            raise Exception('Problem logging in.', response)

    def open_changeset(self):
        """Open a changeset for multiple items"""
        assert not self.changeset, 'A changeset is already open!'
        response = self.create('changesets', {})
        self.changeset = response['id']

    def close_changeset(self):
        """Close a changeset for multiple items"""
        assert self.changeset, 'There is no open changeset!'
        data = {'changesets': {'closed': True}}
        self.request('PUT', 'changesets', self.changeset, data=data)
        self.changeset = None

    def count(self, resource_type):
        """Return the current count for a resource type"""
        response = self.request('GET', resource_type)
        return response['meta']['pagination'][resource_type]['count']

    def create(self, resource_type, resource):
        """Create a resource in the API

        Keyword arguments:
        resource_type -- resource name, such as 'browsers'
        resource -- data as a Resource or Python dict, such as: {'slug': 'foo'}

        The return is a Python dict, such as: {'id': 1, 'slug': 'foo'}
        On failure, an APIException is raised.
        """
        data = {resource_type: resource}
        response = self.request('POST', resource_type, data=data)
        return response[resource_type]

    def update(self, resource_type, resource_id, resource):
        """Update a resource in the API

        Keyword arguments:
        resource_type -- resource name, such as 'browsers'
        resource_id -- resource ID
        resource -- data as a Resource or Python dict, such as: {'slug': 'foo'}

        The return is a Python dict, such as: {'id': 1, 'slug': 'foo'}
        On failure, an APIException is raised.
        """
        data = {resource_type: resource}
        response = self.request('PUT', resource_type, resource_id, data=data)
        return response[resource_type]

    def delete(self, resource_type, resource_id):
        """Delete a resource in the API

        Keyword arguments:
        resource_type -- resource name, such as 'browsers'
        resource_id -- resource ID

        The return is a Python dict, such as: {'id': 1, 'slug': 'foo'}
        On failure, an APIException is raised.
        """
        response = self.request('DELETE', resource_type, resource_id)
        # Response is empty, but return it.
        return response

    def get_resource_collection(self, resource_type, log_at=15):
        """Get all the resources of a type as a single JSON API response.

        Keyword arguments:
        resource_type -- resource name, such as 'browsers'
        log_at -- Every (log_at) seconds, log download progress. Set to a
        negative number to disable.
        """
        data = None
        next_url = True
        page = 0
        count = None
        total = None
        last_time = time()
        while next_url:
            page += 1
            current_time = time()
            if data and log_at >= 0 and (current_time - last_time) > log_at:
                count = float(len(data[resource_type]))
                percent = int(100 * (count / total))
                logger.info(
                    "  Loaded %d of %d %s (%d%%)...",
                    count, total, resource_type, percent)
                last_time = current_time
            params = {'page': page}
            response = self.request(
                'GET', resource_type, params=params,
                json_params={'object_pairs_hook': OrderedDict})
            assert resource_type in response
            if data:
                data[resource_type].extend(response[resource_type])
            else:
                data = response.copy()
                total = data['meta']['pagination'][resource_type]['count']
            next_url = response['meta']['pagination'][resource_type]['next']
        data['meta']['pagination'][resource_type]['previous'] = None
        data['meta']['pagination'][resource_type]['next'] = None
        return data


if __name__ == "__main__":
    from math import log10, trunc
    from common import ToolParser

    parser = ToolParser(
        description='Demo client with resource count', include=['api'],
        logger=logger)

    args = parser.parse_args()
    api = args.api
    logger.info("Counting resources on %s" % api)

    client = Client(api)
    resources = [
        'browsers', 'versions', 'features', 'supports', 'specifications',
        'maturities', 'sections', 'users']
    count = {}
    for r in resources:
        count[r] = client.count(r)

    max_resource_len = max([len(r) for r in resources])
    max_count = max(count.values())
    if max_count:
        max_count_len = trunc(log10(max(count.values()))) + 1
    else:
        max_count_len = 1
    for r in resources:
        print('{0:>{1}}: {2!s:>{3}}'.format(
            r, max_resource_len, count[r], max_count_len))
