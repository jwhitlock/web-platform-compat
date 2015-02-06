Tools
=====

Some potentially useful scripts can be found in the /tools folder:

download_data.py
----------------
Download data from API. Usage::

    $ tools/download_data.py [--api API] [-vq] [--data DATA]

* ``--api <API>`` `(optional)`: Set the base URL of the API
  (default: `http://localhost:8000`)
* ``-v`` `(optional)`: Print debug information
* ``-q`` `(optional)`: Only print warnings
* ``--data <DATA>`` `(optional)`: Set the output data folder
  (default: data subfolder in the working copy)

This will create several files (browsers.json, versions.json, etc.) that
represent the API resources without pagination.

import_mdn.py
-------------
Import features from MDN, or reparse imported features. Usage::

    $ tools/import_mdn.py [--api API] [--user USER] [-vq]

* ``--api <API>`` `(optional)`: Set the base URL of the API
  (default: `http://localhost:8000`)
* ``--user <USER>`` `(optional)`: Set the username to use on the API
  (default: prompt for username)
* ``-v`` `(optional)`: Print debug information
* ``-q`` `(optional)`: Only print warnings

load_spec_data.py
-----------------
Import specification data from MDN's SpecName_ and Spec2_.  Usage::

    $ tools/load_spec_data.py [--api <API>] [--user <USER>] [-vq] [--all-data]

* ``--api <API>`` `(optional)`: Set the base URL of the API
  (default: `http://localhost:8000`)
* ``--user <USER>`` `(optional)`: Set the username to use on the API
  (default: prompt for username)
* ``-v`` `(optional)`: Print debug information
* ``-q`` `(optional)`: Only print warnings

load_webcompat_data.py
----------------------
Initialize with compatibility data from the WebPlatform_ project. Usage::

    $ tools/load_webcompat_data.py [--api <API>] [--user <USER>] [-vq] [--all-data]

* ``--api <API>`` `(optional)`: Set the base URL of the API
  (default: `http://localhost:8000`)
* ``--user <USER>`` `(optional)`: Set the username to use on the API
  (default: prompt for username)
* ``-v`` `(optional)`: Print debug information
* ``-q`` `(optional)`: Only print warnings
* ``--all-data`` `(optional)`: Import all data, rather than a subset

sample_mdn.py
-------------
Load random pages from MDN in your browser.  Usage::

    $ tools/sample_mdn.py

upload_data.py
--------------
Upload data to the API.  Usage::

    $ tools/upload_data.py [--api API] [--user USER] [-vq] [--data DATA]

* ``--api <API>`` `(optional)`: Set the base URL of the API
  (default: `http://localhost:8000`)
* ``--user <USER>`` `(optional)`: Set the username to use on the API
  (default: prompt for username)
* ``-v`` `(optional)`: Print debug information
* ``-q`` `(optional)`: Only print warnings
* ``--data <DATA>`` `(optional)`: Set the output data folder
  (default: data subfolder in the working copy)

This will load the local resources from files (browsers.json, versions.json, etc),
download the resources from the API, and upload the changes to make the API
match the local resource files.


.. _SpecName: https://developer.mozilla.org/en-US/docs/Template:SpecName
.. _Spec2: https://developer.mozilla.org/en-US/docs/Template:Spec2
.. _WebPlatform: https://github.com/webplatform/compatibility-data
