"""
Django settings for wpcsite project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/

Designed for Heroku and http://12factor.net/config.  Configuration is
overriden by environment variables.

One way to set environment variables for local development in a virtualenv:

$ vi $VIRTUAL_ENV/bin/postactivate
export DJANGO_DEBUG=1
$ vi $VIRTUAL_ENV/bin/predeactivate
unset DJANGO_DEBUG
$ source $VIRTUAL_ENV/bin/postactivate

A second way to to use autoenv and a .env file.  See env.dist.

To set environment variables in heroku environment
$ heroku config
$ heroku config:set DJANGO_DEBUG=1

Environment variables:
ADMIN_NAMES, ADMIN_EMAILS - comma-separted list of names and emails of admins
ALLOWED_HOSTS - comma-separated list of allowed hosts
DATABASE_URL - See https://github.com/kennethreitz/dj-database-url
DEFAULT_FROM_EMAIL - "From" email for emails to users
DJANGO_DEBUG - 1 to enable, 0 to disable, default disabled
EMAIL_BACKEND - The backend for email services
EMAIL_FILE_PATH - File path when FileSystemStorage is used
EMAIL_HOST - SMTP server, default localhost
EMAIL_HOST_PASSWORD - SMTP server password, default none
EMAIL_HOST_USER - SMTP server username, default none
EMAIL_PORT - SMTP server ports, default 25
EMAIL_SUBJECT_PREFIX - Prefix for subject line of emails to admins
EMAIL_USE_SSL - 1 to use SSL SMTP connection, usually on port 465
EMAIL_USE_TLS - 1 to use TLS SMTP connection, usually on port 587
EXTRA_INSTALLED_APPS - comma-separated list of apps to add to INSTALLED_APPS
FXA_OAUTH_ENDPOINT - Override for Firefox Account OAuth2 endpoint
FXA_PROFILE_ENDPOINT - Override for Firefox Account profile endpoint
MDN_ALLOWED_URL_PREFIXES - comma-separated list of URL prefixes allowed by
  the scraper
MEMCACHE_SERVERS - semicolon-separated list of memcache servers
MEMCACHE_USERNAME - username for memcache servers
MEMCACHE_PASSWORD - password for memcache servers
USE_DRF_INSTANCE_CACHE - 1 to enable, 0 to disable, default enabled
DRF_INSTANCE_CACHE_POPULATE_COLD - 1 to recursively populate a cold cache on
  updates, 0 to be eventually consistent, default enabled
SECRET_KEY - Overrides SECRET_KEY
SECURE_PROXY_SSL_HEADER - "HTTP_X_FORWARDED_PROTOCOL,https" to enable
SERVER_EMAIL - Email 'From' address for error messages to admins
STATIC_ROOT - Overrides STATIC_ROOT

"""

# Build paths inside the project like this: rel_path('folder', 'file')
from os import environ, path
import sys
import dj_database_url

BASE_DIR = path.dirname(path.dirname(__file__))


def rel_path(*subpaths):
    return path.join(BASE_DIR, *subpaths)


# Detect that we're running tests
TESTING = sys.argv[1:2] == ['test']


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = environ.get(
    'SECRET_KEY', 'jl^8zustdy8ht@=abml-j@%hp7hr-0u-41hb*1=duc91a%=9+%')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = environ.get("DJANGO_DEBUG", '0') in (1, '1')
TEMPLATE_DEBUG = DEBUG

ALLOWED_HOSTS = environ.get('ALLOWED_HOSTS', '').split(',')
if environ.get('SECURE_PROXY_SSL_HEADER'):
    raw = environ['SECURE_PROXY_SSL_HEADER']
    SECURE_PROXY_SSL_HEADER = tuple(raw.split(','))

AUTHENTICATION_BACKENDS = (
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
)

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'corsheaders',
    'django_extensions',
    'django_nose',
    'mptt',
    'simple_history',
    'rest_framework',
    'sortedm2m',

    'bcauth',
    'bcauth.socialaccount.providers.fxa',
    'mdn',
    'webplatformcompat',
]
if environ.get('EXTRA_INSTALLED_APPS'):
    INSTALLED_APPS + environ['EXTRA_INSTALLED_APPS'].split(',')

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'corsheaders.middleware.CorsPostCsrfMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'webplatformcompat.history.HistoryChangesetRequestMiddleware',
)

ROOT_URLCONF = 'wpcsite.urls'

WSGI_APPLICATION = 'wpcsite.wsgi.application'

# django-allauth requires some settings
SITE_ID = int(environ.get('SITE_ID', '1'))

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.request",
    "django.contrib.messages.context_processors.messages",
)

# Email settings
if 'ADMIN_NAMES' in environ and 'ADMIN_EMAILS' in environ:
    names = [x.strip() for x in environ['ADMIN_NAMES'].split(',')]
    emails = [x.strip() for x in environ['ADMIN_EMAILS'].split(',')]
    ADMINS = zip(names, emails)
if 'EMAIL_BACKEND' in environ:
    EMAIL_BACKEND = environ['EMAIL_BACKEND']
if 'EMAIL_HOST' in environ:
    EMAIL_HOST = environ['EMAIL_HOST']
if 'EMAIL_PORT' in environ:
    EMAIL_PORT = environ['EMAIL_PORT']
if 'EMAIL_HOST_USER' in environ:
    EMAIL_HOST_USER = environ['EMAIL_HOST_USER']
if 'EMAIL_HOST_PASSWORD' in environ:
    EMAIL_HOST_PASSWORD = environ['EMAIL_HOST_PASSWORD']
