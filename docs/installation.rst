============
Installation
============

Install Django Project
----------------------

1. Clone project locally
2. Create virtualenv
3. Install dependencies via pip
4. Customize with environment variables (see ``wpcsite/settings.py``)
5. Setup database, add superuser account (``./manage.py migrate``)
6. Optionally, run memcached_ for improved performance
7. Run it (``./manage.py runserver``)

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
3. Import the data (``upload_data.py --data /path/to/browsercompat-data/data``)

Load from another webcompat server
**********************************
If you have read access to a webcompat server that you'd like to clone, you
can grab the data for your own server.

1. Download the data (``download_data.py --api https://browsercompat.example.com``)
2. Run the API (``./manage.py runserver``)
3. Import the data (``upload_data.py``)

Load Sample Data
****************
The `WebPlaform project` imported data from MDN_, and stored the formatted
compatibility data in a `github project`.  There is a lot of data that was
not imported, so it's not a good data source for re-displaying on MDN.
However, combining this data with specification data from MDN will create
a good data set for testing the API at scale.

To load sample data:

1. Run the API (``./manage.py runserver``)
2. Load a subset of the WebPlatform data (``tools/load_webcompat_data.py``) or full
   set of data (``tools/load_webcompat.py --all-data``)
3. Load specification data (``tools/load_spec_data.py``)

.. _memcached: http://memcached.org
.. _`WebPlatform project`: http://www.webplatform.org
.. _MDN: https://developer.mozilla.org/en-US/
.. _`github project`: https://github.com/webplatform/compatibility-data
.. _browsercompat.herokuapp.com: https://browsercompat.herokuapp.com
.. _`browsercompat-data`: https://github.com/jwhitlock/browsercompat-data
