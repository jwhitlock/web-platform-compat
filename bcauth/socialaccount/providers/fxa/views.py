from allauth.socialaccount.providers.fxa.views import \
    FirefoxAccountsOAuth2Adapter as BaseAdapter
from allauth.socialaccount.providers.fxa.provider import \
    FirefoxAccountsProvider
from allauth.socialaccount.providers.oauth2.views import (
    OAuth2Client, OAuth2LoginView, OAuth2CallbackView, OAuth2View)


def _config():
    # TODO: Move these to env variables
    oauth_endpoint = 'https://oauth.accounts.firefox.com/v1'
    profile_endpoint = 'https://profile.accounts.firefox.com/v1'
    oauth_endpoint = 'https://oauth-latest.dev.lcip.org/v1'
    profile_endpoint = 'https://latest.dev.lcip.org/profile/v1'
    abs_uri = "https://browsercompat.herokuapp.com"
    return {
        'access_token_url': oauth_endpoint + '/token',
        'authorize_url': oauth_endpoint + '/authorization',
        'profile_url': profile_endpoint + '/profile',
        'abs_uri': abs_uri,
    }


class FirefoxAccountsOAuth2Adapter(BaseAdapter):
    provider_id = FirefoxAccountsProvider.id

    @property
    def redirect_uri_protocol(self):
        abs_uri = _config()['abs_uri']
        return abs_uri.split(':')[0]

    @property
    def access_token_url(self):
        return _config()['access_token_url']

    @property
    def authorize_url(self):
        return _config()['authorize_url']

    @property
    def profile_url(self):
        return _config()['profile_url']


# TODO: Remove these placeholders if unused
class FirefoxAccountOAuth2Client(OAuth2Client):
    pass


class FirefoxAccountView(OAuth2View):
    pass


class FirefoxAccountLoginView(FirefoxAccountView, OAuth2LoginView):
    pass


class FirefoxAccountCallbackView(FirefoxAccountView, OAuth2CallbackView):
    pass


oauth2_login = FirefoxAccountLoginView.adapter_view(
    FirefoxAccountsOAuth2Adapter)
oauth2_callback = FirefoxAccountCallbackView.adapter_view(
    FirefoxAccountsOAuth2Adapter)
