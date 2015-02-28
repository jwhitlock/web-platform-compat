============
Installation
============

Install Django Project
----------------------
For detailed local instation instructions, including OS-specific
instructions, see the `Installation page on the wiki`_.

1. Install system packages and libraries.  The required packages are
   Python_ (2.7, 3.4, or both),
   pip_ (latest), and
   virtualenv_ (latest).
   To match production and for a smooth installation of Python packages,
   install
   PostgreSQL_ (9.2 or later recommended) and
   Memcached_ (latest).
   virtualenvwrapper_ and autoenv_ will make your development life easier.
2. Optionally, provision a PostgreSQL database, recommended to match
   production.  The default Django database settings will use a
   SQLite_ database named ``db.sqlite3``.
3. Optionally, run Memcached_ for improved read performance and to match
   production.  The default settings will run without a cache.
4. `Clone project locally`_.
5. `Create a virtualenv`_.
6. Install dependencies with
   ``pip install -r requirements.txt -r requirements.dev.txt``.
7. Customize the configuration with environment variables.
   See ``wpcsite/settings.py`` and ``env.dist`` for advice and available
   settings.
8. Initialize the database and a superuser account with
   ``./manage.py migrate``.
9. Verify that tests pass with ``./manage,py test`` or ``make test``.
10. Run it with ``./manage.py runserver`` or ``./manage.py runserver_plus``.

.. _Installation page on the wiki: 
.. _Python: https://www.python.org
.. _pip: https://pip.pypa.io/en/latest/
.. _virtualenv: https://virtualenv.pypa.io/en/latest/
.. _PostgreSQL: http://www.postgresql.org
.. _Memcached: http://memcached.org
.. _memcached: http://memcached.org
.. _virtualenvwrapper: http://virtualenvwrapper.readthedocs.org/en/latest/
.. _autoenv: https://github.com/kennethreitz/autoenv
.. _`Create a virtualenv`: https://virtualenv.pypa.io/en/latest/userguide.html
.. _SQLite: http://sqlite.org


Install in Heroku
-----------------

Heroku_ allows you to quickly deploy web-platform-compat.  Heroku hosts
the beta version of the service at https://browsercompat.herokuapp.com, using
the add-ons:

- `heroku-postgresql`_ (`hobby-basic tier`_, $9/month, required for size
  of dataset)
- `memcachier`_ (free dev tier)


To deploy with Heroku, you'll need to `signup for a free account`_ and
install the `Heroku Toolbelt`_.   Then you can:

1. Clone project locally
2. ``heroku apps:create``
3. ``git push heroku master``
4. See the current config with ``heroku config``, and then customize with
   environment variables using ``heroku config:set``
   (see ``wpcsite/settings.py`` and ``env.dist``)
5. Add superuser account (``heroku run ./manage.py createsuperuser``)

.. _Heroku: https://www.heroku.com/
.. _`signup for a free account`: https://signup.heroku.com/
.. _`Heroku Toolbelt`: http://toolbelt.heroku.com/
.. _`heroku-postgresql`: https://devcenter.heroku.com/articles/heroku-postgresql
.. _`hobby-basic tier`: https://devcenter.heroku.com/articles/heroku-postgres-plans
.. _`memcachier`: https://devcenter.heroku.com/articles/memcachier

Load Data
---------
There are several ways to get data into your API:

1. Load data from the github export
2. Load data from another webcompat server
3. Load sample data from the `WebPlatform project`_ and MDN_

Load from GitHub
****************
The data on browsercompat.herokuapp.com_ is archived in the
`browsercompat-data`_ github repo, and this is the fastest way to get data
into your empty API:

1. Clone the github repo (``git clone https://github.com/jwhitlock/browsercompat-data.git``)
2. Run the API (``./manage.py runserver``)
3. Import the data (``tools/upload_data.py --data /path/to/browsercompat-data/data``)

Load from another webcompat server
**********************************
If you have read access to a webcompat server that you'd like to clone, you
can grab the data for your own server.

1. Download the data (``tools/download_data.py --api https://browsercompat.example.com``)
2. Run the API (``./manage.py runserver``)
3. Import the data (``tools/upload_data.py``)

Load Sample Data
****************
The `WebPlatform project`_ imported data from MDN_, and stored the formatted
compatibility data in a `github project`_.  There is a lot of data that was
not imported, so it's not a good data source for re-displaying on MDN.
However, combining this data with specification data from MDN will create
a good data set for testing the API at scale.

To load sample data:

1. Run the API (``./manage.py runserver``)
2. Load a subset of the WebPlatform data (``tools/load_webcompat_data.py``) or full
   set of data (``tools/load_webcompat.py --all-data``)
3. Load specification data (``tools/load_spec_data.py``)


.. _`WebPlatform project`: http://www.webplatform.org
.. _MDN: https://developer.mozilla.org/en-US/
.. _`github project`: https://github.com/webplatform/compatibility-data
.. _browsercompat.herokuapp.com: https://browsercompat.herokuapp.com
.. _`browsercompat-data`: https://github.com/jwhitlock/browsercompat-data
.. _`Clone project locally`: https://help.github.com/articles/which-remote-url-should-i-use/
