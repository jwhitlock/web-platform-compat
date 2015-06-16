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

.. literalinclude:: /raw/browser-list-request-headers.txt
    :language: http

A sample response is:

.. literalinclude:: /raw/browser-list-response-headers.txt
    :language: http

.. literalinclude:: /raw/browser-list-response-body.json
    :language: json

Retrieve by ID
**************

To request a single **browser** with a known ID:

.. literalinclude:: /raw/browser-by-id-request-headers.txt
    :language: http

A sample response is:

.. literalinclude:: /raw/browser-by-id-response-headers.txt
    :language: http

.. literalinclude:: /raw/browser-by-id-response-body.json
    :language: json

Retrieve by Slug
****************

To request a **browser** by slug:

.. literalinclude:: /raw/browser-by-slug-request-headers.txt
    :language: http

The response includes the desired browser, in list format:

.. literalinclude:: /raw/browser-by-slug-response-headers.txt
    :language: http

.. literalinclude:: /raw/browser-by-slug-response-body.json
    :language: json

Create
******

Creating **browser** instances require authentication with create privileges.
To create a new **browser** instance, ``POST`` a representation with at least
the required parameters.  Some items (such as the ``id`` attribute and the
``history_current`` link) will be picked by the server, and will be ignored if
included.

Here's an example of creating a **browser** instance:

.. literalinclude:: /raw/browser-create-minimal-request-headers.txt
    :language: http

.. literalinclude:: /raw/browser-create-minimal-request-body.json
    :language: json

A sample response is:

.. literalinclude:: /raw/browser-create-minimal-response-headers.txt
    :language: http

.. literalinclude:: /raw/browser-create-minimal-response-body.json
    :language: json

This, and other methods that change resources, will create a new changeset_,
and associate the new historical_browsers_ with that changeset_.  To assign to an
existing changeset, add it to the URI:

.. literalinclude:: /raw/browser-create-in-changeset-2-request-headers.txt
    :language: http

.. literalinclude:: /raw/browser-create-in-changeset-2-request-body.json
    :language: json

A sample response is:

.. literalinclude:: /raw/browser-create-in-changeset-2-response-headers.txt
    :language: http

.. literalinclude:: /raw/browser-create-in-changeset-2-response-body.json
    :language: json

Update
******

Updating a **browser** instance require authentication with create privileges.
Some items (such as the ``id`` attribute and ``history`` links) can not be
changed, and will be ignored if included.  A successful update will return a
``200 OK``, add a new ID to the ``history`` links list, and update the
``history_current`` link.

This update changes the English name from "Internet Explorer" to "Microsoft Internet Explorer":


.. literalinclude:: /raw/browser-update-full-request-headers.txt
    :language: http

.. literalinclude:: /raw/browser-update-full-request-body.json
    :language: json

With this response:

.. literalinclude:: /raw/browser-update-full-response-headers.txt
    :language: http

.. literalinclude:: /raw/browser-update-full-response-body.json
    :language: json

Partial Update
**************

An update can just update the target fields.  This is a further request to
change the English name for the Internet Explorer browser.

.. literalinclude:: /raw/browser-update-partial-request-headers.txt
    :language: http

.. literalinclude:: /raw/browser-update-partial-request-body.json
    :language: json

With this response:

.. literalinclude:: /raw/browser-update-partial-response-headers.txt
    :language: http

.. literalinclude:: /raw/browser-update-partial-response-body.json
    :language: json

