Views
=====

A **View** is a combination of resources for a particular presentation.  It is
suitable for anonymous viewing of content.

It is possible that views are unnecessary, and could be constructed by
supporting optional parts of the JSON API spec, such as `Inclusion of Linked
Resources`_.  These views are written as if they are aliases for a
fully-fleshed implementation of JSON API.

View a Feature
--------------

This view collects the data for a feature_, including the related
resources needed to display it on MDN.

Here is a simple example, the view for the HTML element address_:

.. code-block:: http

    GET /api/v1/view_features/html-element-address HTTP/1.1
    Host: browsersupports.org
    Accept: application/vnd.api+json

A sample response is:

.. code-block:: http

    HTTP/1.1 200 OK
    Content-Type: application/vnd.api+json

.. code-block:: json

    {
        "features": {
            "id": "816",
            "mdn_path": "en-US/docs/Web/HTML/Element/address",
            "slug": "html-element-address",
            "experimental": false,
            "standardized": true,
            "stable": true,
            "obsolete": false,
            "name": "address",
            "links": {
                "sections": ["746", "421", "70"],
                "supports": [],
                "parent": "800",
                "children": ["191"],
                "history_current": "216",
                "history": ["216"]
            }
        },
        "linked": {
            "features": [
                {
                    "id": "191",
                    "mdn_path": null,
                    "slug": "html-address",
                    "experimental": false,
                    "standardized": true,
                    "stable": true,
                    "obsolete": false,
                    "name": {
                        "en": "Basic support"
                    },
                    "links": {
                        "sections": [],
                        "supports": [
                            "358", "359", "360", "361", "362", "363", "364",
                            "365", "366", "367", "368"],
                        "parent": "816",
                        "children": [],
                        "history_current": "395",
                        "history": ["395"]
                    }
                }
            ],
            "sections": [
                {
                    "id": "746",
                    "name": {
                        "en": "The address element"
                    },
                    "subpath": {
                        "en": "sections.html#the-address-element"
                    },
                    "notes": null,
                    "links": {
                        "specification": "273",
                        "features": ["816"],
                    }
                },{
                    "id": "421",
                    "name": {
                        "en": "The address element"
                    },
                    "subpath": {
                        "en": "sections.html#the-address-element"
                    },
                    "notes": null,
                    "links": {
                        "specification": "114",
                        "features": ["816"],
                    }
                },{
                    "id": "70",
                    "name": {
                        "en": "The ADDRESS element"
                    },
                    "subpath": {
                        "en": "struct/global.html#h-7.5.6"
                    },
                    "notes": null,
                    "links": {
                        "specification": "576",
                        "features": ["816"],
                    }
                }
            ],
            "specifications": [
                {
                    "id": "62",
                    "key": "HTML WHATWG",
                    "name": {
                        "en": "WHATWG HTML Living Standard",
                    },
                    "uri": {
                        "en": "http://www.whatwg.org/specs/web-apps/current-work/multipage/",
                    },
                    "links": {
                        "sections": ["745", "746", "747"]
                        "maturity": "23"
                    }
                },{
                    "id": "114",
                    "key": "HTML5 W3C",
                    "name": {
                        "en": "HTML5",
                    },
                    "uri": {
                        "en": "http://www.w3.org/TR/html5/",
                    },
                    "links": {
                        "sections": ["420", "421", "422"]
                        "maturity": "52"
                    }
                },{
                    "id": "576",
                    "key": "HTML4.01",
                    "name": {
                        "en": "HTML 4.01 Specification",
                    },
                    "uri": {
                        "en": "http://www.w3.org/TR/html401/",
                    },
                    "links": {
                        "sections": ["69", "70", "71"]
                        "maturity": "49"
                    }
                }
            ],
            "maturities": [
                {
                    "id": "23",
                    "key": "Living",
                    "name": {
                        "en": "Living Standard",
                    },
                    "links": {
                        "specifications": ["62"]
                    }
                }, {
                    "id": "49",
                    "key": "REC",
                    "name": {
                        "en": "Recommendation",
                        "jp": "勧告"
                    },
                    "links": {
                        "specifications": ["84", "85", "272", "273", "274", "576"]
                    }
                }, {
                    "id": "52",
                    "key": "CR",
                    "name": {
                        "en": "Candidate Recommendation",
                        "ja": "勧告候補",
                    },
                    "links": {
                        "specifications": ["83", "113", "114", "115"]
                    }
                }
            ],
            "supports": [
                {
                    "id": "358",
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
                        "version": "758",
                        "feature": "191",
                        "history_current": "3567",
                        "history": ["3567"]
                    }
                }, {
                    "id": "359",
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
                        "version": "759",
                        "feature": "191",
                        "history_current": "3568",
                        "history": ["3568"]
                    }
                }, {
                    "id": "360",
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
                        "version": "760",
                        "feature": "191",
                        "history_current": "3569",
                        "history": ["3569"]
                    }
                }, {
                    "id": "361",
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
                        "version": "761",
                        "feature": "191",
                        "history_current": "3570",
                        "history": ["3570"]
                    }
                }, {
                    "id": "362",
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
                        "version": "762",
                        "feature": "191",
                        "history_current": "3571",
                        "history": ["3571"]
                    }
                }, {
                    "id": "362",
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
                        "version": "762",
                        "feature": "191",
                        "history_current": "3571",
                        "history": ["3571"]
                    }
                }, {
                    "id": "363",
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
                        "version": "763",
                        "feature": "191",
                        "history_current": "3572",
                        "history": ["3572"]
                    }
                }, {
                    "id": "364",
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
                        "version": "764",
                        "feature": "191",
                        "history_current": "3573",
                        "history": ["3573"]
                    }
                }, {
                    "id": "365",
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
                        "version": "765",
                        "feature": "191",
                        "history_current": "3574",
                        "history": ["3574"]
                    }
                }, {
                    "id": "366",
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
                        "version": "766",
                        "feature": "191",
                        "history_current": "3575",
                        "history": ["3575"]
                    }
                }, {
                    "id": "367",
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
                        "version": "767",
                        "feature": "191",
                        "history_current": "3576",
                        "history": ["3576"]
                    }
                }, {
                    "id": "368",
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
                        "version": "768",
                        "feature": "191",
                        "history_current": "3577",
                        "history": ["3577"]
                    }
                }
            ],
            "versions": [
                {
                    "id": "758",
                    "version": null,
                    "release_day": null,
                    "retirement_day": null,
                    "status": "current",
                    "release_notes_uri": null,
                    "note": null,
                    "links": {
                        "browser": "1",
                        "supports": ["158", "258", "358", "458"],
                        "history_current": "1567",
                        "history": ["1567"]
                    }
                }, {
                    "id": "759",
                    "version": "1.0",
                    "release_day": "2004-12-09",
                    "retirement_day": "2005-02-24",
                    "status": "retired",
                    "release_notes_uri": null,
                    "note": null,
                    "links": {
                        "browser": "2",
                        "supports": ["159", "259", "359", "459"],
                        "history_current": "1568",
                        "history": ["1568"]
                    }
                }, {
                    "id": "760",
                    "version": "1.0",
                    "release_day": "1995-08-16",
                    "retirement_day": null,
                    "status": "retired",
                    "release_notes_uri": null,
                    "note": null,
                    "links": {
                        "browser": "3",
                        "supports": ["160", "260", "360", "460"],
                        "history_current": "1569",
                        "history": ["1569"]
                    }
                }, {
                    "id": "761",
                    "version": "5.12",
                    "release_day": "2001-06-27",
                    "retirement_day": null,
                    "status": "retired",
                    "release_notes_uri": null,
                    "note": null,
                    "links": {
                        "browser": "4",
                        "supports": ["161", "261", "361", "461"],
                        "history_current": "1570",
                        "history": ["1570"]
                    }
                }, {
                    "id": "762",
                    "version": "1.0",
                    "release_day": "2003-06-23",
                    "retirement_day": null,
                    "status": "retired",
                    "release_notes_uri": null,
                    "note": null,
                    "links": {
                        "browser": "5",
                        "supports": ["162", "262", "362", "462"],
                        "history_current": "1571",
                        "history": ["1571"]
                    }
                }, {
                    "id": "763",
                    "version": null,
                    "release_day": null,
                    "retirement_day": null,
                    "status": "current",
                    "release_notes_uri": null,
                    "note": null,
                    "links": {
                        "browser": "6",
                        "supports": ["163", "263", "363", "463"],
                        "history_current": "1572",
                        "history": ["1572"]
                    }
                }, {
                    "id": "764",
                    "version": "1.0",
                    "release_day": null,
                    "retirement_day": null,
                    "status": "retired",
                    "release_notes_uri": null,
                    "note": "Uses Gecko 1.7",
                    "links": {
                        "browser": "7",
                        "supports": ["164", "264", "364", "464"],
                        "history_current": "1574",
                        "history": ["1574"]
                    }
                }, {
                    "id": "765",
                    "version": null,
                    "release_day": null,
                    "retirement_day": null,
                    "status": "current",
                    "release_notes_uri": null,
                    "note": null,
                    "links": {
                        "browser": "8",
                        "supports": ["165", "265", "365", "465"],
                        "history_current": "1575",
                        "history": ["1575"]
                    }
                }, {
                    "id": "766",
                    "version": null,
                    "release_day": null,
                    "retirement_day": null,
                    "status": "current",
                    "release_notes_uri": null,
                    "note": null,
                    "links": {
                        "browser": "11",
                        "supports": ["166", "266", "366", "466"],
                        "history_current": "1576",
                        "history": ["1576"]
                    }
                }, {
                    "id": "767",
                    "version": null,
                    "release_day": null,
                    "retirement_day": null,
                    "status": "current",
                    "release_notes_uri": null,
                    "note": null,
                    "links": {
                        "browser": "9",
                        "supports": ["167", "267", "367", "467"],
                        "history_current": "1577",
                        "history": ["1577"]
                    }
                }, {
                    "id": "768",
                    "version": null,
                    "release_day": null,
                    "retirement_day": null,
                    "status": "current",
                    "release_notes_uri": null,
                    "note": null,
                    "links": {
                        "browser": "10",
                        "supports": ["168", "268", "368", "468"],
                        "history_current": "1578",
                        "history": ["1578"]
                    }
                }
            ],
            "browsers": [
                {
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
                },{
                    "id": "11",
                    "slug": "opera-mini",
                    "name": {
                        "en": "Opera Mini"
                    },
                    "note": null,
                    "links": {
                        "versions": ["131", "766"],
                        "history_current": "1019",
                        "history": ["1019"]
                    }
                }
            ]
        },
        "links": {
            "features.features": {
                "href": "https://browsersupports.org/api/v1/features/{features.features}",
                "type": "features"
            },
            "features.sections": {
                "href": "https://browsersupports.org/api/v1/sections/{features.sections}",
                "type": "sections"
            },
            "features.parent": {
                "href": "https://browsersupports.org/api/v1/features/{features.parent}",
                "type": "features"
            },
            "features.children": {
                "href": "https://browsersupports.org/api/v1/features/{features.children}",
                "type": "features"
            },
            "features.history_current": {
                "href": "https://browsersupports.org/api/v1/historical_features/{features.history_current}",
                "type": "historical_features"
            },
            "features.history": {
                "href": "https://browsersupports.org/api/v1/historical_features/{features.history}",
                "type": "historical_features"
            },
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
            },
            "versions.browser": {
                "href": "https://browsersupports.org/api/v1/browsers/{versions.browser}",
                "type": "browsers"
            },
            "versions.supports": {
                "href": "https://browsersupports.org/api/v1/supports/{versions.features}",
                "type": "supports"
            },
            "versions.history_current": {
                "href": "https://browsersupports.org/api/v1/historical_versions/{versions.history_current}",
                "type": "historical_versions"
            },
            "versions.history": {
                "href": "https://browsersupports.org/api/v1/historical_versions/{versions.history}",
                "type": "historical_versions"
            },
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
            },
            "specifications.sections": {
                "href": "https://browsersupports.org/api/v1/sections/{specifications.sections}",
                "type": "sections"
            },
            "specifications.maturity": {
                "href": "https://browsersupports.org/api/v1/maturities/{specifications.maturity}",
                "type": "maturities"
            },
            "sections.specification": {
                "href": "https://browsersupports.org/api/v1/specifications/{sections.specification}",
                "type": "specifications"
            },
            "sections.features": {
                "href": "https://browsersupports.org/api/v1/sections/{sections.features}",
                "type": "features"
            },
            "maturities.specifications": {
                "href": "https://browsersupports.org/api/v1/specifications/{maturities.specifications}",
                "type": "specifications"
            }
        },
        "meta": {
            "compat_table": {
                "tabs": [{
                    "name": {
                        "en": "Desktop"
                    },
                    "browsers": ["1", "2", "3", "4", "5"]
                },{
                    "name": {
                        "en": "Mobile"
                    },
                    "browsers": ["6", "7", "8", "11", "9", "10"]
                }],
                "supports": {
                    "191": {
                        "1": ["358"],
                        "2": ["359"],
                        "3": ["360"],
                        "4": ["361"],
                        "5": ["362"],
                        "6": ["363"],
                        "7": ["364"],
                        "8": ["365"],
                        "11": ["366"],
                        "9": ["367"],
                        "10": ["368"]
                    }
                }
            }
        }
    }

