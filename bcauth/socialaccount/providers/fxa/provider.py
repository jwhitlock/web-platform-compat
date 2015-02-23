from allauth.socialaccount import providers
from allauth.socialaccount.providers.fxa.provider import (
    FirefoxAccountsProvider as BaseProvider,
    FirefoxAccountsAccount as BaseAccount)


class FirefoxAccountsAccount(BaseAccount):
    def get_profile_url(self):
        return 'https://latest.dev.lcip.org/profile/v1/profile'
        return self.account.uid
        return None

    def get_avatar_url(self):
        return None


class FirefoxAccountsProvider(BaseProvider):
    package = 'bcauth.socialaccount.providers.fxa'
    account_class = FirefoxAccountsAccount


providers.registry.register(FirefoxAccountsProvider)
