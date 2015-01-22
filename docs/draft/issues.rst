Issues
======

This draft API reflects a good guess at a useful, efficent API for storing
user-contributed compatibility data.  Some of the guesses are better than
others.  This section highlights the areas where more experienced opinions
are welcome, and areas where more work is expected.

.. contents:: 

Additions to Browser Compatibility Data Architecture
----------------------------------------------------

This spec includes changes to the `Browser Compatibility Data Architecture`_
developed around March 2014.  These seemed like a good idea to me, based on
list threads and thinking how to recreate Browser Compatibility tables live on
MDN.

These changes are:

* browsers_
    - **slug** - human-friendly unique identifier
    - **name** - converted to localized text.
    - **note** - added for engine, OS, etc. information
* versions_
    - Was `browser-versions`, but multi-word resources are problematic.
    - **release_day** - Day of release
    - **retirement_day** - Day of "retirement", or when it was superceeded by
      a new release.
    - **status** - One of `"retired"`, `"retired-beta"`, `"current"`, `"beta"`,
      `"future"`
    - **relese_notes_uri** - For Mozilla releases, as specified in CompatGeckoDesktop_.
    - **note** - added for engine version, etc.
* features_
    - **slug** - human-friendly unique identifier
    - **mdn_uri** - MDN page that data was scraped from
    - **experimental** - True if the feature is considered experimental due to
      being part of a unratified spec such as CSS Transitions, ES6, or the DOM
      Living Standard.  For example, see the `run-in` value of
      `Web/CSS/display`_.
    - **standardized** - True if the feature is described in a standards-track
      specification, regardless of the maturity of the specification.  Most
      features are standardized, but some browser-specific features may be
      non-standard, and some features like the `left` and `right` features
      of `Web/CSS/caption-side`_ were part of the CSS2 "wishlist" document
      that was not standardized.
    - **stable** - True if the feature is considered stable enough for
      production usage.
    - **obsolete** - True if the feature should no longer be used in
      production code.
    - **name** - converted to localized text, or a string if the name is
      canonical
    - **sections** - replaces spec link
    - **parent**, **children** - tree relations for this feature
* supports_
    - Was `browser-version-features`, but multi-word resources are problematic.
    - **support** - Added a value "never", for cases where developers have
      announced they will not support a feature.  For example, the `CSS
      @font-face at-rule`_, which has been closed as WONTFIX in `Bugzilla
      119490`_, appears as ``{{CompatNo}}{{unimplemented_inline(119490)}}``.
    - **prefix** - string prefix to enable, or null if no prefix
    - **prefix_mandatory** - True if the prefix is required
    - **alternate_name** - An alternate name associated with this feature,
      such as `"RTCPeerConnectionIdentityEvent"`
    - **alternate_name_mandatory** - True if the alternate name is required
    - **requires_config** - A configuration string
      required to enable the feature, such as
      `"media.peerconnection.enabled=on"`
    - **default_config** - The configuration string in the shipping
      browser, such as `"media.peerconnection.enabled=off"`
    - **note** - short note, length limited, translated, or null.  Supports
      inline notes currently in use on MDN
    - **footnote** - longer note, may include code samples, translated, or null.
      Supports extended footnote in use on MDN.

There are also additional Resources_:

* specifications_ - For referring to a specification, with translated titles
  and URIs.
* sections_ - For referring to a section of a specification, with
  translated titles and anchors
* maturities_ - For identifying the process stage of a specification
* All the history_ resources (historical_browsers_,
  historical_versions_, etc.)
* users_ - For identifying the user who made a change
* changesets_ - Collect several history resources into a logical change

Unresolved Issues
-----------------

* We've been talking data models.  This document talks about APIs.
  **The service will not have a working SQL interface**.  Features like
  history require that changes are made through the API.  Make sure your
  use case is supported by the API.
* overholt wants `availability in Web Workers`_.  Is an API enough to support
  that need?
