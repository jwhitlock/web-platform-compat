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
  (default: ``http://localhost:8000``)
* ``--user <USER>`` `(optional)`: Set the username to use on the API
  (default: prompt for username)
* ``-v`` `(optional)`: Print debug information
* ``-q`` `(optional)`: Only print warnings

load_spec_data.py
-----------------
Import specification data from MDN's SpecName_ and Spec2_.  Usage::

    $ tools/load_spec_data.py [--api <API>] [--user <USER>]
                              [-vq] [--all-data]

* ``--api <API>`` `(optional)`: Set the base URL of the API
  (default: ``http://localhost:8000``)
* ``--user <USER>`` `(optional)`: Set the username to use on the API
  (default: prompt for username)
* ``-v`` `(optional)`: Print debug information
* ``-q`` `(optional)`: Only print warnings

load_webcompat_data.py
----------------------
Initialize with compatibility data from the WebPlatform_ project. Usage::

    $ tools/load_webcompat_data.py [--api <API>] [--user <USER>]
                                   [-vq] [--all-data]

* ``--api <API>`` `(optional)`: Set the base URL of the API
  (default: ``http://localhost:8000``)
* ``--user <USER>`` `(optional)`: Set the username to use on the API
  (default: prompt for username)
* ``-v`` `(optional)`: Print debug information
* ``-q`` `(optional)`: Only print warnings
* ``--all-data`` `(optional)`: Import all data, rather than a subset

make_doc_requests.py
--------------------
Make documentation/integration requests against an API. Used by
tools/run_integration_tests.sh. Usage::

    $ tools/integration_requests.py [--mode {display,generate,verify}]
                                    [--api API]
                                    [--raw RAW] [--cases CASES]
                                    [--user USER] [--password PASSWORD]
                                    [--include-mod] [-vq]
                                    [case name [case name ...]]

* ``--mode {display,generate,verify}`` `(optional)`: Set the mode. Values are:
    * ``display`` (default): Run GET requests against an API, printing the
      actual requests and responses.
    * ``generate``: Run all requests against an API.  Throw away some headers,
      such as ``Allow`` and ``Server``.  Modify other headers, such as
      ``Cookies``, to make them consistant from run to run.  Standardize some
      response data, such as creation and modification times.  Store the
      cleaned-up requests and responses in the docs folder, for documentation
      and integration testing.
    * ``verify``: Run all requests against an API, standardizing the requests
      and responses and comparing them to those in the docs folder.
* ``--api API`` `(optional)`: Set the base URL of the API
  (default: ``http://localhost:8000``)
* ``--raw RAW`` `(optional)`: Set the path to the folder containing raw
  requests and responses (default: ``docs/raw``)
* ``--cases CASES`` `(optional)`: Set the path to the documentation cases
  JSON file (default ``docs/doc_cases.json``)
* ``--user USER``: Set the username to use for requests (default anonymous
  requests)
* ``--password PASSWORD``: Set the password to use for requests (default is
  prompt if ``--user`` set, otherwise use anonymous requests)
* ``--include-mod``: If ``--mode display``, then include requests that would
  modify the data, such as ``POST``, ``PUT``, and ``DELETE``.
* ``-v``: Be more verbose
* ``-q``: Be quieter
* ``case name``: Run the listed cases, not the full suite of cases

mirror_mdn_features.py
----------------------
Create and update API features for MDN pages.  This will create the branch
features, and then import_mdn.py can be used to generate the leaf features.
Usage::

    $ tools/mirror_mdn_features.py [--api API] [--data DATA]
                                   [--user USER] [--password PASSWORD]

* ``--api API`` `(optional)`: Set the base URL of the API
  (default: ``http://localhost:8000``)
* ``--user USER``: Set the username to use for requests (default is prompt for
  username)
* ``--password PASSWORD``: Set the password to use for requests (default is
  prompt for username)
* ``--data DATA``: Set the data folder for caching MDN page JSON


run_integration_tests.sh
------------------------
Run a local API server with known data, make requests against it, and look for
issues in the response. Usage::

    $ tools/run_integration_tests.sh [-ghqv]

* ``-g``: Generate documentation / integration test samples. If omitted, then
  responses are checked against the documentation samples. Useful for adding
  new documentation cases, or updating when the API changes.
* ``-h``: Show a usage statement
* ``-q``: Show less output
* ``-v``: Show more output

sample_mdn.py
-------------
Load random pages from MDN in your browser.  Usage::

    $ tools/sample_mdn.py

upload_data.py
--------------
Upload data to the API.  Usage::

    $ tools/upload_data.py [--api API] [--user USER]
                           [-vq] [--data DATA]

* ``--api <API>`` `(optional)`: Set the base URL of the API
  (default: ``http://localhost:8000``)
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