The process for using this representation is:

1. Parse into an in-memory object store,
2. Create the "Specifications" section:
    1. Add the ``Specifications`` header
    2. Create an HTML table with a header row "Specification", "Status", "Comment"
    3. For each id in features.links.sections (``["746", "421", "70"]``):
        * Add the first column: a link to specifications.uri.(lang or en) +
          sections.subpath.(lang or en), with link text
          specifications.name.(lang or en), with title based on
          sections.name.(lang or en) or feature.name.(lang or en).
        * Add the second column: A span with class
          "spec-" + maturities.mdn_key, and the text
          maturities.name.(lang or en).
        * Add the third column:
          maturities.notes.(lang or en), or empty string
    4. Close the table, and add an edit button.
3. Create the Browser Compatibility section:
    1. Add The "Browser compatibility" header
    2. For each item in meta.compat-table.tabs, create a table with the proper
       name ("Desktop", "Mobile")
    3. For each browser id in meta.compat-table.tabs.browsers, add a column with
       the translated browser name.
    4. For each feature in features.features:
        * Add the first column: the feature name.  If it is a string, then wrap
          in ``<code>``.  Otherwise, use the best translation of feature.name,
          in a ``lang=(lang)`` block.
        * Add any feature flags, such as an obsolete or experimental icon,
          based on the feature flags.
        * For each browser id in meta.compat-table-important:
            - Get the important support IDs from
              meta.compat-table-important.supports.<``feature ID``>.<``browser ID``>
            - If null, then display "?"
            - If just one, display "<``version``>", or "<``support``>",
              depending on the defined attributes
            - If multiple, display as subcells
            - Add prefixes, alternate names, config, notes, and footnotes links
              as appropriate
    5. Close each table, add an edit button
    6. Add footnotes for displayed supports