* I think Niels Leenheer has good points about browsers being different across
  operating systems and OS versions - I'm considering adding this to the model:
  `Mapping browsers to 2.2.1 Dictionary Browser Members`_.
* How should we support versioning the API?  There is no Internet concensus.
    - I expect to break the API as needed while implementing.  At some point
      (late 2014), we'll call it v1.
    - Additions, such as new attributes and links, will not cause an API bump
    - Some people put the version in the URL (/v1/browsers, /v2/browsers)
    - Some people use a custom header (``X-Api-Version: 2``)
    - Some people use the Accept header
      (``Accept: application/vnd.api+json;version=2``)
    - These people all hate each other. `Read a good blog post on the subject`_.
* What should be the default permissions for new users?  What is the process
  for upgrading or downgrading permissions?
* Is Persona a good fit for creating API accounts?  There will need to be a
  process where an MDN user becomes an API user, and a way for an API user
  to authenticate directly with the API.
* If we succeed, we'll have a detailed history of browser support for each
  feature.  For example, the datastore will know that every version of Firefox
  supported the ``<h1>`` tag.  How should version history be summarized for the
  Browser Compatibility table?  Should the API pick the "important" versions,
  and the KumaScript display them all?  Or should the API send all known
  versions, and the KumaScript parse them for the significant versions, with
  UX for exposing known versions?  The view doc proposes one implementation,
  with a ``<meta>`` section for identifying the important bits.
* Do we want to add more items to versions?  Wikipedia has interesting
  data for `Chrome release history`_ and `Firefox release history`_.
  Some possibly useful additions: release date, retirement date, codename,
  JS engine version, operating system, notes.  It feels like we should import
  the data from version-specific KumaScripts like CompatGeckoDesktop_
  (versions, release dates, translations, links to release docs).
* We'll need additional models for automated browser testing.  Things like
  user agents, test names, test results for a user / user agent.  And, we'll
  need a bunch of rules for mapping test results to features, required number
  of tests before we'll say a browser supports a feature, what to do with
  test conflicts, etc.  It might be easier to move all those wishlist items to
  a different project, that talks to this API when it's ready to assert
  browser support for a feature.
* We need to decide on the URIs for the API and the developer resources.
  This is being tracked by `Bugzilla 1050458`_.
* In browsers_, it seems like icon won't be generally useful.  What format
  should the icon be?  What size?  It may be more useful to use the slug for
  deciding between icons designed for the local implementation.


Interesting MDN Pages
---------------------

These MDN pages represent use cases for compatibility data.  They may suggest
features to add, or existing features that will be dropped.

* `Web/HTML/Element/address`_ - A typical "simple" example.  However, the name
  is non-canonical ("Basic Features") and must be translated, rather than a
  canonical form ("`<address>`") that could be the same for all languages.
* `Web/CSS/display`_ - This complex page includes non-canonical names
  ("``none,inline`` and ``block``"), experimental features (``run-in``),
  support changes across versions, prefixes, etc.  Everything that makes this
  project hard.
* `Web/CSS/cursor`_ - May be more complex than `display`.
* `Web/HTML/Element/Input`_ - Complex, with lots of attributes.  Split by
  standard may not be as useful as other ways to split it.
* `Web/CSS/animation-name`_ - New property that moved from prefixed support to
  standard support.
* `Web/CSS/caption-side`_ - Rarely used 'Non-standard' tag.  Also seen on
  `Web/CSS/text-align`_.
* `Web/CSS/@font-face`_ - Rarely used 'Unimplemented' tag as inline note.  Also
  seen on `Web/CSS/text-decoration-line`_.
* `Web/CSS/length`_ - Rarely used "warning" tag.  Also seen on
  `Web/CSS/text-underline-position`_.
* `Web/CSS/line-break`_ - Rarely used "Fix Me" inline note
* `Web/CSS/min-height`_ - "Obsolete since Gecko 22" tag on auto, versus:
* `Web/CSS/min-width`_ - Obsolete trash can icon
* `Web/CSS/text-transform`_ - Interesting use of non-ascii unicode in feature
  names, good test case.