Update order of related resources
*********************************
In many cases, related resources (which appear in the "links" attribute")
are sorted by ID.  In some cases, the order is significant, and is set on
a related field.  For example, **versions** for a **browser** are ordered
by updating the order on the **browser** object:

To change just the versions_ order:

.. literalinclude:: /raw/browser-update-versions-order-request-headers.txt
    :language: http

.. literalinclude:: /raw/browser-update-versions-order-request-body.json
    :language: json

With this response:

.. literalinclude:: /raw/browser-update-versions-order-response-headers.txt
    :language: http

.. literalinclude:: /raw/browser-update-versions-order-response-body.json
    :language: json

Reverting to a previous instance
********************************

To revert to an earlier instance, set the ``history_current`` link to a
previous value.  This resets the content and creates a new
historical_browsers_ object:

.. literalinclude:: /raw/browser-revert-request-headers.txt
    :language: http

.. literalinclude:: /raw/browser-revert-request-body.json
    :language: json

With this response:

.. literalinclude:: /raw/browser-revert-response-headers.txt
    :language: http

.. literalinclude:: /raw/browser-revert-response-body.json
    :language: json

Deletion
********

To delete a **browser**:

.. literalinclude:: /raw/browser-delete-request-headers.txt
    :language: http

The response has no body:

.. literalinclude:: /raw/browser-delete-response-headers.txt
    :language: http

Reverting a deletion
********************
Reverting deletions is not currently possible.

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
    - **order** *(read-only)* - The relative order amoung versions for this
      browser. The order can be changed on the **browser** resource.
* **links**
    - **browser** - The related **browser**
    - **supports** *(many)* - Associated **supports**, in ID order.  Changes
      are ignored; work on the **supports** to add, change, or remove.
    - **history_current** *(one)* - Current **historical_versions**.
      Set to a value from **history** to revert to that version.
    - **history** *(many)* - Associated **historical_versions**, in time
      order (most recent first).  Changes are ignored.

To get a single **version**:

.. literalinclude:: /raw/version-by-id-request-headers.txt
    :language: http

A sample response is:

.. literalinclude:: /raw/version-by-id-response-headers.txt
    :language: http

.. literalinclude:: /raw/version-by-id-response-body.json
    :language: json

Features
--------
A **feature** is a web technology.  This could be a precise technology, such
as the value ``cover`` for the CSS ``background-size`` property.  It could be
a heirarchical group of related technologies, such as the CSS
``background-size`` property or the set of all CSS properties.  Some features
correspond to a page on MDN_, which will display the list of specifications
and a browser compatibility table of the sub-features.

The **features** representation includes:

* **attributes**
    - **id** *(server selected)* - Database ID
    - **slug** *(write-once)* - Unique, human-friendly slug
    - **mdn_uri** *(optional, localized)* - The URI of the language-specific
      MDN page that this feature was first scraped from.  If the path contains
      unicode, it should be percent-encoded as in `RFC 3987`_. May be used in
      UX or for debugging import scripts.
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


To get a specific **feature** (in this case, a leaf feature with a translated
name):

.. literalinclude:: /raw/feature-by-id-request-headers.txt
    :language: http

A sample response is:

.. literalinclude:: /raw/feature-by-id-response-headers.txt
    :language: http

.. literalinclude:: /raw/feature-by-id-response-body.json
    :language: json

Here's an example of a branch feature with a canonical name (the parent of the
previous example):

.. literalinclude:: /raw/feature-by-id-canonical-request-headers.txt
    :language: http

A sample response is:

.. literalinclude:: /raw/feature-by-id-canonical-response-headers.txt
    :language: http

.. literalinclude:: /raw/feature-by-id-canonical-response-body.json
    :language: json

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
    - **note** *(localized)* - Note on support, designed for
      display after a compatibility table, can contain HTML
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

.. literalinclude:: /raw/support-by-id-request-headers.txt
    :language: http

A sample response is:

.. literalinclude:: /raw/support-by-id-response-headers.txt
    :language: http

.. literalinclude:: /raw/support-by-id-response-body.json
    :language: json

Specifications
--------------

A **specification** is a standards document that specifies a web technology.

The **specification** representation includes:

* **attributes**
    - **id** *(server selected)* - Database ID
    - **slug** - Unique, human-friendly key
    - **mdn_key** - Key used in the KumaScript macros SpecName_ and Spec2_.
    - **name** *(localized)* - Specification name
    - **uri** *(localized)* - Specification URI, without subpath and anchor
