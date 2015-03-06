"""
WSGI config for wpcsite project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/howto/deployment/wsgi/
"""

import os
try:
    from django.core.wsgi import get_wsgi_application
except ImportError:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "wpcsite.settings")
    from django.core.wsgi import get_wsgi_application

from dj_static import Cling
application = Cling(get_wsgi_application())
