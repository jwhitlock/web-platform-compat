#!/usr/bin/env python
"""Generate raw HTTP requests/responses for API."""
from __future__ import unicode_literals, print_function
from collections import OrderedDict
from difflib import ndiff
from io import open
from urlparse import urlparse
import json
import logging
import os
import re

import requests

my_dir = os.path.dirname(os.path.realpath(__file__))
doc_dir = os.path.realpath(os.path.join(my_dir, '..', 'docs'))
default_api = 'http://localhost:8000'
default_cases_file = os.path.realpath(os.path.join(doc_dir, 'doc_cases.json'))
default_raw_dir = os.path.realpath(os.path.join(doc_dir, 'raw'))


class CaseRunner(object):
    """Run integration test cases."""

    doc_hostname = "browsercompat.org"
    doc_base_url = "https://browsercompat.org"
    default_status = {
        'GET': 200,
        'POST': 201,
        'PUT': 200,
        'DELETE': 204
    }
    doc_csrf = "p7FqFyNp6hZS0FJYKyQxVmLrZILldjqn"
    doc_session = "wurexa2wq416ftlvd5plesngwa28183h"
    modification_methods = ('PUT', 'PATCH', 'DELETE', 'POST')

    def __init__(
            self, cases=None, api=None, raw_dir=None, mode=None,
            username=None, password=None):
        self.cases = cases or default_cases_file
        self.api = api or default_api
        self.raw_dir = raw_dir or default_raw_dir
        self.mode = mode or "verify"
        assert self.mode in ("verify", "display", "generate"), "Invalid mode"
        self.handler = getattr(self, self.mode)
        self.standardize = self.mode in ("verify", "generate")
        self.username = username
        self.password = password
        self._user_session = None
        self.csrftoken = None
        self.sessionid = None

    def uri(self, endpoint):
        return self.api + "/api/v1/" + endpoint

    @property
    def user_session(self):
        if not self._user_session:
            assert (self.username and self.password), (
                "Must set a username and password")
            session = requests.Session()
            next_path = "/api/v1/browsers"

            # Get login page
            params = {'next': next_path}
            url = self.api + '/api-auth/login/'
            response = session.get(url, params=params)
            response.raise_for_status()
            csrf = response.cookies['csrftoken']

            # Post user credentials
            data = {
                'username': self.username,
                'password': self.password,
                'csrfmiddlewaretoken': csrf,
                'next': next_path
            }
            session.headers['referer'] = url
            response = session.post(
                self.api + '/api-auth/login/', params=params, data=data)
            if response.url == self.api + next_path:
                self._user_session = session
                self.csrftoken = session.cookies.get('csrftoken')
                self.sessionid = session.cookies.get('sessionid')
            else:
                raise Exception('Problem logging in.', response)
        return self._user_session

    def run(self, casenames=None, include_mod=None):
        """Run all documentation cases against the API."""
        if include_mod is None:
            include_mod = (self.mode != 'display')
        success, failure, skipped = 0, 0, 0
        for casenum, case in enumerate(self.cases):
            if casenames and case['name'] not in casenames:
                continue
            if case['method'] in self.modification_methods and not include_mod:
                continue
            if case.get('skip'):
                skipped += 1
                header = "SKIPPED Test Case %d: %s" % (casenum, case['name'])
                print()
                print(header)
                print("*" * len(header))
                print(case['skip'])
                continue

            response = self.request_case(casenum, case)
            issues = self.handler(casenum, case, response)
            if issues:
                failure += 1
                header = "Test Case %d: %s" % (casenum, case['name'])
                print()
                print(header)
                print("*" * len(header))
                for num, issue in enumerate(issues):
                    if num != 0:
                        print()
                    print(issue)
            else:
                success += 1
        return success, failure, skipped

    def request_case(self, casenum, case):
        """Run a documentation case against the API."""
        # Anonymous or authenticated session?
        is_mod_request = case['method'].upper() in self.modification_methods
        needs_user = case.get('user', is_mod_request)
        if needs_user:
            session = self.user_session
        else:
            session = requests

        # Setup request
        requester = getattr(session, case['method'].lower())
        full_uri = self.uri(case['endpoint'])
        kwargs = {'allow_redirects': False}

        # Setup headers
        headers = {}
        accept = case.get('accept', 'application/vnd.api+json')
        if accept:
            headers['accept'] = accept
        if is_mod_request and self.csrftoken:
            headers['X-CSRFToken'] = self.csrftoken
        if headers:
            kwargs['headers'] = headers

        # Add POST data
        if case.get('data'):
            content_type = case.get(
                'content_type', 'application/vnd.api+json')
            if content_type == 'application/x-www-form-urlencoded':
                kwargs['data'] = case['data']
            else:
                headers['Content-Type'] = content_type
                kwargs['data'] = json.dumps(
                    case['data'], indent=4, separators=(",", ": "))

        # Make request
        response = requester(full_uri, **kwargs)
        return response

    def display(self, casenum, case, response):
        """Display a requests response."""
        out = self.format_response_for_display(response, case)
        header = "Test Case %d: %s" % (casenum, case['name'])
        print()
        print(header)
        print("*" * len(header))
        print(out)
        return []

    def generate(self, casenum, case, response):
        """Generate the documentation version of the case."""
        for phase, stype, path, section in self.case_sections(case, response):
            if section:
                section = self.ensure_ending_newline(section)
                with open(path, 'w', encoding='utf8') as out:
                    out.write(section)
            elif os.path.exists(path):
                os.remove(path)
        status_issue = self.check_status(case, response)
        if status_issue:
            return [status_issue]
        else:
            return []

    def verify(self, casenum, case, response):
        """Verify the response matches the documentation."""
        issues = []
        for phase, stype, path, section in self.case_sections(case, response):
            if os.path.exists(path):
                with open(path, 'r', encoding='utf8') as doc:
                    expected = doc.read()
                expected = self.ensure_ending_newline(expected)
                if section:
                    actual = self.ensure_ending_newline(section)
                else:
                    actual = ""
                if expected != actual:
                    expected_lines = expected.splitlines(1)
                    actual_lines = actual.splitlines(1)
                    diff = ''.join(ndiff(expected_lines, actual_lines))
                    issues.append(
                        "Difference in %s %s\n%s" % (phase, stype, diff))
        status_issue = self.check_status(case, response)
        if status_issue:
            issues.append(status_issue)
        return issues

    def case_sections(self, case, response):
        """Generate the documentation case, section by section

        Yields a tuple:
        phase - 'request' or 'response'
        section_type - 'headers' or 'body'
        path - Path to the file with expected contents
        section - The formatted section from the live test
        """
        formatted = self.format_response_for_docs(response, case)
        base_path = os.path.join(self.raw_dir, case['name'])
        for phase in ('request', 'response'):
            is_json = (
                'Content-Type: application/vnd.api+json' in
                formatted[phase].get('headers', ''))
            for section_type in ('headers', 'body'):
                ext = 'json' if (section_type == 'body' and is_json) else 'txt'
                path = base_path + '-%s-%s.%s' % (phase, section_type, ext)
                section = formatted[phase][section_type]
                yield phase, section_type, path, section

    def ensure_ending_newline(self, text):
        """Add an ending newline, if needed."""
        if text and text[-1] != '\n':
            return text + '\n'
        else:
            return text

    def check_status(self, case, response):
        method = case['method']
        expected_status = case.get('status', self.default_status[method])
        actual_status = response.status_code
        if actual_status != expected_status:
            return (
                "Status code %s does not match %s:\n%s" % (
                    actual_status, expected_status, response.text))

    def format_response_for_docs(self, response, case):
        """Format a requests response for documentation."""
        parsed = self.parse_response(response, case)
        formatted = {
            "request": {"body": parsed['request']['body']},
            "response": {"body": parsed['response']['body']}
        }

        request = parsed['request']
        headers = request['request_line']
        if request['headers']:
            headers += "\n" + "\n".join(
                "%s: %s" % pair for pair in request['headers'].items())
        formatted['request']['headers'] = headers

        response = parsed['response']
        headers = response['response_line']
        if response['headers']:
            headers += "\n" + "\n".join(
                "%s: %s" % pair for pair in response['headers'].items())
        formatted['response']['headers'] = headers

        for phase in ('request', 'response'):
            for part in ('headers', 'body'):
                if (formatted[phase][part] and
                        not formatted[phase][part].endswith('\n')):
                    formatted[phase][part] += '\n'

        return formatted

    def format_response_for_display(self, response, case):
        """Format a requests response for display."""
        out_bits = []
        parsed = self.parse_response(response, case)

        request = parsed['request']
        out_bits.append(request['request_line'])
        for header, value in request['headers'].items():
            out_bits.append("%s: %s" % (header, value))
        if request['body']:
            out_bits.extend(("", request['body']))

        out_bits.extend([''] * 2)

        response = parsed['response']
        out_bits.append(response['response_line'])
        for header, value in response['headers'].items():
            out_bits.append("%s: %s" % (header, value))
        if response['body']:
            out_bits.extend(("", response['body']))

        return "\n".join(out_bits)

    def parse_response(self, response, case):
        """Parse and reformat a requests response."""
        request = response.request
        parsed = {
            'request': {
                'method': request.method,
                'url': request.url,
                'body': request.body,
            },
            'response': {
                'headers': OrderedDict(),
                'status_code': response.status_code,
                'reason': response.reason,
            }
        }

        # Re-assemble request line
        url_parts = urlparse(request.url)
        parsed['request']['request_line'] = "%s %s%s%s HTTP/1.1" % (
            request.method, url_parts.path, '?' if url_parts.query else '',
            url_parts.query)

        # Process request headers
        if self.mode == 'display':
            hostname = url_parts.hostname
        else:
            hostname = self.doc_hostname
        parsed['request']['headers'] = OrderedDict((('Host', hostname),))
        for header in sorted([h.title() for h in request.headers]):
            raw_value = request.headers[header]
            value = self.parse_header(header, raw_value, "request")
            if value:
                parsed['request']['headers'][header.title()] = value

        # Re-assemble response line
        parsed['response']['response_line'] = "HTTP/1.1 %s %s" % (
            response.status_code, response.reason)

        # Process response headers
        for header in sorted([h.title() for h in response.headers]):
            raw_value = response.headers[header]
            value = self.parse_header(header, raw_value, "response")
            if value:
                parsed['response']['headers'][header.title()] = value

        # Process response body
        body = response.text
        if self.standardize:
            body = body.replace(api, self.doc_base_url)
            for key, value in case.get('standardize', {}).items():
                assert key in ('created', 'modified', 'date')
                pattern = r"""(?x)(?s)  # Be verbose, . include newlines
                    "%s":\s"            # Key and quote
                    \d{4}-\d{2}-\d{2}   # Date
                    T\d{2}:\d{2}:\d{2}  # Time
                    \.\d{0,6}Z          # Microseconds and UTC timezone
                    ",                  # End quote and comma
                    """ % key
                replace = '"%s": "%s",' % (key, value)
                body = re.sub(pattern, replace, body)
        parsed['response']['body'] = body

        return parsed

    def parse_header(self, header, value, phase):
        """Modify or drop headers if in documentation mode."""
        if self.mode == 'display':
            return value
        if phase == 'request':
            if header.lower() == 'accept':
                return value if value != "*/*" else None
            elif header.lower() == 'x-csrftoken':
                if self.csrftoken:
                    value = value.replace(self.csrftoken, self.doc_csrf)
                return value
            elif header.lower() == 'cookie':
                if self.csrftoken:
                    value = value.replace(self.csrftoken, self.doc_csrf)
                if self.sessionid:
                    value = value.replace(self.sessionid, self.doc_session)
                return "; ".join(sorted(value.split('; ')))
            elif header.lower() in ('content-type', 'content-length'):
                return value
            elif header.lower() not in (
                    'accept-encoding', 'connection', 'user-agent', 'referer'):
                print("Unexpected request header %s: %s", header, value)
                return value
        else:
            if header.lower() == 'content-type':
                return value
            elif header.lower() not in (
                    'allow', 'date', 'server', 'vary', 'x-frame-options',
                    'content-length'):
                print("Unexpected response header %s: %s", header, value)
                return value


