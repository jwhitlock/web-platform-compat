# coding: utf-8
"""Test mdn.scrape."""
from __future__ import unicode_literals
from datetime import date
from json import dumps

from mdn.models import FeaturePage, TranslatedContent
from mdn.scrape import (
    date_to_iso, end_of_line, page_grammar, range_error_to_html, scrape_page,
    scrape_feature_page, slugify, PageVisitor)
from webplatformcompat.models import (
    Browser, Feature, Maturity, Section, Specification, Support, Version)
from webplatformcompat.tests.base import TestCase


class TestGrammar(TestCase):
    def test_specdesc_td_empty(self):
        text = '<td></td>'
        parsed = page_grammar['specdesc_td'].parse(text)
        capture = parsed.children[2]
        self.assertEqual('', capture.text)

    def test_specdesc_td_plain_text(self):
        text = '<td>Plain Text</td>'
        parsed = page_grammar['specdesc_td'].parse(text)
        capture = parsed.children[2]
        self.assertEqual('Plain Text', capture.text)

    def test_specdesc_td_html(self):
        text = "<td>Defines <code>right</code> as animatable.</td>"
        parsed = page_grammar['specdesc_td'].parse(text)
        capture = parsed.children[2]
        self.assertEqual(
            'Defines <code>right</code> as animatable.', capture.text)

    def assert_cell_version(self, text, version, eng_version=None):
        match = page_grammar['cell_version'].parse(text).match.groupdict()
        expected = {'version': version, 'eng_version': eng_version}
        self.assertEqual(expected, match)

    def test_cell_version_number(self):
        self.assert_cell_version("1", version="1")

    def test_cell_version_number_dotted(self):
        self.assert_cell_version("1.0", version="1.0")

    def test_cell_version_number_spaces(self):
        self.assert_cell_version("1 ", version="1")

    def test_cell_version_number_dotted_spaces(self):
        self.assert_cell_version("1.0\n\t", version="1.0")

    def test_cell_version_number_with_engine(self):
        self.assert_cell_version("1.0 (85)", version="1.0", eng_version="85")

    def test_cell_version_number_with_dotted_engine(self):
        self.assert_cell_version(
            "5.0 (532.5)", version="5.0", eng_version="532.5")


class ScrapeTestCase(TestCase):
    """Fixtures for scraping tests."""
    longMessage = True

    # Based on:
    # https://developer.mozilla.org/en-US/docs/Web/CSS/background-size?raw
    # but with fixes (id of <h2>, remove &nbsp;).
    simple_prefix = """\
<div>
 {{CSSRef}}</div>
"""
    simple_other_section = """\
<h2 id="Summary">Summary</h2>
<p>The <code>background-size</code> <a href="/en-US/docs/CSS" title="CSS">CSS\
</a> property specifies the size of the background images. The size of the\
 image can be fully constrained or only partially in order to preserve its\
 intrinsic ratio.</p>
<div class="note">
 <strong>Note:</strong> If the value of this property is not set in a\
 {{cssxref("background")}} shorthand property that is applied to the element\
 after the <code>background-size</code> CSS property, the value of this\
 property is then reset to its initial value by the shorthand property.</div>
<p>{{cssbox("background-size")}}</p>
"""
    simple_spec_section = """\
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
   <td>{{SpecName('CSS3 Backgrounds', '#the-background-size',\
 'background-size')}}</td>
   <td>{{Spec2('CSS3 Backgrounds')}}</td>
   <td></td>
  </tr>
 </tbody>
</table>
"""

    # From https://developer.mozilla.org/en-US/docs/Web/CSS/float?raw
    simple_compat_section = """\
<h2 id="Browser_compatibility">Browser compatibility</h2>
<div>
 {{CompatibilityTable}}</div>
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
    <td>1.0</td>
    <td>{{CompatGeckoDesktop("1")}}</td>
    <td>4.0</td>
    <td>7.0</td>
    <td>1.0</td>
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
    <th>IE Mobile</th>
    <th>Opera Mobile</th>
    <th>Safari Mobile</th>
   </tr>
   <tr>
    <td>Basic support</td>
    <td>1.0</td>
    <td>{{CompatGeckoMobile("1")}}</td>
    <td>6.0</td>
    <td>6.0</td>
    <td>1.0</td>
   </tr>
  </tbody>
 </table>
</div>
<p>&nbsp;</p>
"""
    # From Web/CSS/background-size?raw
    # colspan="3" on the Safari column
    # rowspan="2" on Basic Support row
    # footnotes with a <pre> section
    complex_compat_section = """\
<h2 id="Browser_compatibility" name="Browser_compatibility">\
Browser compatibility</h2>
<div>
 {{CompatibilityTable}}</div>
<div id="compat-desktop">
 <table class="compat-table">
  <tbody>
   <tr>
    <th>Feature</th>
    <th>Chrome</th>
    <th>Firefox (Gecko)</th>
    <th>Internet Explorer</th>
    <th>Opera</th>
    <th colspan="3">Safari (WebKit)</th>
   </tr>
   <tr>
    <td rowspan="2">Basic support</td>
    <td>1.0{{property_prefix("-webkit")}} [2]</td>
    <td>{{CompatGeckoDesktop("1.9.2")}}{{property_prefix("-moz")}} [4]</td>
    <td rowspan="2">9.0 [5]</td>
    <td>9.5{{property_prefix("-o")}}<br>
     with some bugs [1]</td>
    <td>3.0 (522){{property_prefix("-webkit")}}<br>
     but from an older CSS3 draft [2]</td>
   </tr>
   <tr>
    <td>3.0</td>
    <td>{{CompatGeckoDesktop("2.0")}}</td>
    <td>10.0</td>
    <td>4.1 (532)</td>
   </tr>
   <tr>
    <td>Support for<br>
     <code>contain</code> and <code>cover</code></td>
    <td>3.0</td>
    <td>{{CompatGeckoDesktop("1.9.2")}}</td>
    <td>9.0 [5]</td>
    <td>10.0</td>
    <td colspan="3">4.1 (532)</td>
   </tr>
   <tr>
    <td>Support for SVG backgrounds</td>
    <td>{{CompatUnknown}}</td>
    <td>{{CompatGeckoDesktop("8.0")}}</td>
    <td>{{CompatUnknown}}</td>
    <td>{{CompatUnknown}}</td>
    <td colspan="3">{{CompatUnknown}}</td>
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
    <th>Windows Phone</th>
    <th>Opera Mobile</th>
    <th>Safari Mobile</th>
   </tr>
   <tr>
    <td>Basic support</td>
    <td>{{CompatVersionUnknown}}{{property_prefix("-webkit")}}<br>
     2.3</td>
    <td>1.0{{property_prefix("-moz")}}<br>
     4.0</td>
    <td>{{CompatUnknown}}</td>
    <td>{{CompatUnknown}}</td>
    <td>5.1 (maybe earlier)</td>
   </tr>
   <tr>
    <td>Support for SVG backgrounds</td>
    <td>{{CompatUnknown}}</td>
    <td>{{CompatGeckoMobile("8.0")}}</td>
    <td>{{CompatUnknown}}</td>
    <td>{{CompatUnknown}}</td>
    <td>{{CompatUnknown}}</td>
   </tr>
  </tbody>
 </table>
</div>
"""
    complex_compat_footnotes = """\
<p>&nbsp;</p>
<p>[1] Opera 9.5's computation of the background positioning area is incorrect\
 for fixed backgrounds.  Opera 9.5 also interprets the two-value form as a\
 horizontal scaling factor and, from appearances, a vertical <em>clipping</em>\
 dimension. This has been fixed in Opera 10.</p>
<p>[2] WebKit-based browsers originally implemented an older draft of\
 CSS3<code> background-size </code>in which an omitted second value is treated\
 as <em>duplicating</em> the first value; this draft does not include\
 the<code> contain </code>or<code> cover </code>keywords.</p>
<p>[3] Konqueror 3.5.4 supports<code> -khtml-background-size</code>.</p>
<p>[4] While this property is new in Gecko 1.9.2 (Firefox 3.6), it is possible\
 to stretch a image fully over the background in Firefox 3.5 by using\
 {{cssxref("-moz-border-image")}}.</p>
<pre class="brush:css">.foo {
  background-image: url(bg-image.png);

  -webkit-background-size: 100% 100%;           /* Safari 3.0 */
     -moz-background-size: 100% 100%;           /* Gecko 1.9.2 (Firefox 3.6) */
       -o-background-size: 100% 100%;           /* Opera 9.5 */
          background-size: 100% 100%;           /* Gecko 2.0 (Firefox 4.0) and\
 other CSS3-compliant browsers */

  -moz-border-image: url(bg-image.png) 0;    /* Gecko 1.9.1 (Firefox 3.5) */
}</pre>
<p>[5] Though Internet Explorer 8 doesn't support the\
 <code>background-size</code> property, it is possible to emulate some of its\
 functionality using the non-standard <code>-ms-filter</code> function:</p>
<pre class="brush:css">-ms-filter:\
 "progid:DXImageTransform.Microsoft.AlphaImageLoader(\
src='path_relative_to_the_HTML_file', sizingMethod='scale')";</pre>
<p>This simulates the value <code>cover</code>.</p>
"""

    simple_see_also = """\
<h2 id="See_also">See also</h2>
<ul>
 <li>{{CSS_Reference:Position}}</li>
 <li><a href="/en-US/docs/Web/CSS/block_formatting_context">\
Block formatting context</a></li>
</ul>"""
    simple_page = (
        simple_prefix + simple_other_section + simple_spec_section +
        simple_compat_section + simple_see_also)
    complex_page = (
        simple_prefix + simple_other_section + simple_spec_section +
        complex_compat_section + complex_compat_footnotes + simple_see_also)

    def add_spec_models(self):
        self.maturity = self.create(
            Maturity, slug='CR', name='{"en": "Candidate Recommendation"}')
        self.spec = self.create(
            Specification, mdn_key='CSS3 Backgrounds',
            slug='css3_backgrounds', maturity=self.maturity,
            name='{"en": "CSS Backgrounds and Borders Module Level&nbsp;3"}',
            uri='{"en": "http://dev.w3.org/csswg/css3-background/"}')
        self.section = self.create(
            Section, specification=self.spec, name='{"en": "background-size"}',
            subpath='{"en": "#the-background-size"}')

    def add_compat_models(self):
        browsers = (
            ('Chrome', 'chrome'),
            ('Firefox', 'firefox'),
            ('Internet Explorer', 'ie'),
            ('Opera', 'opera'),
            ('Safari', 'safari'),
            ('Android', 'android'),
            ('Firefox Mobile', 'firefox-mobile'),
            ('IE Mobile', 'ie-mobile'),
            ('Opera Mobile', 'opera-mobile'),
            ('Safari Mobile', 'safari-mobile'),
        )
        self.browsers = dict()
        for name, slug in browsers:
            self.browsers[slug] = self.create(
                Browser, slug=slug, name={"en": name})

        versions = (
            ('android', ''),
            ('android', '1.0'),
            ('android', '2.3'),
            ('chrome', '1.0'),
            ('chrome', '3.0'),
            ('firefox', '1.0'),
            ('firefox', '3.6'),
            ('firefox', '4.0'),
            ('firefox', '8.0'),
            ('firefox-mobile', '1.0'),
            ('firefox-mobile', '4.0'),
            ('firefox-mobile', '8.0'),
            ('ie', '4.0'),
            ('ie', '9.0'),
            ('ie-mobile', '6.0'),
            ('opera', '10.0'),
            ('opera', '7.0'),
            ('opera', '9.5'),
            ('opera-mobile', '6.0'),
            ('safari', '1.0'),
            ('safari', '3.0'),
            ('safari', '4.1'),
            ('safari-mobile', '1.0'),
            ('safari-mobile', '5.1'),
        )
        self.versions = dict()
        for browser_slug, version in versions:
            browser = self.browsers[browser_slug]
            self.versions[(browser_slug, version)] = self.create(
                Version, browser=browser, version=version)

        if not hasattr(self, 'features'):
            self.add_compat_features()

    def add_compat_features(self):
        self.features = dict()
        self.features['web'] = self.create(
            Feature, slug='web', name={"en": "Web"})
        self.features['web-css'] = self.create(
            Feature, slug='web-css', name={"en": "CSS"},
            parent=self.features['web'])
        self.features['web-css-background-size'] = self.create(
            Feature, slug='web-css-background-size',
            name={"zxx": "background-size"})

    def add_models(self):
        self.add_spec_models()
        self.add_compat_models()


