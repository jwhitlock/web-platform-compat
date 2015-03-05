from allauth.socialaccount.providers.fxa.views import \
    FirefoxAccountsOAuth2Adapter as BaseAdapter
from allauth.socialaccount.providers.fxa.provider import \
    FirefoxAccountsProvider
from allauth.socialaccount.providers.oauth2.views import (
    OAuth2LoginView, OAuth2CallbackView)

from .config import fxa_config


class FirefoxAccountsOAuth2Adapter(BaseAdapter):
    provider_id = FirefoxAccountsProvider.id

    @property
    def access_token_url(self):
        return fxa_config()['access_token_url']

    @property
    def authorize_url(self):
        return fxa_config()['authorize_url']

    @property
    def profile_url(self):
        return fxa_config()['profile_url']


oauth2_login = OAuth2LoginView.adapter_view(FirefoxAccountsOAuth2Adapter)
oauth2_callback = OAuth2CallbackView.adapter_view(FirefoxAccountsOAuth2Adapter)
