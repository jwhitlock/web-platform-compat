Tools
=====

Some potentially useful scripts can be found in the /tools folder:

load_spec_data.py
-----------------
Initialize with specification data from MDN's SpecName_ and Spec2_.  Usage::

    $ tools/load_spec_data.py [--api <API>] [--user <USER>] [-vq] [--all-data]

* ``--api <API>`` `(optional)`: Set the base URL of the API
  (default: `http://localhost:8000`)
* ``--user <USER>`` `(optional)`: Set the username to use on the API
  (default: prompt for username)
* ``-v`` `(optional)`: Print debug information
* ``-q`` `(optional)`: Only print warnings

This script requires a fresh database (no specification data) and a user with
write access.  The bulk import will result in cascading cache invalidations,
which can be avoided by running the server without cached instances during the
import::

    $ USE_DRF_INSTANCE_CACHE=0 ./manage.py runserver


load_webcompat_data.py
----------------------
Initialize with compatibility data from the webplatform_ project. Usage::

    $ tools/load_webcompat_data.py [--api <API>] [--user <USER>] [-vq] [--all-data]

* ``--api <API>`` `(optional)`: Set the base URL of the API
  (default: `http://localhost:8000`)
* ``--user <USER>`` `(optional)`: Set the username to use on the API
  (default: prompt for username)
* ``-v`` `(optional)`: Print debug information
* ``-q`` `(optional)`: Only print warnings
* ``--all-data`` `(optional)`: Import all data, rather than a subset

This script requires a fresh database (no compatibility data) and a user with
write access.  The bulk import will result in cascading cache invalidations,
which can be avoided by running the server without cached instances during the
import::

    $ USE_DRF_INSTANCE_CACHE=0 ./manage.py runserver


sample_mdn.py
-------------
Load random pages from MDN in your browser.  Usage::

    $ tools/sample_mdn.py

.. _SpecName: https://developer.mozilla.org/en-US/docs/Template:SpecName
.. _Spec2: https://developer.mozilla.org/en-US/docs/Template:Spec2
.. _webplatform: https://github.com/webplatform/compatibility-data
