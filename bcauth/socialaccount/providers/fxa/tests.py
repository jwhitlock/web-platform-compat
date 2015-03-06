"""Tests for FirefoxAccounts.

Uses the testing infrastructure from django-allauth.
"""

from allauth.socialaccount.tests import create_oauth2_tests
from allauth.tests import MockedResponse
from allauth.socialaccount.providers import registry

from .provider import FirefoxAccountsProvider

# Setup base class but omit from nose tests
create_oauth2_tests.__test__ = False
base_class = create_oauth2_tests(
    registry.by_id(FirefoxAccountsProvider.id))
base_class.__test__ = False


class FirefoxAccountsTest(base_class):
    __test__ = True  # Include in nose tests

    def get_mocked_response(self):
        return MockedResponse(200, """
        {
            "uid":"6d940dd41e636cc156074109b8092f96",
            "email":"user@example.domain"
        }""")
