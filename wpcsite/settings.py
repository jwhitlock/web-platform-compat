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

To set environment variables in heroku environment
$ heroku config
$ heroku config:set DJANGO_DEBUG=1

Environment variables:
ALLOWED_HOSTS - comma-separated list of allowed hosts
DATABASE_URL - See https://github.com/kennethreitz/dj-database-url
DJANGO_DEBUG - 1 to enable, 0 to disable, default disabled
EXTRA_INSTALLED_APPS - comma-separated list of apps to add to INSTALLED_APPS
MEMCACHE_SERVERS - semicolon-separated list of memcache servers
MEMCACHE_USERNAME - username for memcache servers
MEMCACHE_PASSWORD - password for memcache servers
USE_INSTANCE_CACHE - 1 to enable, 0 to disable, default enabled
SECRET_KEY - Overrides SECRET_KEY
SECURE_PROXY_SSL_HEADER - "HTTP_X_FORWARDED_PROTOCOL,https" to enable
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

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'django_extensions',
    'django_nose',
    'mptt',
    'simple_history',
    'rest_framework',
    'sortedm2m',

    'drf_cached_reads',
    'webplatformcompat',
]
if environ.get('EXTRA_INSTALLED_APPS'):
    INSTALLED_APPS + environ['EXTRA_INSTALLED_APPS'].split(',')

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'simple_history.middleware.HistoryRequestMiddleware',
)

ROOT_URLCONF = 'wpcsite.urls'

WSGI_APPLICATION = 'wpcsite.wsgi.application'

# Prefer our template folder to rest_framework's
TEMPLATE_DIRS = (
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
USE_INSTANCE_CACHE = environ.get('USE_INSTANCE_CACHE', '1') not in (0, '0')
SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"


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