class TestEndOfLine(ScrapeTestCase):
    def test_middle_of_text(self):
        expected_eol = self.simple_page.index('\n', 30)
        end = end_of_line(self.simple_page, expected_eol - 2)
        self.assertEqual(expected_eol, end)

    def test_end_of_text(self):
        end = end_of_line(self.simple_page, len(self.simple_page) - 2)
        self.assertEqual(len(self.simple_page), end)


class TestPageVisitor(ScrapeTestCase):
    def setUp(self):
        self.add_compat_features()
        self.visitor = PageVisitor(self.features['web-css-background-size'])

    def test_cleanup_whitespace(self):
        text = """ This
        text <br/>
        has\t lots\xa0of
        extra&nbsp;whitespace.
        """
        expected = "This text has lots of extra whitespace."
        self.assertEqual(expected, self.visitor.cleanup_whitespace(text))

    def test_specname_3_arg(self):
        self.add_spec_models()
        text = '<td>{{SpecName("CSS3 Backgrounds", "#subpath", "Name")}}</td>'
        parsed = page_grammar['specname_td'].parse(text)
        specname = self.visitor.visit(parsed)
        expected = ('CSS3 Backgrounds', self.spec.id, "#subpath", "Name")
        self.assertEqual(expected, specname)

    def test_specname_1_arg(self):
        # https://developer.mozilla.org/en-US/docs/Web/API/DeviceMotionEvent
        text = '<td>{{SpecName("Device Orientation")}}</td>'
        parsed = page_grammar['specname_td'].parse(text)
        specname = self.visitor.visit(parsed)
        expected = ("Device Orientation", None, '', '')
        self.assertEqual(expected, specname)

    def test_specname_spec2_mismatch(self):
        text = '''\
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
   <td>{{ SpecName('CSS3 UI', '#cursor', 'cursor') }}</td>
   <td>{{ Spec2('CSS3 Basic UI') }}</td>
   <td>Addition of several keywords and the positioning syntax for\
 <code>url()</code>.</td>
  </tr>
 </tbody>
</table>'''
        parsed = page_grammar['spec_table'].parse(text)
        self.visitor.visit(parsed)
        expected = [{
            'section.note': (
                'Addition of several keywords and the positioning syntax for'
                ' <code>url()</code>.'),
            'section.subpath': '#cursor',
            'section.name': 'cursor',
            'specification.mdn_key': 'CSS3 UI',
            'section.id': None,
            'specification.id': None}]
        self.assertEqual(expected, self.visitor.specs)
        errors = [
            (185, 240, 'Unknown Specification "CSS3 UI"'),
            (177, 383,
             'SpecName(CSS3 Basic UI, ...) does not match Spec2(CSS3 UI)')]
        self.assertEqual(errors, self.visitor.errors)

    def test_specname_commas_in_link(self):
        # https://developer.mozilla.org/en-US/docs/Web/HTML/Element
        #  /Heading_Elements
        text = '''\
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
   <td>{{SpecName('HTML WHATWG',\
 'sections.html#the-h1,-h2,-h3,-h4,-h5,-and-h6-elements',\
 '&lt;h1&gt;, &lt;h2&gt;, &lt;h3&gt;, &lt;h4&gt;, &lt;h5&gt;, and &lt;h6&gt;'\
 )}}</td>
   <td>{{Spec2('HTML WHATWG')}}</td>
   <td>&nbsp;</td>
  </tr>
 </tbody>
</table>
'''
        parsed = page_grammar['spec_table'].parse(text)
        self.visitor.visit(parsed)
        expected = [{
            'section.note': '',
            'section.subpath': (
                'sections.html#the-h1,-h2,-h3,-h4,-h5,-and-h6-elements'),
            'section.name': (
                '&lt;h1&gt;, &lt;h2&gt;, &lt;h3&gt;, &lt;h4&gt;, &lt;h5&gt;,'
                ' and &lt;h6&gt;'),
            'specification.mdn_key': 'HTML WHATWG',
            'section.id': None,
            'specification.id': None}]
        self.assertEqual(expected, self.visitor.specs)
        errors = [(185, 357, 'Unknown Specification "HTML WHATWG"')]
        self.assertEqual(errors, self.visitor.errors)

    def test_spec_no_thead(self):
        # https://developer.mozilla.org/en-US/docs/Web/API/AudioContext
        text = '''\
<table class="standard-table">
 <tbody>
  <tr>
   <th scope="col">Specification</th>
   <th scope="col">Status</th>
   <th scope="col">Comment</th>
  </tr>
  <tr>
   <td>{{SpecName('Web Audio API', '#the-audiocontext-interface',\
 'AudioContext')}}</td>
   <td>{{Spec2('Web Audio API')}}</td>
   <td>&nbsp;</td>
  </tr>
 </tbody>
</table>
'''
        parsed = page_grammar['spec_table'].parse(text)
        self.visitor.visit(parsed)
        expected = [{
            'section.note': '',
            'section.subpath': '#the-audiocontext-interface',
            'section.name': 'AudioContext',
            'specification.mdn_key': 'Web Audio API',
            'section.id': None,
            'specification.id': None}]
        self.assertEqual(expected, self.visitor.specs)
        errors = [(166, 251, 'Unknown Specification "Web Audio API"')]
        self.assertEqual(errors, self.visitor.errors)

    def test_compat_row_cell_feature_with_rowspan(self):
        text = '<td rowspan="2">Some Feature</td>'
        parsed = page_grammar['compat_row_cell'].parse(text)
        expected_cell = [{
            'type': 'td',
            'rowspan': '2',
        }, {
            'type': 'text',
            'content': 'Some Feature',
            'start': 16,
            'end': 28
        }]
        cell = self.visitor.visit(parsed)
        self.assertEqual(expected_cell, cell)
        expected_feature = {
            'id': '_some feature',
            'name': 'Some Feature',
            'slug': 'web-css-background-size_some_feature',
        }
        feature = self.visitor.cell_to_feature(cell)
        self.assertEqual(expected_feature, feature)

    def test_compat_row_cell_with_unknown_attr(self):
        text = '<td class="freaky">Some Feature</td>'
        parsed = page_grammar['compat_row_cell'].parse(text)
        expected_cell = [{
            'type': 'td',
        }, {
            'type': 'text',
            'content': 'Some Feature',
            'start': 19,
            'end': 31
        }]
        cell = self.visitor.visit(parsed)
        self.assertEqual(expected_cell, cell)

    def test_compat_row_cell_feature_name_lookup(self):
        texts = [
            '<td>Some Feature</td>',
            '<td>some feature</td>',
            '<td rowspan="2">Some<br/>feature</td>',
            '<td>SOME {{experimental_inline}} FEATURE</td>',
            '<td><code>some feature</code></td>',
        ]
        expected_id = '_some feature'
        expected_slug = 'web-css-background-size_some_feature'
        for text in texts:
            parsed = page_grammar['compat_row_cell'].parse(text)
            cell = self.visitor.visit(parsed)
            feature = self.visitor.cell_to_feature(cell)
            self.assertEqual(expected_id, feature['id'], text)
            self.assertEqual(expected_slug, feature['slug'], text)

    def test_compat_row_cell_feature_match_canonical(self):
        feature = self.create(
            Feature, parent=self.visitor.feature,
            name={'zxx': 'feature'}, slug='feature-slug')
        text = '<td><code>feature</code></td>'
        parsed = page_grammar['compat_row_cell'].parse(text)
        cell = self.visitor.visit(parsed)
        parsed_feature = self.visitor.cell_to_feature(cell)
        self.assertEqual(parsed_feature['id'], feature.id)
        self.assertEqual(parsed_feature['slug'], feature.slug)

    def assert_compat_row_cell_feature(
            self, contents, expected_feature,
            expected_issues=[], expected_errors=[]):
        """Generic tests for compat_row_cell visitor as feature"""
        text = "<td>%s</td>" % contents
        parsed = page_grammar['compat_row_cell'].parse(text)
        cell = self.visitor.visit(parsed)
        feature = self.visitor.cell_to_feature(cell)
        self.assertEqual(expected_feature, feature)
        self.assertEqual(expected_issues, self.visitor.issues)
        self.assertEqual(expected_errors, self.visitor.errors)

    def test_compat_row_cell_feature_remove_whitespace(self):
        text = (
            ' Support for<br>\n     <code>contain</code> and'
            ' <code>cover</code> ')
        expected_feature = {
            'id': '_support for contain and cover',
            'name': 'Support for <code>contain</code> and <code>cover</code>',
            'slug': 'web-css-background-size_support_for_contain_and_co',
        }
        self.assert_compat_row_cell_feature(text, expected_feature)

    def test_compat_row_cell_feature_code_sequence(self):
        # <code> split by commas is special cased
        text = (
            '<code>none</code>, <code>inline</code> and'
            ' <code>block</code>')
        expected_feature = {
            'id': '_none, inline and block',
            'name': (
                '<code>none</code>, <code>inline</code> and'
                ' <code>block</code>'),
            'slug': 'web-css-background-size_none_inline_and_block'
        }
        self.assert_compat_row_cell_feature(text, expected_feature)

    def test_compat_row_cell_feature_canonical(self):
        text = '<code>list-item</code>'
        expected_feature = {
            'id': '_list-item',
            'name': 'list-item',
            'canonical': True,
            'slug': 'web-css-background-size_list-item',
        }
        self.assert_compat_row_cell_feature(text, expected_feature)

    def test_compat_row_cell_feature_experimental(self):
        text = '<code>grid</code> {{experimental_inline}}'
        expected_feature = {
            'id': '_grid',
            'name': 'grid',
            'canonical': True,
            'experimental': True,
            'slug': 'web-css-background-size_grid',
        }
        self.assert_compat_row_cell_feature(text, expected_feature)

    def test_compat_row_cell_feature_non_standard(self):
        # https://developer.mozilla.org/en-US/docs/Web/API/AnimationEvent
        text = '<code>initAnimationEvent()</code> {{non-standard_inline}}'
        expected_feature = {
            'id': '_initanimationevent()',
            'name': 'initAnimationEvent()',
            'canonical': True,
            'standardized': False,
            'slug': 'web-css-background-size_initanimationevent_',
        }
        self.assert_compat_row_cell_feature(text, expected_feature)

    def test_compat_row_cell_feature_deprecated(self):
        text = '<code>initAnimationEvent()</code> {{deprecated_inline}}'
        expected_feature = {
            'id': '_initanimationevent()',
            'name': 'initAnimationEvent()',
            'canonical': True,
            'obsolete': True,
            'slug': 'web-css-background-size_initanimationevent_',
        }
        self.assert_compat_row_cell_feature(text, expected_feature)

    def test_compat_row_cell_feature_htmlelement(self):
        text = '{{ HTMLElement("progress") }}'
        expected_feature = {
            'id': '_&lt;progress&gt;',
            'name': '&lt;progress&gt;',
            'canonical': True,
            'slug': 'web-css-background-size_lt_progress_gt_',
        }
        self.assert_compat_row_cell_feature(text, expected_feature)

    def test_compat_row_cell_feature_domxref(self):
        text = '{{domxref("DeviceProximityEvent")}}'
        expected_feature = {
            'id': '_deviceproximityevent',
            'name': 'DeviceProximityEvent',
            'slug': 'web-css-background-size_deviceproximityevent',
        }
        self.assert_compat_row_cell_feature(text, expected_feature)

    def test_compat_row_cell_feature_unknown_kuma(self):
        text = 'feature foo {{bar}}'
        feature = {
            'id': '_feature foo', 'name': 'feature foo',
            'slug': 'web-css-background-size_feature_foo',
        }
        expected_errors = [(16, 23, 'Unknown kuma function bar')]
        self.assert_compat_row_cell_feature(
            text, feature, expected_errors=expected_errors)

    def test_compat_row_cell_feature_unknown_kuma_with_args(self):
        text = 'foo {{bar("baz")}}'
        feature = {
            'id': '_foo', 'name': 'foo', 'slug': 'web-css-background-size_foo'}
        expected_errors = [(8, 22, 'Unknown kuma function bar(baz)')]
        self.assert_compat_row_cell_feature(
            text, feature, expected_errors=expected_errors)

    def test_compat_row_cell_feature_nonascii_name(self):
        # https://developer.mozilla.org/en-US/docs/Web/CSS/font-variant
        text = '<code>ß</code> → <code>SS</code>'
        feature = {
            'id': '_\xdf \u2192 ss',
            'name': '<code>\xdf</code> \u2192 <code>SS</code>',
            'slug': 'web-css-background-size_ss'}
        self.assert_compat_row_cell_feature(text, feature)

    def test_compat_row_cell_feature_footnote(self):
        # https://developer.mozilla.org/en-US/docs/Web/CSS/text-align
        text = 'Block alignment values [1] {{not_standard_inline}}'
        feature = {
            'id': '_block alignment values',
            'name': 'Block alignment values',
            'standardized': False,
            'slug': 'web-css-background-size_block_alignment_values'
        }
        errors = [(27, 31, "Footnotes are not allowed on features")]
        self.assert_compat_row_cell_feature(
            text, feature, expected_errors=errors)

    def test_compat_row_cell_feature_digit(self):
        # https://developer.mozilla.org/en-US/docs/Web/CSS/transform
        text = '3D Support'
        feature = {
            'id': '_3d support',
            'name': '3D Support',
            'slug': 'web-css-background-size_3d_support'
        }
        self.assert_compat_row_cell_feature(text, feature)

    def test_cell_to_feature_unknown_item(self):
        bad_cell = [{
            'type': 'td',
        }, {
            'type': 'other',
        }]
        self.assertRaises(ValueError, self.visitor.cell_to_feature, bad_cell)

    def test_cell_to_support_unknown_item(self):
        feature = {'id': '_feature', 'name': 'feature', 'slug': 'feature_slug'}
        browser = {'id': '_browser', 'name': 'Browser', 'slug': 'browser'}
        bad_cell = [{'type': 'td'}, {'type': 'other'}]
        self.assertRaises(
            ValueError, self.visitor.cell_to_support, bad_cell, feature,
            browser)

    def test_compat_row_cell_support_matched_version(self):
        browser = self.create(Browser, name={'en': 'Browser'}, slug='browser')
        version = self.create(Version, version='1.0', browser=browser)
        feature = self.create(
            Feature, name={'en': 'feature'}, slug='feature_slug',
            parent=self.features['web-css-background-size'])

        feature_rep = {
            'id': feature.id,
            'name': 'feature',
            'slug': 'feature_slug',
        }
        browser_rep = {
            'id': browser.id,
            'name': 'Browser',
            'slug': 'browser',
        }
        text = "<td>1.0</td>"
        parsed = page_grammar['compat_row_cell'].parse(text)
        cell = self.visitor.visit(parsed)
        versions, supports = self.visitor.cell_to_support(
            cell, feature_rep, browser_rep)
        expected_versions = [{
            'id': version.id,
            'version': version.version,
            'browser': browser.id,
        }]
        self.assertEqual(expected_versions, versions)
        expected_supports = [{
            'id': '_%s-%s' % (feature.id, version.id),
            'support': "yes",
            'version': version.id,
            'feature': feature.id
        }]
        self.assertEqual(expected_supports, supports)
        self.assertEqual([], self.visitor.issues)
        self.assertEqual([], self.visitor.errors)

    def test_compat_row_cell_support_unknown_version(self):
        browser = self.create(Browser, name={'en': 'Browser'}, slug='browser')

        feature_rep = {
            'id': '_feature',
            'name': 'feature',
            'slug': 'feature_slug',
        }
        browser_rep = {
            'id': browser.id,
            'name': 'Browser',
            'slug': 'browser',
        }
        text = "<td>1.0</td>"
        parsed = page_grammar['compat_row_cell'].parse(text)
        cell = self.visitor.visit(parsed)
        versions, supports = self.visitor.cell_to_support(
            cell, feature_rep, browser_rep)
        expected_versions = [{
            'id': '_Browser-1.0',
            'version': '1.0',
            'browser': browser.id,
        }]
        self.assertEqual(expected_versions, versions)
        expected_supports = [{
            'id': '__feature-_Browser-1.0',
            'support': "yes",
            'version': '_Browser-1.0',
            'feature': '_feature'
        }]
        self.assertEqual(expected_supports, supports)
        self.assertEqual([], self.visitor.issues)
        expected_errors = [
            (4, 7,
             'Unknown version "1.0" for browser "Browser" (id %d, slug "%s")'
             % (browser.id, 'browser'))]
        self.assertEqual(expected_errors, self.visitor.errors)

    def test_compat_row_cell_support_matched_support(self):
        browser = self.create(Browser, name={'en': 'Browser'}, slug='browser')
        version = self.create(Version, version='1.0', browser=browser)
        feature = self.create(
            Feature, name={'en': 'feature'}, slug='feature_slug',
            parent=self.features['web-css-background-size'])
        support = self.create(Support, version=version, feature=feature)

        feature_rep = {
            'id': feature.id, 'name': 'feature', 'slug': 'feature_slug'}
        browser_rep = {
            'id': browser.id, 'name': 'Browser', 'slug': 'browser'}
        text = "<td>1.0</td>"
        parsed = page_grammar['compat_row_cell'].parse(text)
        cell = self.visitor.visit(parsed)
        versions, supports = self.visitor.cell_to_support(
            cell, feature_rep, browser_rep)
        expected_versions = [{
            'id': version.id,
            'version': version.version,
            'browser': browser.id,
        }]
        self.assertEqual(expected_versions, versions)
        expected_supports = [{
            'id': support.id,
            'support': "yes",
            'version': version.id,
            'feature': feature.id
        }]
        self.assertEqual(expected_supports, supports)
        self.assertEqual([], self.visitor.issues)
        self.assertEqual([], self.visitor.errors)

    def test_compat_row_cell_support_compatversionunknown_vmatch(self):
        browser = self.create(Browser, name={'en': 'Browser'}, slug='browser')
        version = self.create(Version, version='', browser=browser)
        feature = self.create(
            Feature, name={'en': 'feature'}, slug='feature_slug',
            parent=self.features['web-css-background-size'])
        feature_rep = {'id': feature.id, 'name': 'feature', 'slug': 'f_slug'}
        browser_rep = {'id': browser.id, 'name': 'Browser', 'slug': 'b_slug'}
        text = "<td>{{CompatVersionUnknown}}</td>"
        parsed = page_grammar['compat_row_cell'].parse(text)
        cell = self.visitor.visit(parsed)
        versions, supports = self.visitor.cell_to_support(
            cell, feature_rep, browser_rep)
        expected_versions = [{
            'id': version.id,
            'browser': browser.id,
            'version': '',
        }]
        self.assertEqual(expected_versions, versions)
        expected_supports = [{
            'id': '_%s-%s' % (feature.id, version.id),
            'version': version.id,
            'feature': feature.id,
            'support': "yes",
        }]
        self.assertEqual(expected_supports, supports)
        self.assertEqual([], self.visitor.issues)
        self.assertEqual([], self.visitor.errors)

    def assert_compat_row_cell_support(
            self, contents, expected_versions=[], expected_supports=[],
            expected_issues=[], expected_errors=[]):
        """Generic tests for compat_row_cell visitor"""
        feature = {'id': '_feature', 'name': 'feature', 'slug': 'feature_slug'}
        browser = {'id': '_browser', 'name': 'Browser', 'slug': 'browser'}
        text = "<td>%s</td>" % contents
        parsed = page_grammar['compat_row_cell'].parse(text)
        cell = self.visitor.visit(parsed)
        versions, supports = self.visitor.cell_to_support(
            cell, feature, browser)
        for ev in expected_versions:
            assert 'id' not in ev
            assert 'browser' not in ev
            ev['id'] = '_%s-%s' % (browser['name'], ev['version'])
            ev['browser'] = browser['id']
        self.assertEqual(expected_versions, versions)
        for i, es in enumerate(expected_supports):
            version = expected_versions[i]
            assert 'id' not in es
            assert 'version' not in es
            assert 'feature' not in es
            es['id'] = '_%s-%s' % (feature['id'], version['id'])
            es['version'] = version['id']
            es['feature'] = feature['id']
        self.assertEqual(expected_supports, supports)
        self.assertEqual(expected_issues, self.visitor.issues)
        self.assertEqual(expected_errors, self.visitor.errors)

    def test_compat_row_cell_support_version(self):
        self.assert_compat_row_cell_support(
            '1.0',
            [{'version': '1.0'}], [{'support': 'yes'}])

    def test_compat_row_cell_support_compatno(self):
        self.assert_compat_row_cell_support(
            '{{CompatNo}}',
            [{'version': ''}], [{'support': 'no'}])

    def test_compat_row_cell_support_compatversionunknown(self):
        self.assert_compat_row_cell_support(
            '{{CompatVersionUnknown}}',
            [{'version': ''}], [{'support': 'yes'}])

    def test_compat_row_cell_support_compatunknown(self):
        self.assert_compat_row_cell_support('{{CompatUnknown}}', [], [])

    def test_compat_row_cell_support_compatgeckodesktop_10(self):
        self.assert_compat_row_cell_support(
            '{{CompatGeckoDesktop("1")}}',
            [{'version': '1.0'}], [{'support': 'yes'}])

    def test_compat_row_cell_support_compatgeckodesktop_8(self):
        self.assert_compat_row_cell_support(
            '{{CompatGeckoDesktop("8.0")}}',
            [{'version': '8.0'}], [{'support': 'yes'}])

    def test_compat_row_cell_support_compatgeckodesktop_bad_text(self):
        self.assert_compat_row_cell_support(
            '{{CompatGeckoDesktop("Yep")}}',
            expected_errors=[(4, 33, 'Unknown Gecko version "Yep"')])

    def test_compat_row_cell_support_compatgeckodesktop_bad_num(self):
        self.assert_compat_row_cell_support(
            '{{CompatGeckoDesktop("1.1")}}',
            expected_errors=[(4, 33, 'Unknown Gecko version "1.1"')])

    def test_compat_row_cell_support_compatgeckomobile_1(self):
        self.assert_compat_row_cell_support(
            '{{CompatGeckoMobile("1")}}',
            [{'version': '1.0'}], [{'support': 'yes'}])

    def test_compat_row_cell_support_compatgeckomobile_1_11(self):
        self.assert_compat_row_cell_support(
            '{{CompatGeckoMobile("1.11")}}',
            [{'version': '1.0'}], [{'support': 'yes'}])

    def test_compat_row_cell_support_compatgeckomobile_2(self):
        self.assert_compat_row_cell_support(
            '{{CompatGeckoMobile("2")}}',
            [{'version': '4.0'}], [{'support': 'yes'}])

    def test_compat_row_cell_support_compatandroid_3(self):
        self.assert_compat_row_cell_support(
            '{{CompatAndroid("3.0")}}',
            [{'version': '3.0'}], [{'support': 'yes'}])

    def test_compat_row_cell_support_unknown_kuma(self):
        self.assert_compat_row_cell_support(
            '{{UnknownKuma}}',
            expected_errors=[(4, 19, "Unknown kuma function UnknownKuma")])

    def test_compat_row_cell_support_unknown_kuma_args(self):
        self.assert_compat_row_cell_support(
            '{{UnknownKuma("foo")}}',
            expected_errors=[
                (4, 26, 'Unknown kuma function UnknownKuma(foo)')])

    def test_compat_row_cell_support_nested_p(self):
        self.assert_compat_row_cell_support(
            '<p><p>4.0</p></p>',
            expected_errors=[
                (7, 10, 'Nested <p> tags not supported')])

    def test_compat_row_cell_support_with_prefix_and_break(self):
        self.assert_compat_row_cell_support(
            ('{{CompatVersionUnknown}}{{property_prefix("-webkit")}}<br>\n'
             '   2.3'),
            [{'version': ''}, {'version': '2.3'}],
            [{'support': 'yes', 'prefix': '-webkit'}, {'support': 'yes'}])

    def test_compat_row_cell_support_p_tags(self):
        self.assert_compat_row_cell_support(
            '<p>4.0</p><p>32</p>',
            [{'version': '4.0'}, {'version': '32.0'}],
            [{'support': 'yes'}, {'support': 'yes'}])

    def test_compat_row_cell_two_line_note(self):
        self.assert_compat_row_cell_support(
            '18<br>\n(behind a pref) [1]',
            [{'version': '18.0'}],
            [{'support': 'yes', 'footnote_id': ('1', 27, 30)}],
            expected_errors=[
                (11, 27, 'Unknown support text "(behind a pref)"')])

    def test_compat_row_cell_support_removed_in_gecko(self):
        self.assert_compat_row_cell_support(
            ('{{ CompatGeckoMobile("6.0") }}<br>'
             'Removed in {{ CompatGeckoMobile("23.0") }}'),
            [{'version': '6.0'}, {'version': '23.0'}],
            [{'support': 'yes'}, {'support': 'no'}])

    def test_compat_row_cell_support_removed_in_version(self):
        self.assert_compat_row_cell_support(
            'Removed in 32',
            [{'version': '32.0'}], [{'support': 'no'}])

    def test_compat_row_cell_support_unmatched_free_text(self):
        self.assert_compat_row_cell_support(
            '32 (unprefixed)',
            [{'version': '32.0'}], [{'support': 'yes'}],
            expected_errors=[
                (7, 19, 'Unknown support text "(unprefixed)"')])

    def test_compat_row_cell_support_code_block(self):
        # https://developer.mozilla.org/en-US/docs/Web/CSS/order
        self.assert_compat_row_cell_support(
            '32 with alt name <code>foobar</code>',
            [{'version': '32.0'}], [{'support': 'yes'}],
            expected_errors=[
                (7, 21, 'Unknown support text "with alt name"'),
                (21, 40, 'Unknown support text <code>foobar</code>')])

    def test_compat_row_cell_support_spaces(self):
        self.assert_compat_row_cell_support('  ')

    def test_compat_row_cell_support_prefix_plus_footnote(self):
        self.assert_compat_row_cell_support(
            '18{{property_prefix("-webkit")}} [1]',
            [{'version': '18.0'}],
            [{'support': 'partial', 'prefix': '-webkit',
              'footnote_id': ('1', 37, 40)}])

    def test_compat_row_cell_support_prefix_double_footnote(self):
        # https://developer.mozilla.org/en-US/docs/Web/API/CSSSupportsRule
        self.assert_compat_row_cell_support(
            '{{ CompatGeckoDesktop("17") }} [1][2]',
            [{'version': '17.0'}],
            [{'support': 'yes', 'footnote_id': ('1', 35, 38)}],
            expected_errors=[
                (38, 41, 'Only one footnote allowed.')])

    def test_compat_row_cell_support_nbsp(self):
        self.assert_compat_row_cell_support(
            '15&nbsp;{{property_prefix("webkit")}}',
            [{'version': '15.0'}], [{'support': 'yes', 'prefix': 'webkit'}])

    def test_complex_footnotes_empty(self):
        text = "\n"
        parsed = page_grammar['compat_footnotes'].parse(text)
        expected = {}
        self.assertEqual(expected, self.visitor.visit(parsed))

    def test_compat_footnotes_simple(self):
        text = "<p>[1] A footnote.</p>"
        parsed = page_grammar['compat_footnotes'].parse(text)
        expected = {'1': ('A footnote.', 0, 22)}
        self.assertEqual(expected, self.visitor.visit(parsed))

    def test_compat_footnotes_multi_paragraph(self):
        text = "<p>[1] Footnote line 1.</p><p>Footnote line 2.</p>"
        parsed = page_grammar['compat_footnotes'].parse(text)
        expected = {
            '1': ('<p>Footnote line 1.</p>\n<p>Footnote line 2.</p>', 0, 50)}
        self.assertEqual(expected, self.visitor.visit(parsed))

    def test_compat_footnotes_multiple_footnotes(self):
        text = "<p>[1] Footnote 1.</p><p>[2] Footnote 2.</p>"
        parsed = page_grammar['compat_footnotes'].parse(text)
        expected = {
            '1': ('Footnote 1.', 0, 22),
            '2': ('Footnote 2.', 22, 44),
        }
        self.assertEqual(expected, self.visitor.visit(parsed))

    def test_compat_footnotes_kuma_cssxref(self):
        text = '<p>[1] Use {{cssxref("-moz-border-image")}}</p>'
        parsed = page_grammar['compat_footnotes'].parse(text)
        expected = {
            '1': ('Use <code>-moz-border-image</code>', 0, 47),
        }
        self.assertEqual(expected, self.visitor.visit(parsed))

    def test_compat_footnotes_unknown_kumascript(self):
        text = "<p>[1] Footnote {{UnknownKuma}} but the beat continues.</p>"
        parsed = page_grammar['compat_footnotes'].parse(text)
        expected = {
            '1': ('Footnote  but the beat continues.', 0, 59)}
        self.assertEqual(expected, self.visitor.visit(parsed))
        expected_errors = [
            (16, 31, "Unknown footnote kuma function UnknownKuma")]
        self.assertEqual(expected_errors, self.visitor.errors)

    def test_compat_footnotes_unknown_kumascript_with_args(self):
        text = '<p>[1] Footnote {{UnknownKuma("arg")}}</p>'
        parsed = page_grammar['compat_footnotes'].parse(text)
        expected = {'1': ('Footnote ', 0, 42)}
        self.assertEqual(expected, self.visitor.visit(parsed))
        expected_errors = [
            (16, 38, 'Unknown footnote kuma function UnknownKuma("arg")')]
        self.assertEqual(expected_errors, self.visitor.errors)

    def test_compat_footnotes_pre_section(self):
        text = '<p>[1] Here\'s some code:</p><pre>foo = bar</pre>'
        parsed = page_grammar['compat_footnotes'].parse(text)
        expected = {
            '1': ("<p>Here's some code:</p>\n<pre>foo = bar</pre>", 0, 48)}
        self.assertEqual(expected, self.visitor.visit(parsed))

    def test_compat_footnotes_pre_with_attrs_section(self):
        text = (
            '<p>[1] Here\'s some code:</p>\n'
            '<pre class="brush:css">\n'
            '.foo {background-image: url(bg-image.png);}\n'
            '</pre>')
        parsed = page_grammar['compat_footnotes'].parse(text)
        expected = {
            '1': (
                "<p>Here's some code:</p>\n<pre class=\"brush:css\">\n"
                ".foo {background-image: url(bg-image.png);}\n</pre>",
                0, 103),
        }
        self.assertEqual(expected, self.visitor.visit(parsed))

    def test_compat_footnotes_complex_page(self):
        text = self.complex_compat_footnotes
        parsed = page_grammar['compat_footnotes'].parse(text)
        # Full return is in TestScrape.test_complex_page_with_data
        self.assertEqual(5, len(self.visitor.visit(parsed)))

    def test_compat_footnotes_bad_footnote(self):
        text = "<p>A footnote.</p>"
        parsed = page_grammar['compat_footnotes'].parse(text)
        expected = {}
        self.assertEqual(expected, self.visitor.visit(parsed))
        errors = [(0, 18, 'No ID in footnote.')]
        self.assertEqual(errors, self.visitor.errors)

    def assert_kuma(self, text, name, args, errors=None):
        parsed = page_grammar['kuma'].parse(text)
        expected = {
            'type': 'kuma', 'name': name, 'args': args,
            'start': 0, 'end': len(text)}
        self.assertEqual(expected, self.visitor.visit(parsed))
        self.assertEqual(errors or [], self.visitor.errors)

    def test_kuma_no_parens(self):
        self.assert_kuma('{{CompatNo}}', 'CompatNo', [])

    def test_kuma_no_parens_and_spaces(self):
        self.assert_kuma('{{ CompatNo }}', 'CompatNo', [])

    def test_kuma_empty_parens(self):
        self.assert_kuma('{{CompatNo()}}', 'CompatNo', [])

    def test_kuma_one_arg(self):
        self.assert_kuma(
            '{{cssxref("-moz-border-image")}}', 'cssxref',
            ['-moz-border-image'])

    def test_kuma_one_arg_no_quotes(self):
        self.assert_kuma(
            '{{CompatGeckoDesktop(27)}}', 'CompatGeckoDesktop', ['27'])

    def test_kuma_three_args(self):
        self.assert_kuma(
            ("{{SpecName('CSS3 Backgrounds', '#the-background-size',"
             " 'background-size')}}"),
            "SpecName",
            ["CSS3 Backgrounds", "#the-background-size",
             "background-size"])

    def test_unquote_double(self):
        self.assertEqual('foo', self.visitor.unquote('"foo"'))

    def test_unquote_single(self):
        self.assertEqual('foo', self.visitor.unquote("'foo'"))

    def test_unquote_no_quote(self):
        self.assertEqual('27', self.visitor.unquote("27"))

    def test_unquote_unbalanced(self):
        self.assertRaises(ValueError, self.visitor.unquote, "'Mixed\"")