This may be done by including the JSON in the page as sent over the wire,
or loaded asynchronously, with the tables built after initial page load.

This can also be used by a `"caniuse" table layout`_ by ignoring the meta
section and displaying all the included data.  This will require more
client-side processing to generate, or additional data in the ``<meta>``
section.

Updating Views with Changesets
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Updating the page requires a sequence of requests.  For example, if a user
wants to change Chrome support for ``<address>`` from an unknown version to
version 1, you'll have to create the version_ for that version,
then add the support_ for the support.

The first step is to create a changeset_ as an authenticated user:

.. code-block:: http

    POST /api/v1/changesets/ HTTP/1.1
    Host: browsersupports.org
    Accept: application/vnd.api+json
    Authorization: Bearer mF_9.B5f-4.1JqM
    Content-Type: application/vnd.api+json

.. code-block:: json

    {
        "changesets": {
            "target_resource": "features",
            "target_resource_id": "816"
        }
    }

A sample response is:

.. code-block:: http

    HTTP/1.1 201 Created
    Content-Type: application/vnd.api+json
    Location: https://browsersupports.org/changesets/5284

.. code-block:: json

    {
        "changesets": {
            "id": "5284",
            "created": "1405360263.670000",
            "modified": "1405360263.670000",
            "target_resource": "features",
            "target_resource_id": "816",
            "links": {
                "user": "42",
                "historical_browsers": [],
                "historical_versions": [],
                "historical_features": [],
                "historical_supports": []
            }
        },
        "links": {
            "changesets.user": {
                "href": "https://browsersupports.org/api/v1/users/{changesets.user}",
                "type": "users"
            },
            "changesets.historical_browsers": {
                "href": "https://browsersupports.org/api/v1/historical_browsers/{changesets.historical_browsers}",
                "type": "historical_browsers"
            },
            "changesets.historical_versions": {
                "href": "https://browsersupports.org/api/v1/historical_versions/{changesets.historical_versions}",
                "type": "historical_versions"
            },
            "changesets.historical_features": {
                "href": "https://browsersupports.org/api/v1/historical_features/{changesets.historical_features}",
                "type": "historical_features"
            },
            "changesets.historical_supports": {
                "href": "https://browsersupports.org/api/v1/historical_supports/{changesets.historical_supports}",
                "type": "historical_supports"
            }
        }
    }

