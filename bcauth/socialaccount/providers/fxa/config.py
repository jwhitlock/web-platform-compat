"""Configuration for the Firefox Accounts provider"""


def fxa_config():
    from django.conf import settings

    PROVIDERS = getattr(settings, 'SOCIALACCOUNT_PROVIDERS', {})
    fxa = PROVIDERS.get('fxa', {})
    oauth_endpoint = fxa.get(
        'OAUTH_ENDPOINT', 'https://oauth.accounts.firefox.com/v1')
    profile_endpoint = fxa.get(
        'PROFILE_ENDPOINT', 'https://profile.accounts.firefox.com/v1/profile')
    return {
        'access_token_url': oauth_endpoint + '/token',
        'authorize_url': oauth_endpoint + '/authorization',
        'profile_url': profile_endpoint + '/profile',
    }
