Resources
=========

Resources are simple objects supporting CRUD_ operations.  Read operations can
be done anonymously.  Creating and updating require account permissions, and
deleting requires admin account permissions.

All resources support similar operations using HTTP methods:

* ``GET /api/v1/<type>`` - List instances (paginated)
* ``POST /api/v1/<type>`` - Create new instance
* ``GET /api/v1/<type>/<id>`` - Retrieve an instance
* ``PUT /api/v1/<type>/<id>`` - Update an instance
* ``DELETE /api/v1/<type>/<id>`` - Delete instance

Additional features may be added as needed.  See the `JSON API docs`_ for ideas
and what format they will take.

Because the operations are similar, only browsers_ has complete operations
examples, and others just show retrieving an instance (``GET /api/v1/<type>/<id>``).

.. _CRUD: http://en.wikipedia.org/wiki/Create,_read,_update_and_delete
.. _`JSON API docs`: http://jsonapi.org/format/

.. contents:: 

Browsers
--------

A **browser** is a brand of web client that has one or more versions.  This
follows most users' understanding of browsers, i.e., ``firefox`` represents
desktop Firefox, ``safari`` represents desktop Safari, and ``firefox-mobile``
represents Firefox Mobile.

The **browsers** representation includes:

* **attributes**
    - **id** *(server selected)* - Database ID
    - **slug** *(write-once)* - Unique, human-friendly slug
    - **name** *(localized)* - Browser name
    - **note** *(localized)* - Notes, intended for related data like
      OS, applicable device, engines, etc.
* **links**
    - **versions** *(many)* - Associated versions_, ordered roughly
      from earliest to latest.  User can change the order.
    - **history_current** *(one)* - Current historical_browsers_.  Can be
      set to a value from **history** to revert changes.
    - **history** *(many)* - Associated historical_browsers_ in time order
      (most recent first). Changes are ignored.


List
****

To request the paginated list of **browsers**:

.. code-block:: http

    GET /api/v1/browsers HTTP/1.1
    Host: browsersupports.org
    Accept: application/vnd.api+json

A sample response is:

.. code-block:: http

    HTTP/1.1 200 OK
    Content-Type: application/vnd.api+json

.. code-block:: json

    {
        "browsers": [{
            "id": "1",
            "slug": "chrome",
            "name": {
                "en": "Chrome"
            },
            "note": null,
            "links": {
                "versions": ["123", "758"],
                "history_current": "1001",
                "history": ["1001"]
            }
        },{
            "id": "2",
            "slug": "firefox",
            "name": {
                "en": "Firefox"
            },
            "note": {
                "en": "Uses Gecko for its web browser engine."
            },
            "links": {
                "versions": ["124", "759"],
                "history_current": "1002",
                "history": ["1002"]
            }
        },{
            "id": "3",
            "slug": "ie",
            "name": {
                "en": "Internet Explorer"
            },
            "note": null,
            "links": {
                "versions": ["125", "167", "178", "760"],
                "history_current": "1003",
                "history": ["1003"]
            }
        },{
            "id": "4",
            "slug": "opera",
            "name": {
                "en": "Opera"
            },
            "note": null,
            "links": {
                "versions": ["126", "761"],
                "history_current": "1004",
                "history": ["1004"]
            }
        },{
            "id": "5",
            "slug": "safari",
            "name": {
                "en": "Safari"
            },
            "note": {
                "en": "Uses Webkit for its web browser engine."
            },
            "links": {
                "versions": ["127", "762"],
                "history_current": "1005",
                "history": ["1005"]
            }
        },{
            "id": "6",
            "slug": "android",
            "name": {
                "en": "Android"
            },
            "note": null,
            "links": {
                "versions": ["128", "763"],
                "history_current": "1006",
                "history": ["1006"]
            }
        },{
            "id": "7",
            "slug": "firefox-mobile",
            "name": {
                "en": "Firefox Mobile"
            },
            "note": {
                "en": "Uses Gecko for its web browser engine."
            },
            "links": {
                "versions": ["129", "764"],
                "history_current": "1007",
                "history": ["1007"]
            }
        },{
            "id": "8",
            "slug": "ie-phone",
            "name": {
                "en": "IE Phone"
            },
            "note": null,
            "links": {
                "versions": ["130", "765"],
                "history_current": "1008",
                "history": ["1008"]
            }
        },{
            "id": "9",
            "slug": "opera-mobile",
            "name": {
                "en": "Opera Mobile"
            },
            "note": null,
            "links": {
                "versions": ["131", "767"],
                "history_current": "1009",
                "history": ["1009"]
            }
        },{
            "id": "10",
            "slug": "safari-mobile",
            "name": {
                "en": "Safari Mobile"
            },
            "note": null,
            "links": {
                "versions": ["132", "768"],
                "history_current": "1010",
                "history": ["1010"]
            }
        }],
        "links": {
            "browsers.versions": {
                "href": "https://browsersupports.org/api/v1/versions/{browsers.versions}",
                "type": "versions"
            },
            "browsers.history_current": {
                "href": "https://browsersupports.org/api/v1/historical_browsers/{browsers.history_current}",
                "type": "historical_browsers"
            },
            "browsers.history": {
                "href": "https://browsersupports.org/api/v1/historical_browsers/{browsers.history}",
                "type": "historical_browsers"
            }
        },
        "meta": {
            "pagination": {
                "browsers": {
                    "prev": null,
                    "next": "https://browsersupports.org/api/v1/browsers?page=2&per_page=10",
                    "pages": 2,
                    "per_page": 10,
                    "total": 14,
                }
            }
        }
    }

