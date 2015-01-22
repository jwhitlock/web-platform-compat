"""Test mdn.scrape."""
from __future__ import unicode_literals
from json import dumps

from parsimonious.grammar import Grammar

from mdn.models import FeaturePage, TranslatedContent
from mdn.scrape import (
    page_grammar, range_error_to_html, scrape_page, scrape_feature_page)
from webplatformcompat.models import Feature, Maturity, Section, Specification
from webplatformcompat.tests.base import TestCase


class TestGrammar(TestCase):
    def setUp(self):
        self.grammar = Grammar(page_grammar)

    def test_specdesc_td_empty(self):
        text = '<td></td>'
        parsed = self.grammar['specdesc_td'].parse(text)
        capture = parsed.children[2]
        self.assertEqual('', capture.text)

    def test_specdesc_td_plain_text(self):
        text = '<td>Plain Text</td>'
        parsed = self.grammar['specdesc_td'].parse(text)
        capture = parsed.children[2]
        self.assertEqual('Plain Text', capture.text)

    def test_specdesc_td_html(self):
        text = "<td>Defines <code>right</code> as animatable.</td>"
        parsed = self.grammar['specdesc_td'].parse(text)
        capture = parsed.children[2]
        self.assertEqual(
            'Defines <code>right</code> as animatable.', capture.text)


class ScrapeTestCase(TestCase):
    """Fixtures for scraping tests."""

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

    simple_see_also = """\
<h2 id="See_also">See also</h2>
<ul>
 <li>{{CSS_Reference:Position}}</li>
 <li><a href="/en-US/docs/Web/CSS/block_formatting_context">\
Block formatting context</a></li>
</ul>
"""
    simple_page = (
        simple_prefix + simple_other_section + simple_spec_section +
        simple_see_also)

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


class TestScrape(ScrapeTestCase):
    def test_empty(self):
        out = scrape_page("")
        expected = {
            'locale': 'en',
            'specs': [],
            'issues': [],
            'errors': ["No <h2> found in page"],
        }
        self.assertEqual(out, expected)

    def test_spec_only(self):
        """Test with a only a Specification section."""
        out = scrape_page(self.simple_spec_section)
        expected = {
            'specs': [{
                'specification.mdn_key': 'CSS3 Backgrounds',
                'specification.id': None,
                'section.subpath': '#the-background-size',
                'section.name': 'background-size',
                'section.note': '',
                'section.id': None,
            }],
            'locale': 'en',
            'issues': [],
            'errors': [
                (251, 335, 'Unknown Specification "CSS3 Backgrounds"'),
            ]
        }
        self.assertEqual(expected, out)

    def test_full_page(self):
        """Test with a more complete but simple page."""
        out = scrape_page(self.simple_page)
        expected = {
            'specs': [{
                'specification.mdn_key': 'CSS3 Backgrounds',
                'specification.id': None,
                'section.subpath': '#the-background-size',
                'section.name': 'background-size',
                'section.note': '',
                'section.id': None,
            }],
            'locale': 'en',
            'issues': [],
            'errors': [
                (902, 986, 'Unknown Specification "CSS3 Backgrounds"'),
            ]
        }
        self.assertEqual(expected, out)

    def test_parse_error(self):
        page = self.simple_page.replace("</h2>", "</h3")
        out = scrape_page(page)
        expected = {
            'locale': 'en',
            'specs': [],
            'issues': [],
            'errors': [
                (40, 52,
                 'Rule "attr" failed to match.  Rule definition:',
                 'attr = _ ident _ equals _ qtext _')]
        }
        self.assertEqual(expected, out)


class TestScrapeFeaturePage(ScrapeTestCase):
    def setUp(self):
        web = self.create(Feature, slug='web')
        css = self.create(Feature, parent=web, slug='web-css')
        self.background_size = self.create(
            Feature, parent=css, slug='web-css-background')
        url = ("https://developer.mozilla.org/en-US/docs/Web/CSS/"
               "background-size")
        self.page = FeaturePage.objects.create(
            url=url, feature=self.background_size,
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
        self.assertTrue(fp.has_issues)
        section_ids = ["_CSS3 Backgrounds_#the-background-size"]
        self.assertEqual(section_ids, fp.data['features']['links']['sections'])
        self.assertEqual('_unknown', fp.data['linked']['maturities'][0]['id'])

    def test_success_with_spec_data(self):
        self.add_spec_models()
        scrape_feature_page(self.page)
        fp = FeaturePage.objects.get(id=self.page.id)
        self.assertEqual(fp.STATUS_PARSED, fp.status)
        self.assertFalse(fp.has_issues)
        section_ids = [str(self.section.id)]
        self.assertEqual(section_ids, fp.data['features']['links']['sections'])

    def test_with_section_mismatch(self):
        self.add_spec_models()
        self.section.subpath['en'] = '#the-other-background-size'
        self.section.save()
        scrape_feature_page(self.page)
        fp = FeaturePage.objects.get(id=self.page.id)
        self.assertEqual(fp.STATUS_PARSED, fp.status)
        self.assertFalse(fp.has_issues)
        section_ids = ["%d_#the-background-size" % self.spec.id]
        self.assertEqual(section_ids, fp.data['features']['links']['sections'])

    def test_with_section_already_associated(self):
        self.add_spec_models()
        self.background_size.sections.add(self.section)
        scrape_feature_page(self.page)
        fp = FeaturePage.objects.get(id=self.page.id)
        self.assertEqual(fp.STATUS_PARSED, fp.status)
        self.assertFalse(fp.has_issues)
        section_ids = [str(self.section.id)]
        self.assertEqual(section_ids, fp.data['features']['links']['sections'])

    def test_with_issues(self):
        self.add_spec_models()
        en_content = TranslatedContent.objects.get(
            page=self.page, locale='en-US')

        h2_fmt = '<h2 id="{0}" name="{0}">Specifications</h2>'
        h2_good = h2_fmt.format('Specifications')
        h2_bad = h2_fmt.format('Browser_Compatibility')
        self.assertTrue(h2_good in en_content.raw)
        en_content.raw = en_content.raw.replace(h2_good, h2_bad)
        en_content.save()

        scrape_feature_page(self.page)
        fp = FeaturePage.objects.get(id=self.page.id)
        self.assertEqual(fp.STATUS_PARSED, fp.status)
        self.assertTrue(fp.has_issues)

    def test_scrape_almost_empty_page(self):
        self.add_spec_models()
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