class TestScrape(ScrapeTestCase):
    def setUp(self):
        self.add_compat_features()

    def assertScrape(self, page, expected):
        """Specialize assertion for scraping"""
        actual = scrape_page(page, self.features['web-css-background-size'])
        exp_issues = expected.pop('issues')
        act_issues = actual.pop('issues')
        exp_errors = expected.pop('errors')
        act_errors = actual.pop('errors')
        self.assertDataEqual(expected, actual)
        self.assertEqual(len(exp_issues), len(act_issues), act_issues)
        self.assertEqual(len(exp_errors), len(act_errors), act_errors)
        for exp_issue, act_issue in zip(exp_issues, act_issues):
            self.assertEqual(
                exp_issue, act_issue, range_error_to_html(page, *act_issue))
        for exp_error, act_error in zip(exp_errors, act_errors):
            self.assertEqual(
                exp_error, act_error, range_error_to_html(page, *act_error))

    def test_empty(self):
        out = scrape_page("", self.features['web-css-background-size'])
        expected = {
            'locale': 'en',
            'specs': [],
            'compat': [],
            'footnotes': None,
            'issues': [],
            'errors': ["No <h2> found in page"],
        }
        self.assertDataEqual(out, expected)

    def test_spec_only(self):
        """Test with a only a Specification section."""
        expected = {
            'locale': 'en',
            'specs': [{
                'specification.mdn_key': 'CSS3 Backgrounds',
                'specification.id': None,
                'section.subpath': '#the-background-size',
                'section.name': 'background-size',
                'section.note': '',
                'section.id': None,
            }],
            'compat': [],
            'footnotes': None,
            'issues': [],
            'errors': [
                (251, 335, 'Unknown Specification "CSS3 Backgrounds"'),
            ]
        }
        self.assertScrape(self.simple_spec_section, expected)

    def test_simple_page(self):
        """Test with a more complete but simple page."""
        expected = {
            'locale': 'en',
            'specs': [{
                'specification.mdn_key': 'CSS3 Backgrounds',
                'specification.id': None,
                'section.subpath': '#the-background-size',
                'section.name': 'background-size',
                'section.note': '',
                'section.id': None,
            }],
            'compat': [{
                'name': 'desktop',
                'browsers': [
                    {'id': '_Chrome',
                     'name': 'Chrome', 'slug': '_Chrome'},
                    {'id': '_Firefox (Gecko)',
                     'name': 'Firefox', 'slug': '_Firefox (Gecko)'},
                    {'id': '_Internet Explorer',
                     'name': 'Internet Explorer',
                     'slug': '_Internet Explorer'},
                    {'id': '_Opera', 'name': 'Opera', 'slug': '_Opera'},
                    {'id': '_Safari', 'name': 'Safari', 'slug': '_Safari'},
                ],
                'features': [
                    {'name': 'Basic support', 'id': '_basic support',
                     'slug': 'web-css-background-size_basic_support'},
                ],
                'versions': [
                    {'version': '1.0', 'browser': '_Chrome',
                     'id': '_Chrome-1.0'},
                    {'version': '1.0', 'browser': '_Firefox (Gecko)',
                     'id': '_Firefox-1.0'},
                    {'version': '4.0', 'browser': '_Internet Explorer',
                     'id': '_Internet Explorer-4.0'},
                    {'version': '7.0', 'browser': '_Opera',
                     'id': '_Opera-7.0'},
                    {'version': '1.0', 'browser': '_Safari',
                     'id': '_Safari-1.0'},
                ],
                'supports': [
                    {'id': '__basic support-_Chrome-1.0',
                     'feature': '_basic support', 'version': '_Chrome-1.0',
                     'support': 'yes'},
                    {'id': '__basic support-_Firefox-1.0',
                     'feature': '_basic support', 'version': '_Firefox-1.0',
                     'support': 'yes'},
                    {'id': '__basic support-_Internet Explorer-4.0',
                     'feature': '_basic support',
                     'version': '_Internet Explorer-4.0',
                     'support': 'yes'},
                    {'id': '__basic support-_Opera-7.0',
                     'feature': '_basic support', 'version': '_Opera-7.0',
                     'support': 'yes'},
                    {'id': '__basic support-_Safari-1.0',
                     'feature': '_basic support', 'version': '_Safari-1.0',
                     'support': 'yes'},
                ],
            }, {
                'name': 'mobile',
                'browsers': [
                    {'id': '_Android', 'name': 'Android', 'slug': '_Android'},
                    {'id': '_Firefox Mobile (Gecko)',
                     'name': 'Firefox Mobile',
                     'slug': '_Firefox Mobile (Gecko)'},
                    {'id': '_IE Mobile', 'name': 'IE Mobile',
                     'slug': '_IE Mobile'},
                    {'id': '_Opera Mobile', 'name': 'Opera Mobile',
                     'slug': '_Opera Mobile'},
                    {'id': '_Safari Mobile',
                     'name': 'Safari Mobile', 'slug': '_Safari Mobile'},
                ],
                'features': [
                    {'name': 'Basic support', 'id': '_basic support',
                     'slug': 'web-css-background-size_basic_support'}
                ],
                'versions': [
                    {'version': '1.0', 'browser': '_Android',
                     'id': '_Android-1.0'},
                    {'version': '1.0', 'browser': '_Firefox Mobile (Gecko)',
                     'id': '_Firefox Mobile-1.0'},
                    {'version': '6.0', 'browser': '_IE Mobile',
                     'id': '_IE Mobile-6.0'},
                    {'version': '6.0', 'browser': '_Opera Mobile',
                     'id': '_Opera Mobile-6.0'},
                    {'version': '1.0', 'browser': '_Safari Mobile',
                     'id': '_Safari Mobile-1.0'},
                ],
                'supports': [
                    {'id': '__basic support-_Android-1.0',
                     'feature': '_basic support', 'version': '_Android-1.0',
                     'support': 'yes'},
                    {'id': '__basic support-_Firefox Mobile-1.0',
                     'feature': '_basic support',
                     'version': '_Firefox Mobile-1.0',
                     'support': 'yes'},
                    {'id': '__basic support-_IE Mobile-6.0',
                     'feature': '_basic support', 'version': '_IE Mobile-6.0',
                     'support': 'yes'},
                    {'id': '__basic support-_Opera Mobile-6.0',
                     'feature': '_basic support',
                     'version': '_Opera Mobile-6.0',
                     'support': 'yes'},
                    {'id': '__basic support-_Safari Mobile-1.0',
                     'feature': '_basic support',
                     'version': '_Safari Mobile-1.0',
                     'support': 'yes'},
                ],
            }],
            'footnotes': {},
            'issues': [],
            'errors': [
                (902, 986, 'Unknown Specification "CSS3 Backgrounds"'),
                (1266, 1272, 'Unknown Browser "Chrome"'),
                (1286, 1301, 'Unknown Browser "Firefox (Gecko)"'),
                (1315, 1332, 'Unknown Browser "Internet Explorer"'),
                (1346, 1351, 'Unknown Browser "Opera"'),
                (1365, 1371, 'Unknown Browser "Safari"'),
                (1669, 1676, 'Unknown Browser "Android"'),
                (1690, 1712, 'Unknown Browser "Firefox Mobile (Gecko)"'),
                (1726, 1735, 'Unknown Browser "IE Mobile"'),
                (1749, 1761, 'Unknown Browser "Opera Mobile"'),
                (1775, 1788, 'Unknown Browser "Safari Mobile"'),
            ]
        }
        self.assertScrape(self.simple_page, expected)

    def test_complex_page_with_data(self):
        self.add_models()
        bs_id = '__basic support-%s'
        cc_id = '__support for contain and cover-%s'
        fn_1 = (
            "Opera 9.5's computation of the background positioning area is"
            " incorrect for fixed backgrounds.\xa0 Opera 9.5 also interprets"
            " the two-value form as a horizontal scaling factor and, from"
            " appearances, a vertical <em>clipping</em> dimension. This has"
            " been fixed in Opera 10.")
        fn_2 = (
            'WebKit-based browsers originally implemented an older draft of'
            ' CSS3<code> background-size </code>in which an omitted second'
            ' value is treated as <em>duplicating</em> the first value; this'
            ' draft does not include the<code> contain </code>or<code> cover'
            ' </code>keywords.')
        fn_3 = (
            'Konqueror 3.5.4 supports<code> -khtml-background-size</code>.')
        fn_4 = """\
<p>While this property is new in Gecko 1.9.2 (Firefox 3.6), it\
 is possible to stretch a image fully over the background in\
 Firefox 3.5 by using <code>-moz-border-image</code>.</p>
<pre class="brush:css">.foo {
  background-image: url(bg-image.png);

  -webkit-background-size: 100% 100%;           /* Safari 3.0 */
     -moz-background-size: 100% 100%;           /* Gecko 1.9.2 (Firefox 3.6) */
       -o-background-size: 100% 100%;           /* Opera 9.5 */
          background-size: 100% 100%;           /* Gecko 2.0 (Firefox 4.0) and\
 other CSS3-compliant browsers */

  -moz-border-image: url(bg-image.png) 0;    /* Gecko 1.9.1 (Firefox 3.5) */
}</pre>"""
        fn_5 = """\
<p>Though Internet Explorer 8 doesn\'t support the <code>background-size\
</code> property, it is possible to emulate some of its functionality using\
 the non-standard <code>-ms-filter</code> function:</p>
<pre class="brush:css">-ms-filter: "progid:DXImageTransform.Microsoft\
.AlphaImageLoader(src=\'path_relative_to_the_HTML_file\',\
 sizingMethod=\'scale\')";</pre>
<p>This simulates the value <code>cover</code>.</p>"""

        expected = {
            'locale': 'en',
            'specs': [{
                'specification.mdn_key': 'CSS3 Backgrounds',
                'specification.id': self.spec.id,
                'section.subpath': '#the-background-size',
                'section.name': 'background-size',
                'section.note': '',
                'section.id': self.section.id,
            }],
            'compat': [{
                'name': 'desktop',
                'browsers': [
                    {'id': self.browsers['chrome'].pk,
                     'name': 'Chrome', 'slug': 'chrome'},
                    {'id': self.browsers['firefox'].pk,
                     'name': 'Firefox', 'slug': 'firefox'},
                    {'id': self.browsers['ie'].pk,
                     'name': 'Internet Explorer', 'slug': 'ie'},
                    {'id': self.browsers['opera'].pk,
                     'name': 'Opera', 'slug': 'opera'},
                    {'id': self.browsers['safari'].pk,
                     'name': 'Safari', 'slug': 'safari'},
                ],
                'features': [
                    {'name': 'Basic support', 'id': '_basic support',
                     'slug': 'web-css-background-size_basic_support'},
                    {'id': '_support for contain and cover',
                     'name': ('Support for <code>contain</code> and'
                              ' <code>cover</code>'),
                     'slug': ('web-css-background-size_support_for_contain'
                              '_and_co')},
                    {'name': 'Support for SVG backgrounds',
                     'id': '_support for svg backgrounds',
                     'slug': ('web-css-background-size_support_for_svg_'
                              'background')},
                ],
                'versions': [
                    {'id': self.versions[('chrome', '1.0')].pk,
                     'browser': self.browsers['chrome'].pk, 'version': '1.0'},
                    {'id': self.versions[('firefox', '3.6')].pk,
                     'browser': self.browsers['firefox'].pk, 'version': '3.6'},
                    {'id': self.versions[('ie', '9.0')].pk,
                     'browser': self.browsers['ie'].pk, 'version': '9.0'},
                    {'id': self.versions[('opera', '9.5')].pk,
                     'browser': self.browsers['opera'].pk, 'version': '9.5'},
                    {'id': self.versions[('safari', '3.0')].pk,
                     'browser': self.browsers['safari'].pk,
                     'version': '3.0'},
                    {'id': self.versions[('chrome', '3.0')].pk,
                     'browser': self.browsers['chrome'].pk,
                     'version': '3.0'},
                    {'id': self.versions[('firefox', '4.0')].pk,
                     'browser': self.browsers['firefox'].pk,
                     'version': '4.0'},
                    {'id': self.versions[('opera', '10.0')].pk,
                     'browser': self.browsers['opera'].pk,
                     'version': '10.0'},
                    {'id': self.versions[('safari', '4.1')].pk,
                     'browser': self.browsers['safari'].pk,
                     'version': '4.1'},
                    {'id': self.versions[('firefox', '8.0')].pk,
                     'browser': self.browsers['firefox'].pk,
                     'version': '8.0'},
                ],
                'supports': [
                    {'id': bs_id % self.versions[('chrome', '1.0')].pk,
                     'feature': '_basic support',
                     'version': self.versions[('chrome', '1.0')].pk,
                     'support': 'partial', 'prefix': '-webkit',
                     'footnote_id': ('2', 1525, 1528), 'footnote': fn_2},
                    {'id': bs_id % self.versions[('firefox', '3.6')].pk,
                     'feature': '_basic support',
                     'version': self.versions[('firefox', '3.6')].pk,
                     'support': 'partial', 'prefix': '-moz',
                     'footnote_id': ('4', 1601, 1604), 'footnote': fn_4},
                    {'id': bs_id % self.versions[('ie', '9.0')].pk,
                     'feature': '_basic support',
                     'version': self.versions[('ie', '9.0')].pk,
                     'support': 'yes',
                     'footnote_id': ('5', 1634, 1637), 'footnote': fn_5},
                    {'id': bs_id % self.versions[('opera', '9.5')].pk,
                     'feature': '_basic support',
                     'version': self.versions[('opera', '9.5')].pk,
                     'support': 'yes', 'prefix': '-o',
                     'footnote_id': ('1', 1704, 1707), 'footnote': fn_1},
                    {'id': bs_id % self.versions[('safari', '3.0')].pk,
                     'feature': '_basic support',
                     'version': self.versions[('safari', '3.0')].pk,
                     'support': 'yes', 'prefix': '-webkit',
                     'footnote_id': ('2', 1799, 1802), 'footnote': fn_2},
                    {'id': bs_id % self.versions[('chrome', '3.0')].pk,
                     'feature': '_basic support',
                     'version': self.versions[('chrome', '3.0')].pk,
                     'support': 'yes'},
                    {'id': bs_id % self.versions[('firefox', '4.0')].pk,
                     'feature': '_basic support',
                     'version': self.versions[('firefox', '4.0')].pk,
                     'support': 'yes'},
                    {'id': bs_id % self.versions[('opera', '10.0')].pk,
                     'feature': '_basic support',
                     'version': self.versions[('opera', '10.0')].pk,
                     'support': 'yes'},
                    {'id': bs_id % self.versions[('safari', '4.1')].pk,
                     'feature': '_basic support',
                     'version': self.versions[('safari', '4.1')].pk,
                     'support': 'yes'},
                    {'id': cc_id % self.versions[('chrome', '3.0')].pk,
                     'feature': '_support for contain and cover',
                     'version': self.versions[('chrome', '3.0')].pk,
                     'support': 'yes'},
                    {'id': cc_id % self.versions[('firefox', '3.6')].pk,
                     'feature': '_support for contain and cover',
                     'version': self.versions[('firefox', '3.6')].pk,
                     'support': 'yes'},
                    {'id': cc_id % self.versions[('ie', '9.0')].pk,
                     'feature': '_support for contain and cover',
                     'version': self.versions[('ie', '9.0')].pk,
                     'support': 'yes',
                     'footnote_id': ('5', 2095, 2098), 'footnote': fn_5},
                    {'id': cc_id % self.versions[('opera', '10.0')].pk,
                     'feature': '_support for contain and cover',
                     'version': self.versions[('opera', '10.0')].pk,
                     'support': 'yes'},
                    {'id': cc_id % self.versions[('safari', '4.1')].pk,
                     'feature': '_support for contain and cover',
                     'version': self.versions[('safari', '4.1')].pk,
                     'support': 'yes'},
                    {'id': '__support for svg backgrounds-%s' % (
                        self.versions[('firefox', '8.0')].pk),
                     'feature': '_support for svg backgrounds',
                     'version': self.versions[('firefox', '8.0')].pk,
                     'support': 'yes'},
                ],
            }, {
                'name': 'mobile',
                'browsers': [
                    {'id': self.browsers['android'].pk,
                     'name': 'Android', 'slug': 'android'},
                    {'id': self.browsers['firefox-mobile'].pk,
                     'name': 'Firefox Mobile', 'slug': 'firefox-mobile'},
                    {'id': self.browsers['ie-mobile'].pk,
                     'name': 'IE Mobile', 'slug': 'ie-mobile'},
                    {'id': self.browsers['opera-mobile'].pk,
                     'name': 'Opera Mobile', 'slug': 'opera-mobile'},
                    {'id': self.browsers['safari-mobile'].pk,
                     'name': 'Safari Mobile', 'slug': 'safari-mobile'},
                ],
                'features': [
                    {'name': 'Basic support', 'id': '_basic support',
                     'slug': 'web-css-background-size_basic_support'},
                    {'name': 'Support for SVG backgrounds',
                     'id': '_support for svg backgrounds',
                     'slug': ('web-css-background-size_support_for_svg_'
                              'background')},
                ],
                'versions': [
                    {'id': self.versions[('android', '')].pk,
                     'browser': self.browsers['android'].pk, 'version': ''},
                    {'id': self.versions[('android', '2.3')].pk,
                     'browser': self.browsers['android'].pk, 'version': '2.3'},
                    {'id': self.versions[('firefox-mobile', '1.0')].pk,
                     'browser': self.browsers['firefox-mobile'].pk,
                     'version': '1.0'},
                    {'id': self.versions[('firefox-mobile', '4.0')].pk,
                     'browser': self.browsers['firefox-mobile'].pk,
                     'version': '4.0'},
                    {'id': self.versions[('safari-mobile', '5.1')].pk,
                     'browser': self.browsers['safari-mobile'].pk,
                     'version': '5.1'},
                    {'id': self.versions[('firefox-mobile', '8.0')].pk,
                     'browser': self.browsers['firefox-mobile'].pk,
                     'version': '8.0'},
                ],
                'supports': [
                    {'id': bs_id % self.versions[('android', '')].pk,
                     'feature': '_basic support',
                     'version': self.versions[('android', '')].pk,
                     'support': 'yes', 'prefix': '-webkit'},
                    {'id': bs_id % self.versions[('android', '2.3')].pk,
                     'feature': '_basic support', 'version': '_Android-2.3',
                     'version': self.versions[('android', '2.3')].pk,
                     'support': 'yes'},
                    {'id': bs_id % self.versions[('firefox-mobile', '1.0')].pk,
                     'feature': '_basic support',
                     'version': self.versions[('firefox-mobile', '1.0')].pk,
                     'support': 'yes', 'prefix': '-moz'},
                    {'id': bs_id % self.versions[('firefox-mobile', '4.0')].pk,
                     'feature': '_basic support',
                     'version': self.versions[('firefox-mobile', '4.0')].pk,
                     'support': 'yes'},
                    {'id': bs_id % self.versions[('safari-mobile', '5.1')].pk,
                     'feature': '_basic support',
                     'version': self.versions[('safari-mobile', '5.1')].pk,
                     'support': 'yes'},
                    {'id': '__support for svg backgrounds-%s' % (
                        self.versions[('firefox-mobile', '8.0')].pk),
                     'feature': '_support for svg backgrounds',
                     'version': self.versions[('firefox-mobile', '8.0')].pk,
                     'support': 'yes'},
                ],
            }],
            'footnotes': {'3': (fn_3, 3771, 3844)},
            'issues': [],
            'errors': [
                (1689, 1704, 'Unknown support text "with some bugs"'),
                (1770, 1799,
                 'Unknown support text "but from an older CSS3 draft"'),
                (2918, 2933, 'Unknown support text "(maybe earlier)"'),
                (3771, 3844, 'Footnote [3] not used')
            ]
        }
        self.assertScrape(self.complex_page, expected)

    def test_feature_slug_is_unique(self):
        self.add_models()
        collide = self.create(
            Feature, slug='web-css-background-size_basic_support',
            name={'en': 'Not Basic Support'})
        actual = scrape_page(
            self.simple_page,
            self.features['web-css-background-size'])
        self.assertNotEqual(
            str(collide.id),
            actual['compat'][0]['features'][0]['id'])
        self.assertEqual(
            'web-css-background-size_basic_support1',
            actual['compat'][0]['features'][0]['slug'])

    def test_incomplete_parse_error(self):
        page = self.simple_page.replace("</h2>", "</h3")
        expected = {
            'locale': 'en',
            'specs': [],
            'compat': [],
            'footnotes': None,
            'issues': [],
            'errors': [
                (24, 52,
                 'Unable to finish parsing MDN page, starting at this'
                 ' position.')
            ]
        }
        self.assertScrape(page, expected)

    def test_unable_to_parse_compat(self):
        good = '<td>{{CompatGeckoDesktop("1")}}</td>'
        bad = '<td><kuma>CompatGeckoDesktop("1")</kuma></td>'
        self.assertTrue(good in self.simple_compat_section)
        page = self.simple_compat_section.replace(good, bad)
        expected = {
            'locale': 'en',
            'specs': [],
            'compat': [],
            'footnotes': None,
            'issues': [],
            'errors': [
                (377, 418,
                 'Section <h2>Browser compatibility</h2> was not parsed,'
                 ' because rule "compat_cell_item" failed to match.'
                 '  Definition:',
                 'compat_cell_item = kuma / cell_break / code_block /'
                 ' cell_p_open / cell_p_close / cell_version /'
                 ' cell_footnote_id / cell_removed / cell_other')
            ]
        }
        self.assertScrape(page, expected)

    def test_with_issues(self):
        h2_fmt = '<h2 id="{0}" name="{0}">Specifications</h2>'
        h2_good = h2_fmt.format('Specifications')
        h2_bad = h2_fmt.format('Browser_Compatibility')
        self.assertTrue(h2_good in self.simple_spec_section)
        page = self.simple_spec_section.replace(h2_good, h2_bad)

        expected = {
            'locale': 'en',
            'specs': [{
                'specification.mdn_key': 'CSS3 Backgrounds',
                'specification.id': None,
                'section.subpath': '#the-background-size',
                'section.name': 'background-size',
                'section.note': '',
                'section.id': None,
            }],
            'compat': [],
            'footnotes': None,
            'issues': [
                (0, 79,
                 'In Specifications section, expected <h2 id="Specifications">'
                 ', actual id="Browser_Compatibility"'),
                (0, 79,
                 'In Specifications section, expected <h2'
                 ' name="Specifications"> or no name attribute,'
                 ' actual name="Browser_Compatibility"'),
            ],
            'errors': [
                (265, 349, 'Unknown Specification "CSS3 Backgrounds"'),
            ],
        }
        self.assertScrape(page, expected)

    def test_with_bad_footnote_reference(self):
        self.add_compat_models()
        good_support = "<td>9.0 [5]</td>"
        bad_support = "<td>9.0 [50]</td>"
        self.assertEqual(1, self.complex_compat_section.count(good_support))
        page = self.complex_compat_section.replace(good_support, bad_support)
        page += self.complex_compat_footnotes
        actual = scrape_page(page, self.features['web-css-background-size'])
        expected_errors = [
            (620, 635, 'Unknown support text "with some bugs"'),
            (701, 730, 'Unknown support text "but from an older CSS3 draft"'),
            (1850, 1865, 'Unknown support text "(maybe earlier)"'),
            (1026, 1030, 'Footnote [50] not found'),
            (2703, 2776, 'Footnote [3] not used'),
        ]
        self.assertEqual(expected_errors, actual['errors'])