Retrieve by ID
**************

To request a single **browser**:

.. code-block:: http

    GET /api/v1/browsers/2 HTTP/1.1
    Host: browsersupports.org
    Accept: application/vnd.api+json

A sample response is:

.. code-block:: http

    HTTP/1.1 200 OK
    Content-Type: application/vnd.api+json

.. code-block:: json

    {
        "browsers": {
            "id": "2",
            "slug": "firefox",
            "name": {
                "en": "Firefox"
            },
            "note": {
                "en": "Uses Gecko for its web browser engine."
            },
            "links": {
                "versions": ["124"],
                "history_current": "1002",
                "history": ["1002"]
            }
        },
        "links": {
            "browsers.versions": {
                "href": "https://browsersupports.org/api/v1/versions/{browsers.versions}",
                "type": "versions"
            },
            "browsers.history_current": {
                "href": "https://browsersupports.org/api/v1/historical_browsers/{browsers.history_current}",
                "type": "historical_browsers"
            },
            "browsers.history": {
                "href": "https://browsersupports.org/api/v1/historical_browsers/{browsers.history}",
                "type": "historical_browsers"
            }
        }
    }

Retrieve by Slug
****************

To request a **browser** by slug:

.. code-block:: http

    GET /api/v1/browsers?slug=firefox HTTP/1.1
    Host: browsersupports.org
    Accept: application/vnd.api+json

A sample response is:

.. code-block:: http

    HTTP/1.1 200 OK
    Content-Type: application/vnd.api+json

.. code-block:: json

    {
        "browsers": [{
            "id": "2",
            "slug": "firefox",
            "name": {
                "en": "Firefox"
            },
            "note": {
                "en": "Uses Gecko for its web browser engine."
            },
            "links": {
                "versions": ["124"],
                "history_current": "1002",
                "history": ["1002"]
            }
        }],
        "links": {
            "browsers.versions": {
                "href": "https://browsersupports.org/api/v1/versions/{browsers.versions}",
                "type": "versions"
            },
            "browsers.history_current": {
                "href": "https://browsersupports.org/api/v1/historical_browsers/{browsers.history_current}",
                "type": "historical_browsers"
            },
            "browsers.history": {
                "href": "https://browsersupports.org/api/v1/historical_browsers/{browsers.history}",
                "type": "historical_browsers"
            }
        }
    }

Create
******

Creating **browser** instances require authentication with create privileges.
To create a new **browser** instance, ``POST`` a representation with at least
the required parameters.  Some items (such as the ``id`` attribute and the
``history_current`` link) will be picked by the server, and will be ignored if
included.

Here's an example of creating a **browser** instance:

.. code-block:: http

    POST /api/v1/browsers HTTP/1.1
    Host: browsersupports.org
    Accept: application/vnd.api+json
    Authorization: Bearer mF_9.B5f-4.1JqM
    Content-Type: application/vnd.api+json