if __name__ == '__main__':
    import argparse
    import getpass
    import sys

    description = 'Make raw requests to API'
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        'casenames', metavar="case name", nargs="*",
        help='Case names to run, defaults to all cases')
    parser.add_argument(
        '-a', '--api', default=default_api,
        help='Base URL of the API (default: http://localhost:8000)')
    parser.add_argument(
        '-r', '--raw', default=default_raw_dir,
        help="Path to requests/responses folder")
    parser.add_argument(
        '-c', '--cases', default=default_cases_file,
        help="Path to cases JSON")
    parser.add_argument(
        '-v', '--verbose', action="store_true",
        help='Print extra debug information')
    parser.add_argument(
        '-q', '--quiet', action="store_true",
        help='Only print warnings')
    parser.add_argument(
        '-m', '--mode', choices=("display", "generate", "verify"),
        default="display",
        help="Run test cases in the specified mode, default display")
    parser.add_argument(
        '-u', '--user',
        help="Regular user to use for API requests")
    parser.add_argument(
        '-p', '--password',
        help="Password to use for regular user")
    parser.add_argument(
        '--include-mod', action="store_true",
        help="In display mode, include cases that modify data")

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
    mode = args.mode
    logger.info("Making API requests against %s for %s", api, mode)
    if mode == 'display':
        include_mod = args.include_mod
    else:
        include_mod = True

    if args.user and not args.password:
        password = getpass.getpass("API password: ")
    else:
        password = args.password

    # Load data
    with open(args.cases, 'r', encoding='utf8') as cases_file:
        cases = json.load(cases_file, object_pairs_hook=OrderedDict)
    runner = CaseRunner(
        cases=cases, api=api, raw_dir=args.raw, mode=mode,
        username=args.user, password=password)
    success, failure, skipped = runner.run(args.casenames, include_mod)

    if skipped:
        skip_msg = " (%d skipped)" % skipped
    else:
        skip_msg = ""
    if not (success or failure):
        logger.info("No requests made%s.", skip_msg)
    if success and not failure:
        logger.info("Requests complete, %d passed%s.", success, skip_msg)
    else:
        logger.info(
            "Requests complete, %d failed, %d passed%s.",
            failure, success, skip_msg)
        sys.exit(1)
