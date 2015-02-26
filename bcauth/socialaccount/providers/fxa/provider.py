from allauth.socialaccount import providers
from allauth.socialaccount.providers.fxa.provider import (
    FirefoxAccountsProvider as BaseProvider)


class FirefoxAccountsProvider(BaseProvider):
    package = 'bcauth.socialaccount.providers.fxa'


providers.registry.register(FirefoxAccountsProvider)