.. code-block:: json

    {
        "browsers": {
            "slug": "amazon-silk-mobile",
            "name": {
                "en": "Amazon Silk Mobile"
            }
        }
    }

A sample response is:

.. code-block:: http

    HTTP/1.1 201 Created
    Content-Type: application/vnd.api+json
    Location: https://browsersupports.org/browsers/15

.. code-block:: json

    {
        "browsers": {
            "id": "15",
            "slug": "amazon-silk-mobile",
            "name": {
                "en": "Amazon Silk Mobile"
            },
            "note": null,
            "links": {
                "versions": [],
                "history_current": "1027",
                "history": ["1027"]
            }
        },
        "links": {
            "browsers.versions": {
                "href": "https://browsersupports.org/api/v1/versions/{browsers.versions}",
                "type": "versions"
            },
            "browsers.history_current": {
                "href": "https://browsersupports.org/api/v1/historical_browsers/{browsers.history_current}",
                "type": "historical_browsers"
            },
            "browsers.history": {
                "href": "https://browsersupports.org/api/v1/historical_browsers/{browsers.history}",
                "type": "historical_browsers"
            }
        }
    }

This, and other methods that change resources, will create a new changeset_,
and associate the new historical_browsers_ with that changeset_.  To assign to an
existing changeset, add it to the URI:

.. code-block:: http

    POST /api/v1/browsers?changeset=176 HTTP/1.1
    Host: browsersupports.org
    Accept: application/vnd.api+json
    Authorization: Bearer mF_9.B5f-4.1JqM
    Content-Type: application/vnd.api+json

.. code-block:: json

    {
        "browsers": {
            "slug": "amazon-silk-mobile",
            "name": {
                "en": "Amazon Silk Mobile"
            }
        }
    }

Update
******

Updating a **browser** instance require authentication with create privileges.
Some items (such as the ``id`` attribute and ``history`` links) can not be
changed, and will be ignored if included.  A successful update will return a
``200 OK``, add a new ID to the ``history`` links list, and update the
``history_current`` link.

To update a **browser**:

.. code-block:: http

    PUT /api/v1/browsers/3 HTTP/1.1
    Host: browsersupports.org
    Accept: application/vnd.api+json
    Authorization: Bearer mF_9.B5f-4.1JqM

.. code-block:: json

    {
        "browsers": {
            "id": "3",
            "slug": "ie",
            "name": {
                "en": "IE"
            },
        }
    }

A sample response is:

.. code-block:: http

    HTTP/1.1 200 OK
    Content-Type: application/vnd.api+json

.. code-block:: json

    {
        "browsers": {
            "id": "3",
            "slug": "ie",
            "name": {
                "en": "IE"
            },
            "note": null,
            "links": {
                "versions": ["125", "167", "178"],
                "history_current": "1033",
                "history": ["1033", "1003"]
            }
        },
        "links": {
            "browsers.versions": {
                "href": "https://browsersupports.org/api/v1/versions/{browsers.versions}",
                "type": "versions"
            },
            "browsers.history_current": {
                "href": "https://browsersupports.org/api/v1/historical_browsers/{browsers.history_current}",
                "type": "historical_browsers"
            },
            "browsers.history": {
                "href": "https://browsersupports.org/api/v1/historical_browsers/{browsers.history}",
                "type": "historical_browsers"
            }
        }
    }

Partial Update
**************

An update can just update some fields:

.. code-block:: http

    PUT /api/v1/browsers/3 HTTP/1.1
    Host: browsersupports.org
    Accept: application/vnd.api+json
    Authorization: Bearer mF_9.B5f-4.1JqM

.. code-block:: json

    {
        "browsers": {
            "name": {
                "en": "M$ Internet Exploder 💩"
            }
        }
    }

A sample response is:

.. code-block:: http

    HTTP/1.1 200 OK
    Content-Type: application/vnd.api+json