* `Web/CSS/transform-origin`_ - IE may justify a 'alternate' value for
  supports.support, or just 'no' with a footnote.

Some pages will require manual intervention to get them into the data store.
Here's a sample:

* `Web/CSS/box-decoration-break`_ - Broken formatting
* `Web/CSS/box-sizing`_ - In Safari column, link to engine version will become
  an inline note.
* `Web/CSS/break-inside`_ - Will need to add a skeleton compatibility table.
* `Web/CSS/@document`_ - Specification paragraph rather than normal table.
* `Web/CSS/clip`_ - Long inline notes should be converted to footnotes.
* `Web/CSS/:invalid`_ - Links in feature names to other MDN docs
* `Web/CSS/outline-color`_ - Instead of version, long note about support.
  Convert to two versions, footnote.
* `Web/CSS/radial-gradient`_ - Evolving standard, used version notes instead of
  marking feature as experimental or deprecated.
* `Web/CSS/ratio`_ - Strange Chrome version
* `Web/CSS/tab-size`_ - Lots of interesting versions, including Safari nightly.
* `Web/CSS/text-rendering`_ - convert to footnotes, other changes needed.  Not
  sure if it belongs under CSS.
* `Web/API/IDBObjectStore`_ - apoplectic warning of Chrome behaviour.  Maybe
  convert to regular note, or add a Feature for Chrome prefix with non-standard
  tag?

Translating from MDN wiki format
--------------------------------

The current compatibility data on developer.mozilla.org in MDN wiki format, a
combination of HTML and KumaScript.

A MDN page will be imported as a feature with at least one child feature.

Here's the MDN wiki version of the Specifications section for
`Web/CSS/border-image-width`_:

.. code-block:: html

    <h2 id="Specifications" name="Specifications">Specifications</h2>
    <table class="standard-table">
      <thead>
        <tr>
          <th scope="col">Specification</th>
          <th scope="col">Status</th>
          <th scope="col">Comment</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>{{SpecName('CSS3 Backgrounds', '#border-image-width', 'border-image-width')}}</td>
          <td>{{Spec2('CSS3 Backgrounds')}}</td>
          <td>Initial specification</td>
        </tr>
      </tbody>
    </table>

The elements of this table are converted into API data:

* **Body row, first column** - Format is ``SpecName('KEY', 'PATH', 'NAME')``.
  ``KEY`` is the specification.mdn_key, ``PATH`` is
  section.subpath, in the page language, and ``NAME`` is
  section.name, in the page language.  The macro SpecName_ has
  additional lookups on ``KEY`` for specification.name and specification.uri
  (en language only).
* **Body row, second column** - Format is ``Spec2('KEY')``.  ``KEY`` is the
  specification.mdn_key, and should match the one from column one.  The macro
  Spec2_ has additional lookups on ``KEY`` for maturity.mdn_key,
  and maturity.name (multiple languages).
* **Body row, third column** - Format is a text fragment which may include HTML
  markup, becomes the section.name associated with this
  feature.

and here's the Browser compatibility section:

.. code-block:: html

    <h2 id="Browser_compatibility">Browser compatibility</h2>
    <div>{{CompatibilityTable}}</div>
      <div id="compat-desktop">
        <table class="compat-table">
          <tbody>
            <tr>
              <th>Feature</th>
              <th>Chrome</th>
              <th>Firefox (Gecko)</th>
              <th>Internet Explorer</th>
              <th>Opera</th>
              <th>Safari</th>
            </tr>
            <tr>
              <td>Basic support</td>
              <td>15.0</td>
              <td>{{CompatGeckoDesktop("13.0")}}</td>
              <td>11</td>
              <td>15</td>
              <td>6</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div id="compat-mobile">
        <table class="compat-table">
          <tbody>
            <tr>
              <th>Feature</th>
              <th>Android</th>
              <th>Firefox Mobile (Gecko)</th>
              <th>IE Phone</th>
              <th>Opera Mobile</th>
              <th>Safari Mobile</th>
            </tr>
            <tr>
              <td>Basic support</td>
              <td>{{CompatUnknown}}</td>
              <td>{{CompatGeckoMobile("13.0")}}</td>
              <td>{{CompatNo}}</td>
              <td>{{CompatUnknown}}</td>
              <td>{{CompatUnknown}}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