class TestScrapeFeaturePage(ScrapeTestCase):
    def setUp(self):
        self.add_models()
        url = ("https://developer.mozilla.org/en-US/docs/Web/CSS/"
               "background-size")
        self.page = FeaturePage.objects.create(
            url=url, feature=self.features['web-css-background-size'],
            status=FeaturePage.STATUS_PARSING)
        meta = self.page.meta()
        meta.raw = dumps({
            'locale': 'en-US',
            'url': url,
            'translations': [{
                'locale': 'fr',
                'url': url.replace('en-US', 'fr')
            }]})
        meta.status = meta.STATUS_FETCHED
        meta.save()

        for translation in self.page.translations():
            translation.status = translation.STATUS_FETCHED
            translation.raw = self.simple_page
            translation.save()

    def test_success(self):
        scrape_feature_page(self.page)
        fp = FeaturePage.objects.get(id=self.page.id)
        self.assertEqual(fp.STATUS_PARSED, fp.status)
        self.assertEqual([], fp.data['meta']['scrape']['errors'])
        self.assertFalse(fp.has_issues)
        section_ids = [str(self.section.id)]
        self.assertEqual(section_ids, fp.data['features']['links']['sections'])

    def test_with_specification_mismatch(self):
        self.spec.mdn_key = 'CSS3_Backgrounds'
        self.spec.save()
        scrape_feature_page(self.page)
        fp = FeaturePage.objects.get(id=self.page.id)
        self.assertEqual(fp.STATUS_PARSED, fp.status)
        self.assertTrue(fp.has_issues)
        self.assertEqual(
            ["_CSS3 Backgrounds_#the-background-size"],
            fp.data['features']['links']['sections'])

    def test_with_section_mismatch(self):
        self.section.subpath['en'] = '#the-other-background-size'
        self.section.save()
        scrape_feature_page(self.page)
        fp = FeaturePage.objects.get(id=self.page.id)
        self.assertEqual(fp.STATUS_PARSED, fp.status)
        self.assertFalse(fp.has_issues)
        section_ids = ["%d_#the-background-size" % self.spec.id]
        self.assertEqual(section_ids, fp.data['features']['links']['sections'])

    def test_with_section_already_associated(self):
        self.page.feature.sections.add(self.section)
        scrape_feature_page(self.page)
        fp = FeaturePage.objects.get(id=self.page.id)
        self.assertEqual(fp.STATUS_PARSED, fp.status)
        self.assertFalse(fp.has_issues)
        section_ids = [str(self.section.id)]
        self.assertEqual(section_ids, fp.data['features']['links']['sections'])

    def test_with_browser_mismatch(self):
        good_name = '<th>Chrome</th>'
        bad_name = '<th>Chromium</th>'
        en_content = TranslatedContent.objects.get(
            page=self.page, locale='en-US')
        self.assertEqual(1, en_content.raw.count(good_name))
        en_content.raw = en_content.raw.replace(good_name, bad_name)
        en_content.save()

        scrape_feature_page(self.page)
        fp = FeaturePage.objects.get(id=self.page.id)
        self.assertEqual(fp.STATUS_PARSED, fp.status)
        self.assertTrue(fp.has_issues)
        self.assertEqual(1, len(fp.data['meta']['scrape']['errors']))
        err = fp.data['meta']['scrape']['errors'][0]
        expected = '<div><p>Unknown Browser &quot;Chromium&quot;</p>'
        self.assertTrue(err.startswith(expected))
        desktop_browsers = fp.data['meta']['compat_table']['tabs'][0]
        self.assertEqual('Desktop Browsers', desktop_browsers['name']['en'])
        self.assertEqual('_Chromium', desktop_browsers['browsers'][0])

    def test_with_existing_feature(self):
        basic = self.create(
            Feature, slug=self.page.feature.slug + '-basic-support',
            name={'en': 'Basic support'}, parent=self.page.feature)
        scrape_feature_page(self.page)
        fp = FeaturePage.objects.get(id=self.page.id)
        self.assertEqual(fp.STATUS_PARSED, fp.status)
        self.assertFalse(fp.has_issues)
        supports = fp.data['meta']['compat_table']['supports']
        self.assertTrue(str(basic.id) in supports)

    def test_with_existing_support(self):
        basic = self.create(
            Feature, slug=self.page.feature.slug + '-basic-support',
            name={'en': 'Basic support'}, parent=self.page.feature)
        browser = self.browsers['firefox']
        version = self.versions[('firefox', '1.0')]
        support = self.create(Support, version=version, feature=basic)

        scrape_feature_page(self.page)
        fp = FeaturePage.objects.get(id=self.page.id)
        self.assertEqual(fp.STATUS_PARSED, fp.status)
        self.assertFalse(fp.has_issues)
        supports = fp.data['meta']['compat_table']['supports']
        basic_support = supports[str(basic.id)][str(browser.id)]
        self.assertTrue(str(support.id) in basic_support)

    def test_scrape_almost_empty_page(self):
        en_content = TranslatedContent.objects.get(
            page=self.page, locale='en-US')
        en_content.raw = "<h1>nothing here</h1>"
        en_content.save()

        scrape_feature_page(self.page)
        fp = FeaturePage.objects.get(id=self.page.id)
        self.assertEqual(fp.STATUS_PARSED, fp.status)
        self.assertTrue(fp.has_issues)
        self.assertEqual(
            ["<pre>No &lt;h2&gt; found in page</pre>"],
            fp.data['meta']['scrape']['errors'])

    def test_scrape_canonical_feature(self):
        en_content = TranslatedContent.objects.get(
            page=self.page, locale='en-US')
        old_name = '<td>Basic support</td>'
        new_name = '<td><code>basic-support</code></td>'
        self.assertTrue(old_name in en_content.raw)
        en_content.raw = en_content.raw.replace(old_name, new_name)
        en_content.save()

        scrape_feature_page(self.page)
        fp = FeaturePage.objects.get(id=self.page.id)
        self.assertEqual(fp.STATUS_PARSED, fp.status)
        self.assertEqual([], fp.data['meta']['scrape']['errors'])
        self.assertFalse(fp.has_issues)
        expected = [{
            'id': '_basic-support',
            'slug': 'web-css-background-size_basic-support',
            'mdn_uri': None,
            'experimental': False,
            'standardized': True,
            'stable': True,
            'obsolete': False,
            'name': 'basic-support',
            'links': {
                'children': [],
                'parent': str(self.page.feature.id),
                'sections': [],
                'supports': [],
            }}]
        self.assertDataEqual(expected, fp.data['linked']['features'])

    def test_scrape_with_footnote(self):
        orig = "<td>4.0</td>"
        new = "<td>4.0 [1]</td>"
        en_content = TranslatedContent.objects.get(
            page=self.page, locale='en-US')
        assert orig in self.simple_compat_section
        en_content.raw = (
            self.simple_spec_section +
            self.simple_compat_section.replace(orig, new) +
            "<p>[1] Footnote</p>")
        en_content.save()

        scrape_feature_page(self.page)
        fp = FeaturePage.objects.get(id=self.page.id)
        self.assertEqual(fp.STATUS_PARSED, fp.status)
        self.assertEqual([], fp.data['meta']['scrape']['errors'])
        self.assertFalse(fp.has_issues)
        version = self.versions[('ie', '4.0')]
        expected = {'__basic support-%d' % version.id: 1}
        self.assertDataEqual(
            expected, fp.data['meta']['compat_table']['footnotes'])