.. code-block:: json

    {
        "browsers": {
            "id": "3",
            "slug": "ie",
            "name": {
                "en": "M$ Internet Exploder 💩"
            },
            "note": null,
            "links": {
                "versions": ["125", "167", "178"],
                "history_current": "1034",
                "history": ["1034", "1033", "1003"]
            }
        },
        "links": {
            "browsers.versions": {
                "href": "https://browsersupports.org/api/v1/versions/{browsers.versions}",
                "type": "versions"
            },
            "browsers.history_current": {
                "href": "https://browsersupports.org/api/v1/historical_browsers/{browsers.history_current}",
                "type": "historical_browsers"
            },
            "browsers.history": {
                "href": "https://browsersupports.org/api/v1/historical_browsers/{browsers.history}",
                "type": "historical_browsers"
            }
        }
    }

To change just the versions_ order:

.. code-block:: http

    PUT /api/v1/browsers/3 HTTP/1.1
    Host: browsersupports.org
    Accept: application/vnd.api+json
    Authorization: Bearer mF_9.B5f-4.1JqM

.. code-block:: json

    {
        "browsers": {
            "links": {
                "versions": ["178", "167", "125"]
            }
        }
    }

A sample response is:

.. code-block:: http

    HTTP/1.1 200 OK
    Content-Type: application/vnd.api+json

.. code-block:: json

    {
        "browsers": {
            "id": "3",
            "slug": "ie",
            "name": {
                "en": "M$ Internet Exploder 💩"
            },
            "note": null,
            "links": {
                "versions": ["178", "167", "125"],
                "history_current": "1035",
                "history": ["1035", "1034", "1033", "1003"]
            }
        },
        "links": {
            "browsers.versions": {
                "href": "https://browsersupports.org/api/v1/versions/{browsers.versions}",
                "type": "versions"
            },
            "browsers.history_current": {
                "href": "https://browsersupports.org/api/v1/historical_browsers/{browsers.history_current}",
                "type": "historical_browsers"
            },
            "browsers.history": {
                "href": "https://browsersupports.org/api/v1/historical_browsers/{browsers.history}",
                "type": "historical_browsers"
            }
        }
    }

Reverting to a previous instance
********************************

To revert to an earlier instance, set the ``history_current`` link to a
previous value.  This resets the content and creates a new
historical_browsers_ object:

.. code-block:: http

    PUT /api/v1/browsers/3 HTTP/1.1
    Host: browsersupports.org
    Accept: application/vnd.api+json
    Authorization: Bearer mF_9.B5f-4.1JqM

.. code-block:: json

    {
        "browsers": {
            "links": {
                "history_current": "1003"
            }
        }
    }

A sample response is:

.. code-block:: http

    HTTP/1.1 200 OK
    Content-Type: application/vnd.api+json

.. code-block:: json

    {
        "browsers": {
            "id": "3",
            "slug": "ie",
            "name": {
                "en": "Internet Explorer"
            },
            "note": none,
            "links": {
                "versions": ["125", "167", "178"],
                "history_current": "1036",
                "history": ["1036", "1035", "1034", "1033", "1003"]
            }
        },
        "links": {
            "browsers.versions": {
                "href": "https://browsersupports.org/api/v1/versions/{browsers.versions}",
                "type": "versions"
            },
            "browsers.history_current": {
                "href": "https://browsersupports.org/api/v1/historical_browsers/{browsers.history_current}",
                "type": "historical_browsers"
            },
            "browsers.history": {
                "href": "https://browsersupports.org/api/v1/historical_browsers/{browsers.history}",
                "type": "historical_browsers"
            }
        }
    }

Deletion
********

To delete a **browser**:

.. code-block:: http

    DELETE /api/v1/browsers/2 HTTP/1.1
    Host: browsersupports.org
    Accept: application/vnd.api+json
    Authorization: Bearer mF_9.B5f-4.1JqM

A successful response has no body:

.. code-block:: http

    HTTP/1.1 204 No Content

Reverting a deletion
********************

To revert a deletion:

.. code-block:: http

    PUT /api/v1/browsers/2 HTTP/1.1
    Host: browsersupports.org
    Accept: application/vnd.api+json
    Authorization: Bearer mF_9.B5f-4.1JqM

A sample response is:

.. code-block:: http

    HTTP/1.1 200 OK
    Content-Type: application/vnd.api+json