This will be converted to API resources:

* **Table class** - one of ``"compat-desktop"`` or ``"compat-mobile"``.
  Representation in API is TBD.
* **Header row, all but the first column** - format is either ``Browser Name
  (Engine Name)`` or ``Browser Name``.  Used for browser.name, engine name is
  discarded.  Other formats or KumaScript halt import.
* **Non-header rows, first column** - If the format is ``<code>some
  text</code>``, then feature.canonical=true and the string is the canonical
  name.  If the format is text w/o KumaScript, it is the non-canonocial name.
  If there is also KumaScript, it varies. **TODO:** doc KumaScript.
* **Non-header rows, remaining columns** - Usually Kumascript:
    * ``{{CompatUnknown}}`` - version.version is ``null``, and
      support.support is ``"unknown"``
    * ``{{CompatVersionUnknown}}`` - version.version and are ``null``,
      and support.support in ``"yes"``
    * ``{{CompatNo}}`` - version.version and are ``null``, and
      support.support is ``"no"``
    * ``{{CompatGeckoDesktop("VAL")}}`` - version.version is set to
      ``"VAL"``, support.support is ``"yes"``.  and
      version.release_day is set by logic in CompatGeckoDesktop_.
    * ``{{CompatGeckoMobile("VAL")}}`` - version.version is set to
      ``"VAL"``, support.support is ``"yes"``.  is set by logic
      in CompatGeckoMobile_.
    * Numeric string, such as ``6``, ``15.0``.  This becomes the
      version.version, and support.support is
      ``"yes"``.
* **Content after table** - This is usually formatted as a paragraph,
  containing HTML.  It should become supports.footnotes,
  but it will challenging to auto-parse and associate.

Once the initial conversion has been done for a page, it may be useful to
perform additional steps:

1. Split large features_ into smaller ones.  For example,
   here's one way to reorganize `Web/CSS/display`_:

.. image:: ../../_static/canonicalized-display.svg
   :alt: Reorganization of Web/CSS/display
   :target: https://rawgit.com/jwhitlock/web-platform-compat/master/docs/_static/canonicalized-display.svg

Data sources for browser versions
---------------------------------

The **version** model currently supports a release date and a
retirement date, as well as other version data.  Some sources for this data
include:

* Google Chrome - `Google Chrome Release History`_ on Wikipedia
* Mozilla Firefox - `Firefox Release History`_ on Wikipedia and KumaScript
  macro CompatGeckoDesktop_
* Microsoft Internet Explorer - `Release History of IE`_ on Wikipedia
* Opera - `Current Opera version history`_ and `Presto history`_ on opera.com
* Safari - `Safari version history`_ on Wikipedia


To Do
-----

* Add multi-get to browser doc, after deciding on ``GET
  /versions/1,2,3,4`` vs.  ``GET /browser/1/versions``