Next, use the changeset_ ID when creating the version_:

.. code-block:: http

    POST /api/v1/versions/?changeset=5284 HTTP/1.1
    Host: browsersupports.org
    Accept: application/vnd.api+json
    Authorization: Bearer mF_9.B5f-4.1JqM
    Content-Type: application/vnd.api+json

.. code-block:: json

    {
        "versions": {
            "version": "1",
            "status": "retired",
            "links": {
                "browser": "1",
            }
        }
    }

A sample response is:

.. code-block:: http

    HTTP/1.1 201 Created
    Content-Type: application/vnd.api+json
    Location: https://browsersupports.org/versions/4477

.. code-block:: json

    {
        "versions": {
            "id": "4477",
            "version": "1",
            "release_day": null,
            "retirement_day": null,
            "status": "retired",
            "release_notes_uri": null,
            "note": null,
            "links": {
                "browser": "1",
                "supports": [],
                "history_current": "3052",
                "history": ["3052"]
            }
        },
        "links": {
            "versions.browser": {
                "href": "https://browsersupports.org/api/v1/browsers/{versions.browser}",
                "type": "browsers"
            },
            "versions.supports": {
                "href": "https://browsersupports.org/api/v1/supports/{versions.features}",
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

Finally, create the support_:

.. code-block:: http

    POST /api/v1/supports/?changeset=5284 HTTP/1.1
    Host: browsersupports.org
    Accept: application/vnd.api+json
    Authorization: Bearer mF_9.B5f-4.1JqM
    Content-Type: application/vnd.api+json

.. code-block:: json

    {
        "supports": {
            "support": "yes",
            "links": {
                "version": "4477",
                "feature": "191"
            }
        }
    }

A sample response is:

.. code-block:: http

    HTTP/1.1 201 Created
    Content-Type: application/vnd.api+json
    Location: https://browsersupports.org/supports/8219

.. code-block:: json

    {
        "supports": {
            "id": "8219",
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
                "version": "4477",
                "feature": "191",
                "history_current": "7164",
                "history": ["7164"]
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

The historical_versions_ and historical_supports_
resources will both refer to changeset_ 5284, and this changeset_ is
linked to feature_ 816, despite the fact that no changes were made
to the feature_.  This will facilitate displaying a history of
the compatibility tables, for the purpose of reviewing changes and reverting
vandalism.

.. _feature: resources.html#features
.. _support: resources.html#versions-feature
.. _version: resources.html#versions

.. _changeset: change-control#changeset

.. _historical_versions: history.html#historical-versions
.. _historical_supports: history.html#historical-supports

.. _address: https://developer.mozilla.org/en-US/docs/Web/HTML/Element/address
.. _`Inclusion of Linked Resources`: http://jsonapi.org/format/#fetching-includes
.. _`"caniuse" table layout`: https://wiki.mozilla.org/MDN/Development/CompatibilityTables/Data_Requirements#1._CanIUse_table_layout