.. code-block:: json

    {
        "browsers": {
            "id": "2",
            "slug": "firefox",
            "name": {
                "en": "Firefox"
            },
            "note": null,
            "links": {
                "versions": ["124"],
                "history_current": "1104",
                "history": ["1104", "1103", "1002"]
            }
        },
        "links": {
            "browsers.versions": {
                "href": "https://browsersupports.org/api/v1/versions/{browsers.versions}",
                "type": "versions"
            },
            "browsers.history_current": {
                "href": "https://browsersupports.org/api/v1/historical_browsers/{browsers.history_current}",
                "type": "historical_browsers"
            },
            "browsers.history": {
                "href": "https://browsersupports.org/api/v1/historical_browsers/{browsers.history}",
                "type": "historical_browsers"
            }
        }
    }


Versions
--------

A **version** is a specific release of a Browser.

The **versions** representation includes:

* **attributes**
    - **id** *(server selected)* - Database ID
    - **version** *(write-once)* - Version of browser, or null
      if unknown (for example, to document support for features in early HTML)
    - **release_day** - Day that browser was released in `ISO 8601`_ format, or
      null if unknown.
    - **retirement_day** - Approximate day the browser was "retired" (stopped
      being a current browser), in `ISO 8601`_ format, or null if unknown.
    - **status** - One of
      ``retired`` (old version, no longer the preferred download for any
      platform),
      ``retired-beta`` (old beta version, replaced
      by a new beta or release),
      ``current`` (current version, the preferred download or update for
      users),
      ``beta`` (a release candidate suggested for early adopters or testers),
      ``future`` (a planned future release).
    - **release_notes_uri** *(localized)* - URI of release notes for this
      version, or null if none.
    - **note** *(localized)* - Engine, OS, etc. information, or null
* **links**
    - **browser** - The related **browser**
    - **supports** *(many)* - Associated **supports**, in ID order.  Changes
      are ignored; work on the **supports** to add, change, or remove.
    - **history_current** *(one)* - Current **historical_versions**.
      Set to a value from **history** to revert to that version.
    - **history** *(many)* - Associated **historical_versions**, in time
      order (most recent first).  Changes are ignored.

To get a single **version**:

.. code-block:: http

    GET /api/v1/versions/123 HTTP/1.1
    Host: browsersupports.org
    Accept: application/vnd.api+json

A sample response is:

.. code-block:: http

    HTTP/1.1 200 OK
    Content-Type: application/vnd.api+json

.. code-block:: json

    {
        "versions": {
            "id": "123",
            "version": "1.0.154",
            "release_day": "2008-12-11",
            "retirement_day": "2009-05-24",
            "status": "retired",
            "release_notes_uri": null,
            "note": null,
            "links": {
                "browser": "1",
                "supports": ["1125", "1126", "1127", "1128", "1129"],
                "history_current": "567",
                "history": ["567"]
            }
        },
        "links": {
            "versions.browser": {
                "href": "https://browsersupports.org/api/v1/browsers/{versions.browser}",
                "type": "browsers"
            },
            "versions.supports": {
                "href": "https://browsersupports.org/api/v1/supports/{versions.supports}",
                "type": "supports"
            },
            "versions.history_current": {
                "href": "https://browsersupports.org/api/v1/historical_versions/{versions.history_current}",
                "type": "historical_versions"
            },
            "versions.history": {
                "href": "https://browsersupports.org/api/v1/historical_versions/{versions.history}",
                "type": "historical_versions"
            }
        }
    }

Features
--------
A **feature** is a web technology.  This could be a precise technology, such
as the value ``cover`` for the CSS ``background-size`` property.  It could be
a heirarchical group of related technologies, such as the CSS
``background-size`` property or the set of all CSS properties.  Some features
correspond to a page on MDN_, which will display the list of specifications
and a browser compatability table of the sub-features.

The **features** representation includes:

* **attributes**
    - **id** *(server selected)* - Database ID
    - **slug** *(write-once)* - Unique, human-friendly slug
    - **mdn_path** *(optional)* - The path to the page on MDN that this feature
      was first scraped from.  May be used in UX or for debugging import
      scripts.
    - **experimental** - True if a feature is considered experimental, such as
      being non-standard or part of an non-ratified spec.
    - **standardized** - True if a feature is described in a standards-track
      spec, regardless of the spec's maturity.
    - **stable** - True if a feature is considered suitable for production
      websites.
    - **obsolete** - True if a feature should not be used in new development.
    - **name** *(canonical or localized)* - Feature name.  If the name is the
      code used by a developer, then the value is a string, and should be
      wrapped in a ``<code>`` block when displayed.  If the name is a
      description of the feature, then the value is the available
      translations, including at least an ``en`` translation, and may include
      HTML markup.  For example, ``"display"`` and ``"display: none"`` are
      canonical names for the CSS display property and one of the values for
      that property, while ``"Basic support"``,
      ``"<code>none, inline</code> and <code>block</code>"``, and
      ``"CSS Properties"`` are non-canonical names that should be translated.

* **links**
    - **sections** *(many)* - Associated sections_.  Order can be changed by
      the user.
    - **supports** *(many)* - Associated supports_, Order is in ID order,
      changes are ignored.
    - **parent** *(one or null)* - The feature one level up, or null
      if top-level.  Can be changed by user.
    - **children** *(many)* - The features that have this feature as parent, in
      display order.  Can be an empty list, for "leaf" features.  Can be
      re-ordered by the user.
    - **history_current** *(one)* - Current historical_features_.  User can
      set to a valid **history** to revert to that version.
    - **history** *(many)* - Associated historical_features_, in time order
      (most recent first).  Changes are ignored.


To get a specific **feature** (in this case, a leaf feature with a canonical name):

.. code-block:: http

    GET /api/v1/features/276 HTTP/1.1
    Host: browsersupports.org
    Accept: application/vnd.api+json

A sample response is:

.. code-block:: http

    HTTP/1.1 200 OK
    Content-Type: application/vnd.api+json

.. code-block:: json

    {
        "features": {
            "id": "276",
            "mdn_path": null,
            "slug": "css-property-background-size-value-contain",
            "experimental": false,
            "standardized": true,
            "stable": true,
            "obsolete": false,
            "name": "background-size: contain"},
            "links": {
                "sections": ["485"],
                "supports": ["1125", "1212", "1536"],
                "parent": "173",
                "children": [],
                "history_current": "456",
                "history": ["456"]
            }
        },
        "links": {
            "features.sections": {
                "href": "https://browsersupports.org/api/v1/sections/{features.sections}",
                "type": "sections"
            },
            "feature.parent": {
                "href": "https://browsersupports.org/api/v1/features/{feature.parent}",
                "type": "features"
            },
            "features.children": {
                "href": "https://browsersupports.org/api/v1/features/{feature.children}",
                "type": "features"
            },
            "features.history_current": {
                "href": "https://browsersupports.org/api/v1/historical_features/{features.history_current}",
                "type": "historical_features"
            },
            "features.history": {
                "href": "https://browsersupports.org/api/v1/historical_features/{features.history}",
                "type": "historical_features"
            }
        }
    }

Here's an example of a branch feature with a translated name (the parent of the
previous example):

.. code-block:: http

    GET /api/v1/features/173 HTTP/1.1
    Host: browsersupports.org
    Accept: application/vnd.api+json

A sample response is:

.. code-block:: http

    HTTP/1.1 200 OK
    Content-Type: application/vnd.api+json

.. code-block:: json

    {
        "features": {
            "id": "173",
            "mdn_path": "en-US/docs/Web/CSS/background",
            "slug": "css-property-background",
            "experimental": false,
            "standardized": true,
            "stable": true,
            "obsolete": false,
            "name": {
                "en": "CSS <code>background</code> property"
            },
            "links": {
                "sections": [],
                "supports": [],
                "parent": ["12"],
                "children": ["275", "276", "277"],
                "history_current": "395",
                "history": ["395"]
            }
        },
        "links": {
            "features.sections": {
                "href": "https://browsersupports.org/api/v1/sections/{features.sections}",
                "type": "sections"
            },
            "feature.parent": {
                "href": "https://browsersupports.org/api/v1/features/{feature.parent}",
                "type": "features"
            },
            "features.children": {
                "href": "https://browsersupports.org/api/v1/features/{feature.children}",
                "type": "features"
            },
            "features.history_current": {
                "href": "https://browsersupports.org/api/v1/historical_features/{features.history_current}",
                "type": "historical_features"
            },
            "features.history": {
                "href": "https://browsersupports.org/api/v1/historical_features/{features.history}",
                "type": "historical_features"
            }
        }
    }

