============
Installation
============

Install Django Project
----------------------

1. Clone project locally
2. Create virtualenv
3. Install dependencies via pip
4. Customize with environment variables (see ``wpcsite/settings.py``)
5. Setup database, add superuser account (``./manage.py syncdb``)
6. Run it (``./manage.py runserver``)

Install in Heroku
-----------------

1. Clone project locally
2. ``heroku apps:create``
3. ``git push heroku master``
4. See current config with ``heroku config``, and customize with environment
   variables using ``heroku config:set`` (see ``wpcsite/settings.py``)
5. Add superuser account (``heroku run ./manage.py createsuperuser``)


Load Data
---------
To load sample data:

1. Run w/ instance cache (``USE_INSTANCE_CACHE=0 ./manage.py runserver``)
2. Load subset of webplatform_ data (``tools/load_webcompat_data.py``) or full
   set of data (``tools/load_webcompat.py --all-data``)
3. Load specification data (``tools/load_spec_data.py``)

.. _webplatform: https://github.com/webplatform/compatibility-data