* **links**
    - **maturity** *(one)* - Associated maturity_.
      Can be changed by the user.
    - **sections** *(many)* - Associated sections_.  The order can be changed
      by the user.
    - **history_current** *(one)* - Current
      historical_specifications_.  Can be changed to a valid
      **history** to revert to that version.
    - **history** *(many)* - Associated historical_specifications_
      in time order (most recent first).  Changes are ignored.

To get a single **specification**:

.. literalinclude:: /raw/specification-by-id-request-headers.txt
    :language: http

A sample response is:

.. literalinclude:: /raw/specification-by-id-response-headers.txt
    :language: http

.. literalinclude:: /raw/specification-by-id-response-body.json
    :language: json

Sections
--------

A **section** refers to a specific area of a specification_ document.

The **section** representation includes:

* **attributes**
    - **id** *(server selected)* - Database ID
    - **number** *(optional, localized)* - The section number
    - **name** *(localized)* - Section name
    - **subpath** *(localized, optional)* - A subpage (possibly with an
      #anchor) to get to the subsection in the doc.  Can be empty string.
    - **note** *(localized, optional)* - Notes for this section
* **links**
    - **specification** *(one)* - The specification_.  Can be changed by
      the user.
    - **features** *(many)* - The associated features_.  In ID order,
      changes are ignored.
    - **history_current** *(one)* - Current
      historical_sections_.  Can be changed to a valid
      **history** to revert to that version.
    - **history** *(many)* - Associated historical_sections_
      in time order (most recent first).  Changes are ignored.

To get a single **section**:

.. literalinclude:: /raw/section-by-id-request-headers.txt
    :language: http

A sample response is:

.. literalinclude:: /raw/section-by-id-response-headers.txt
    :language: http

.. literalinclude:: /raw/section-by-id-response-body.json
    :language: json

Maturities
----------

A **maturity** refers to the maturity of a specification_ document.

The **maturity** representation includes:

* **attributes**
    - **id** *(server selected)* - Database ID
    - **slug** - A human-friendly identifier for this maturity.  When applicabile,
      it match the key in the KumaScript macro Spec2_
    - **name** *(localized)* - Status name
* **links**
    - **specifications** *(many)* - Associated specifications_.  In ID order,
      changes are ignored.
    - **history_current** *(one)* - Current
      historical_maturities_.  Can be changed to a valid
      **history** to revert to that version.
    - **history** *(many)* - Associated historical_maturities_
      in time order (most recent first).  Changes are ignored.

To get a single **maturity**:

.. literalinclude:: /raw/maturity-by-id-request-headers.txt
    :language: http

A sample response is:

.. literalinclude:: /raw/maturity-by-id-response-headers.txt
    :language: http

.. literalinclude:: /raw/maturity-by-id-response-body.json
    :language: json

.. _feature: Features_
.. _specification: Specifications_
.. _maturity: `Maturities`_
.. _version: `Versions`_

.. _changeset: change-control.html#changesets

.. _historical_browsers: history.html#historical-browsers
.. _historical_features: history.html#historical-features
.. _historical_supports: history.html#historical-supports
.. _historical_specifications: history.html#historical-specifications
.. _historical_sections: history.html#historical-sections
.. _historical_maturities: history.html#historical-maturities

.. _non-linguistic: http://www.w3.org/International/questions/qa-no-language#nonlinguistic
.. _`ISO 8601`: http://en.wikipedia.org/wiki/ISO_8601
.. _MDN: https://developer.mozilla.org
.. _RFC 3987: http://tools.ietf.org/html/rfc3987.html#section-3.1
.. _SpecName: https://developer.mozilla.org/en-US/docs/Template:SpecName
.. _Spec2: https://developer.mozilla.org/en-US/docs/Template:Spec2