Supports
--------

A **support** is an assertion that a particular Version of a Browser supports
(or does not support) a feature.

The **support** representation includes:

* **attributes**
    - **id** *(server selected)* - Database ID
    - **support** - Assertion of support of the version_ for the
      feature_, one of ``"yes"``, ``"no"``, ``"partial"``,
      ``"unknown"``, or ``"never"``
    - **prefix** - Prefix used to enable support, such as `"moz"`
    - **prefix_mandatory** - True if the prefix is required
    - **alternate_name** - An alternate name associated with this feature,
      such as ``"RTCPeerConnectionIdentityEvent"``
    - **alternate_name_mandatory** - True if the alternate name is required
    - **requires_config** - A configuration string
      required to enable the feature, such as
      ``"media.peerconnection.enabled=on"``
    - **default_config** - The configuration string in the shipping
      browser, such as ``"media.peerconnection.enabled=off"``
    - **protected** - True if the feature requires additional steps to enable
      in order to protect the user's security or privacy, such as geolocation
      and the Bluetooth API.
    - **note** *(localized)* - Short note on support, designed for inline
      display, max 20 characters
    - **footnote** *(localized)* - Long note on support, designed for
      display after a compatibility table, MDN wiki format
* **links**
    - **version** *(one)* - The associated version_.  Cannot be changed by
      the user after creation.
    - **feature** *(one)* - The associated feature_.  Cannot be changed by
      the user after creation.  The version and feature combo must be unique.
    - **history_current** *(one)* - Current
      historical_supports_.  Can be changed to a valid
      **history** to revert to that version.
    - **history** *(many)* - Associated historical_supports_
      in time order (most recent first).  Changes are ignored.


To get a single **support**:

.. code-block:: http

    GET /api/v1/supports/1123 HTTP/1.1
    Host: browsersupports.org
    Accept: application/vnd.api+json

A sample response is:

.. code-block:: http

    HTTP/1.1 200 OK
    Content-Type: application/vnd.api+json

.. code-block:: json

    {
        "supports": {
            "id": "1123",
            "support": "yes",
            "prefix": null,
            "prefix_mandatory": false,
            "alternate_name": null,
            "alternate_name_mandatory": false,
            "requires_config": null,
            "default_config": null,
            "protected": false,
            "note": null,
            "footnote": null,
            "links": {
                "version": "123",
                "feature": "276",
                "history_current": "2567",
                "history": ["2567"]
            }
        },
        "links": {
            "supports.version": {
                "href": "https://browsersupports.org/api/v1/versions/{supports.version}",
                "type": "versions"
            },
            "supports.feature": {
                "href": "https://browsersupports.org/api/v1/browsers/{supports.feature}",
                "type": "features"
            },
            "supports.history_current": {
                "href": "https://browsersupports.org/api/v1/historical_supports/{supports.history_current}",
                "type": "historical_supports"
            },
            "supports.history": {
                "href": "https://browsersupports.org/api/v1/historical_supports/{supports.history}",
                "type": "historical_supports"
            }
        }
    }

Specifications
--------------

A **specification** is a standards document that specifies a web technology.

The **specification** representation includes:

* **attributes**
    - **id** *(server selected)* - Database ID
    - **mdn_key** - The key for the KumaScript macros SpecName_ and Spec2_
      used as a data source.
    - **name** *(localized)* - Specification name
    - **uri** *(localized)* - Specification URI, without subpath and anchor
* **links**
    - **sections** *(many)* - Associated sections_.  The order can be changed
      by the user.
    - **maturity** *(one)* - Associated maturity_.
      Can be changed by the user.

To get a single **specification**:

.. code-block:: http

    GET /api/v1/specifications/273 HTTP/1.1
    Host: browsersupports.org
    Accept: application/vn.api+json

A sample response is:

.. code-block:: http

    HTTP/1.1 200 OK
    Content-Type: application/vnd.api+json