class TestRangeErrorToHtml(ScrapeTestCase):
    def test_no_rule(self):
        html = range_error_to_html(
            self.simple_page, 902, 986,
            'Unknown Specification "CSS3 Backgrounds"')
        expected = """\
<div><p>Unknown Specification &quot;CSS3 Backgrounds&quot;</p>\
<p>Context:<pre>\
16  &lt;tbody&gt;
17   &lt;tr&gt;
18    &lt;td&gt;{{SpecName(&#39;CSS3 Backgrounds&#39;, &#39;#the-background-\
size&#39;, &#39;background-size&#39;)}}&lt;/td&gt;
**    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\
^^^^^^^^^^^^^^
19    &lt;td&gt;{{Spec2(&#39;CSS3 Backgrounds&#39;)}}&lt;/td&gt;
20    &lt;td&gt;&lt;/td&gt;
</pre></p></div>"""
        self.assertEqual(expected, html)

    def test_rule(self):
        html = range_error_to_html(
            self.simple_page, 902, 986,
            'Unknown Specification "CSS3 Backgrounds"',
            'me = "awesome"')
        expected = """\
<div><p>Unknown Specification &quot;CSS3 Backgrounds&quot;</p>\
<p><code>me = &quot;awesome&quot;</code></p>\
<p>Context:<pre>\
16  &lt;tbody&gt;
17   &lt;tr&gt;
18    &lt;td&gt;{{SpecName(&#39;CSS3 Backgrounds&#39;, &#39;#the-background-\
size&#39;, &#39;background-size&#39;)}}&lt;/td&gt;
**    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\
^^^^^^^^^^^^^^
19    &lt;td&gt;{{Spec2(&#39;CSS3 Backgrounds&#39;)}}&lt;/td&gt;
20    &lt;td&gt;&lt;/td&gt;
</pre></p></div>"""
        self.assertEqual(expected, html)


class TestSlugify(TestCase):
    def test_already_slugged(self):
        self.assertEqual('foo', slugify('foo'))

    def test_long_string(self):
        self.assertEqual(
            'abcdefghijklmnopqrstuvwxyz-abcdefghijklmnopqrstuvw',
            slugify('ABCDEFGHIJKLMNOPQRSTUVWXYZ-abcdefghijklmnopqrstuvwxyz'))

    def test_non_ascii(self):
        self.assertEqual('_', slugify("Рекомендация"))

    def test_limit(self):
        self.assertEqual(
            'abcdefghij', slugify('ABCDEFGHIJKLMNOPQRSTUVWXYZ', length=10))

    def test_num_suffix(self):
        self.assertEqual('slug13', slugify('slug', suffix=13))


class TestDateToIso(TestCase):
    def test_date(self):
        self.assertEqual('2015-02-02', date_to_iso(date(2015, 2, 2)))

    def test_none(self):
        self.assertEqual(None, date_to_iso(''))