* Look at additional MDN content for items in common use
* Move to developers.mozilla.org subpath, auth changes
* Jeremie's suggested changes (*italics are done*)
    * *Add browsers.notes, localized, to note things like engine, applicable
      OS, execution contexts (web workers, XUL, etc.).*
    * *Drop browsers.engine attribute.  Not important for searching or
      filtering, instead free text in browsers.notes*
    * *Add versions.notes, localized, to note things like OS, devices,
      engines, etc.*
    * *Drop versions.engine-version, not important for searching or
      sorting.*
    * Drop versions.status.  Doesn't think the MDN team will be able
      to keep up with browser releases.  Will instead rely on users
      figuring out if a browser version is the current release.
    * *Drop feature.canonical.  Instead, name="string" means it is
      canonical, and name={"lang": "translation"} means it is non-canonical.*
    * Feature-sets is a cloud, not a heirarchy.  "color=red" is the same
      feature as "background-color=red", so needs to be multiply assigned.
    * *A feature-set can either have sub-feature sets (middle of cloud), or
      features (edge of cloud).* - Note - implemented by merging features and
      feature sets.
    * *Add support-sets, to make positive assertions about
      a version supporting a feature-set.  Only negative assertions
      can be made based on features.* - Note - implemented by merging features
      and feature sets
    * Drop order of features by feature set.  Client will alpha-sort.
    * *supports.support, drop "prefixed" status.  If prefixed,
      support = 'yes', and prefix is set.*
    * Add examples of filtering (browser versions in 2010, firefox versions
      before version X).
* Holly's suggestions
    * Nail down the data, so she has something solid to build a UX on.
    * sheppy or jms will have experience with how users use tables and
      contribute to them, how frequently.
* Add history resources for specifications, etc.
* Add empty resource for deleted items?

.. _Resources: resources.html
.. _browsers: resources.html#browsers
.. _features: resources.html#features
.. _sections: resources.html#sections
.. _specifications: resources.html#specifications
.. _maturities: resources.html#maturities
.. _supports: resources.html#supports
.. _versions: resources.html#versions

.. _changesets: change-control#changesets
.. _users: change-control#users

.. _history: history.html
.. _historical_browsers: history.html#historical-browsers
.. _historical_versions: history.html#historical-versions

.. _`Browser Compatibility Data Architecture`: https://docs.google.com/document/d/1YF7GJ6kgV5_hx6SJjyrgunqznQU1mKxp5FaLAEzMDl4/edit#
.. _CompatGeckoDesktop: https://developer.mozilla.org/en-US/docs/Template:CompatGeckoDesktop
.. _CompatGeckoMobile: https://developer.mozilla.org/en-US/docs/Template:CompatGeckoMobile
.. _`CSS @font-face at-rule`: https://developer.mozilla.org/en-US/docs/Web/CSS/@font-face#Specifications
.. _`Bugzilla 119490`: https://bugzilla.mozilla.org/show_bug.cgi?id=119490
.. _`Bugzilla 1050458`: https://bugzilla.mozilla.org/show_bug.cgi?id=1050458
.. _`availability in Web Workers`: https://bugzilla.mozilla.org/show_bug.cgi?id=996570#c14
.. _`don't localize our brand`: http://www.mozilla.org/en-US/styleguide/communications/translation/#branding
.. _`Mapping browsers to 2.2.1 Dictionary Browser Members`: http://lists.w3.org/Archives/Public/public-webplatform-tests/2013OctDec/0007.html
.. _`Read a good blog post on the subject`: http://www.troyhunt.com/2014/02/your-api-versioning-is-wrong-which-is.html
.. _`Chrome release history`: http://en.wikipedia.org/wiki/Google_Chrome_complete_version_history#Release_history
.. _`Firefox release history`: http://en.wikipedia.org/wiki/Firefox_release_history#Release_history
.. _`SpecName`: https://developer.mozilla.org/en-US/docs/Template:SpecName
.. _`Spec2`: https://developer.mozilla.org/en-US/docs/Template:Spec2
.. _`Google Chrome Release History`: http://en.wikipedia.org/wiki/Google_Chrome#Release_history
.. _`Release History of IE`: http://en.wikipedia.org/wiki/Internet_Explorer_1#Release_history_for_desktop_Windows_OS_version
.. _`Current Opera version history`: http://www.opera.com/docs/history/
.. _`Presto history`: http://www.opera.com/docs/history/presto/
.. _`Safari version history`: http://en.wikipedia.org/wiki/Safari_version_history#Release_history