.. code-block:: json

    {
        "specifications": {
            "id": "273",
            "mdn_key": "CSS1",
            "name": {
                "en": "Cascading Style Sheets, level 1",
                "fr": "Les feuilles de style en cascade, niveau 1"
            },
            "uri": {
                "en": "http://www.w3.org/TR/CSS1/",
                "fr": "http://www.yoyodesign.org/doc/w3c/css1/index.html"
            },
            "links": {
                "sections": ["792", "793"]
                "maturity": "23"
            }
        },
        "links": {
            "specifications.sections": {
                "href": "https://browsersupports.org/api/v1/sections/{specifications.sections}",
                "type": "sections"
            },
            "specifications.maturity": {
                "href": "https://browsersupports.org/api/v1/maturities/{specifications.maturity}",
                "type": "maturities"
            }
        }
    }

Sections
--------

A **section** refers to a specific area of a specification_ document.

The **section** representation includes:

* **attributes**
    - **id** *(server selected)* - Database ID
    - **name** *(localized)* - Section name
    - **subpath** *(localized)* - A subpage (possibly with an #anchor) to get
      to the subsection in the doc.  Can be empty string.
    - **note** *(localized)* - Notes for this section
* **links**
    - **specification** *(one)* - The specification_.  Can be changed by
      the user.
    - **features** *(many)* - The associated features_.  In ID order,
      changes are ignored.

To get a single **section**:

.. code-block:: http

    GET /api/v1/sections/792 HTTP/1.1
    Host: browsersupports.org
    Accept: application/vn.api+json

A sample response is:

.. code-block:: http

    HTTP/1.1 200 OK
    Content-Type: application/vnd.api+json

.. code-block:: json

    {
        "sections": {
            "id": "792",
            "name": {
                "en": "'display'"
            },
            "subpath": {
                "en": "#display"
            },
            "note": {
                "en": "Basic values: <code>none<\/code>, <code>block<\/code>, <code>inline<\/code>, and <code>list-item<\/code>."
            },
            "links": {
                "specification": "273",
                "features": ["275", "276", "277"],
            }
        },
        "links": {
            "sections.specification": {
                "href": "https://browsersupports.org/api/v1/specifications/{sections.specification}",
                "type": "specifications"
            },
            "sections.features": {
                "href": "https://browsersupports.org/api/v1/sections/{sections.features}",
                "type": "features"
            }
        }
    }

Maturities
----------

A **maturity** refers to the maturity of a specification_ document.

The **maturity** representation includes:

* **attributes**
    - **id** *(server selected)* - Database ID
    - **mdn_key** - The value for this status in the KumaScript macro Spec2_
    - **name** *(localized)* - Status name
* **links**
    - **specifications** *(many)* - Associated specifications_.  In ID order,
      changes are ignored.

To get a single **maturity**:

.. code-block:: http

    GET /api/v1/maturities/49 HTTP/1.1
    Host: browsersupports.org
    Accept: application/vn.api+json

A sample response is:

.. code-block:: http

    HTTP/1.1 200 OK
    Content-Type: application/vnd.api+json

.. code-block:: json

    {
        "maturities": {
            "id": "49",
            "mdn_key": "REC",
            "name": {
                "en": "Recommendation",
                "jp": "勧告"
            },
            "links": {
                "specifications": ["84", "85", "272", "273", "274", "576"]
            }
        },
        "links": {
            "maturities.specifications": {
                "href": "https://browsersupports.org/api/v1/specifications/{maturities.specifications}",
                "type": "specifications"
            }
        }
    }

.. _feature: Features_
.. _specification: Specifications_
.. _maturity: `Maturities`_
.. _version: `Versions`_

.. _changeset: change-control.html#changesets

.. _historical_browsers: history.html#historical-browsers
.. _historical_features: history.html#historical-features
.. _historical_supports: history.html#historical-supports

.. _non-linguistic: http://www.w3.org/International/questions/qa-no-language#nonlinguistic
.. _`ISO 8601`: http://en.wikipedia.org/wiki/ISO_8601
.. _MDN: https://developer.mozilla.org
.. _SpecName: https://developer.mozilla.org/en-US/docs/Template:SpecName
.. _Spec2: https://developer.mozilla.org/en-US/docs/Template:Spec2