if 'EMAIL_USE_TLS' in environ:
    EMAIL_USE_TLS = (environ['EMAIL_USE_TLS'] in (1, "1"))
if 'EMAIL_USE_SSL' in environ:
    EMAIL_USE_SSL = (environ['EMAIL_USE_SSL'] in (1, "1"))
if 'EMAIL_SUBJECT_PREFIX' in environ:
    EMAIL_SUBJECT_PREFIX = environ['EMAIL_SUBJECT_PREFIX']
if 'SERVER_EMAIL' in environ:
    SERVER_EMAIL = environ['SERVER_EMAIL']
if 'DEFAULT_FROM_EMAIL' in environ:
    DEFAULT_FROM_EMAIL = environ['DEFAULT_FROM_EMAIL']
if 'EMAIL_FILE_PATH' in environ:
    EMAIL_FILE_PATH = environ['EMAIL_FILE_PATH']

# Prefer our template folders to rest_framework's, allauth's
TEMPLATE_DIRS = (
    rel_path('bcauth', 'templates'),
    rel_path('webplatformcompat', 'templates'),
)

# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases

DATABASES = {
    'default':
        dj_database_url.config(default='sqlite:///' + rel_path('db.sqlite3'))
}

# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/
if environ.get('STATIC_ROOT'):
    STATIC_ROOT = environ['STATIC_ROOT']
STATIC_URL = '/static/'

#
# Caching
#
# In Heroku, use MemCachier and load from environment
# https://devcenter.heroku.com/articles/django-memcache
# Otherwise, use django-pylibmc environment variables or locmen
# https://github.com/jbalogh/django-pylibmc

# In Heroku, load Memcachier settings into django-pylibmc
if environ.get('MEMCACHIER_SERVERS'):
    environ['MEMCACHE_SERVERS'] = environ.get(
        'MEMCACHIER_SERVERS', '').replace(',', ';')
if environ.get('MEMCACHIER_USERNAME'):
    environ['MEMCACHE_USERNAME'] = environ.get('MEMCACHIER_USERNAME', '')
if environ.get('MEMCACHIER_PASSWORD'):
    environ['MEMCACHE_PASSWORD'] = environ.get('MEMCACHIER_PASSWORD', '')

if environ.get('MEMCACHE_SERVERS') and not TESTING:
    # Use memcache
    CACHES = {
        'default': {
            'BACKEND': 'django_pylibmc.memcached.PyLibMCCache',
            'TIMEOUT': 500,
            'BINARY': True,
            'OPTIONS': {
                'no_block': True,
                'tcp_nodelay': True,
                'tcp_keepalive': True,
                'remove_failed': 4,
                'retry_timeout': 2,
                'dead_timeout': 10,
                '_poll_timeout': 2000,
            },
        },
    }
else:
    # Use local cache
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        },
    }
SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"

# When the number of descendants means to paginate a view_feature
PAGINATE_VIEW_FEATURE = 50

# Authentication
LOGIN_URL = '/accounts/login/'

# MDN Scraping
if environ.get('MDN_ALLOWED_URL_PREFIXES') and not TESTING:
    raw = environ['MDN_ALLOWED_URL_PREFIXES']
    MDN_ALLOWED_URLS = tuple(raw.split(','))
else:
    MDN_ALLOWED_URLS = ('https://developer.mozilla.org/en-US/', )

#
# 3rd Party Libraries
#

# Jingo / Jinja2 templates
TEMPLATE_LOADERS = (
    'jingo.Loader',
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)
JINGO_INCLUDE_PATTERN = r'\.jinja2'

# Django REST Framework
REST_FRAMEWORK = {
    'DEFAULT_MODEL_SERIALIZER_CLASS':
        'rest_framework.serializers.HyperlinkedModelSerializer',
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.DjangoModelPermissionsOrAnonReadOnly',
    ],
    'VIEW_NAME_FUNCTION': 'webplatformcompat.utils.get_view_name',
    'DEFAULT_FILTER_BACKENDS': [
        'webplatformcompat.filters.UnorderedDjangoFilterBackend',
    ],
    'PAGINATE_BY': 10,
    'PAGINATE_BY_PARAM': 'page_size',
    'MAX_PAGINATE_BY': 100,
}

# Django nose
TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'

# Django Debug Toolbar
if DEBUG:
    try:
        import debug_toolbar
    except ImportError:
        pass
    else:
        assert debug_toolbar
        INSTALLED_APPS.append('debug_toolbar')

# Celery - async task management
CELERY_TASK_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ENABLE_UTC = True
CELERY_ALWAYS_EAGER = True
CELERY_EAGER_PROPAGATES_EXCEPTIONS = True

# DRF Cached Instances - avoid DB reads for Django REST Framework
USE_DRF_INSTANCE_CACHE = (
    environ.get('USE_DRF_INSTANCE_CACHE', '1') not in (0, '0'))
DRF_INSTANCE_CACHE_POPULATE_COLD = (
    environ.get('DRF_INSTANCE_CACHE_POPULATE_COLD', '1') not in (0, '0'))

# CORS Middleware
CORS_ORIGIN_ALLOW_ALL = True
CORS_ALLOW_CREDENTIALS = True

# django-allauth
SOCIALACCOUNT_PROVIDERS = {
    'fxa': {
        'OAUTH_ENDPOINT': environ.get(
            'FXA_OAUTH_ENDPOINT',
            'https://oauth.accounts.firefox.com/v1'),
        'PROFILE_ENDPOINT': environ.get(
            'FXA_PROFILE_ENDPOINT',
            'https://profile.accounts.firefox.com/v1'),
    }
}