.. _`Web/API/IDBObjectStore`: https://developer.mozilla.org/en-US/docs/Web/API/IDBObjectStore#Specifications
.. _`Web/CSS/:invalid`: https://developer.mozilla.org/en-US/docs/Web/CSS/:invalid#Specifications
.. _`Web/CSS/@document`: https://developer.mozilla.org/en-US/docs/Web/CSS/@document#Specifications
.. _`Web/CSS/@font-face`: https://developer.mozilla.org/en-US/docs/Web/CSS/@font-face#Specifications
.. _`Web/CSS/animation-name`: https://developer.mozilla.org/en-US/docs/Web/CSS/animation-name#Specifications
.. _`Web/CSS/border-image-width`: http://developer.mozilla.org/en-US/docs/Web/CSS/border-image-width
.. _`Web/CSS/box-decoration-break`: https://developer.mozilla.org/en-US/docs/Web/CSS/box-decoration-break#Specifications
.. _`Web/CSS/box-sizing`: https://developer.mozilla.org/en-US/docs/Web/CSS/box-sizing#Specifications
.. _`Web/CSS/break-inside`: https://developer.mozilla.org/en-US/docs/Web/CSS/break-inside#Specifications
.. _`Web/CSS/caption-side`: https://developer.mozilla.org/en-US/docs/Web/CSS/caption-side#Specifications
.. _`Web/CSS/clip`: https://developer.mozilla.org/en-US/docs/Web/CSS/clip#Specifications
.. _`Web/CSS/cursor`: https://developer.mozilla.org/en-US/docs/Web/CSS/cursor#Specifications
.. _`Web/CSS/display`: https://developer.mozilla.org/en-US/docs/Web/CSS/display#Specifications
.. _`Web/CSS/length`: https://developer.mozilla.org/en-US/docs/Web/CSS/length#Browser_compatibility
.. _`Web/CSS/line-break`: https://developer.mozilla.org/en-US/docs/Web/CSS/line-break#Specifications
.. _`Web/CSS/min-height`: https://developer.mozilla.org/en-US/docs/Web/CSS/min-height#Specifications
.. _`Web/CSS/min-width`: https://developer.mozilla.org/en-US/docs/Web/CSS/min-width#Specifications
.. _`Web/CSS/outline-color`: https://developer.mozilla.org/en-US/docs/Web/CSS/outline-color#Specifications
.. _`Web/CSS/radial-gradient`: https://developer.mozilla.org/en-US/docs/Web/CSS/radial-gradient#Specifications
.. _`Web/CSS/ratio`: https://developer.mozilla.org/en-US/docs/Web/CSS/ratio#Specifications
.. _`Web/CSS/tab-size`: https://developer.mozilla.org/en-US/docs/Web/CSS/tab-size#Specifications
.. _`Web/CSS/text-align`: https://developer.mozilla.org/en-US/docs/Web/CSS/text-align#Specifications
.. _`Web/CSS/text-decoration-line`: https://developer.mozilla.org/en-US/docs/Web/CSS/text-decoration-line#Specifications
.. _`Web/CSS/text-rendering`: https://developer.mozilla.org/en-US/docs/Web/CSS/text-rendering#Specifications
.. _`Web/CSS/text-transform`: https://developer.mozilla.org/en-US/docs/Web/CSS/text-transform#Specifications
.. _`Web/CSS/text-underline-position`: https://developer.mozilla.org/en-US/docs/Web/CSS/text-underline-position#Specifications
.. _`Web/CSS/transform-origin`: https://developer.mozilla.org/en-US/docs/Web/CSS/transform-origin#Specifications
.. _`Web/HTML/Element/Input`: https://developer.mozilla.org/en-US/docs/Web/HTML/Element/Input#Browser_compatibility
.. _`Web/HTML/Element/address`: https://developer.mozilla.org/en-US/docs/Web/HTML/Element/address#Specifications
