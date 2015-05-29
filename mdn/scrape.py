"""Parsing Expression Grammar for MDN pages.

This code is messy. Parsing is messy. This may be related. It also, hopefully,
temporary, and will be jettisoned when the MDN data is imported.

The workflow is:
1. scrape_featurepage() takes a FeaturePage, which links an API Feature with
   an MDN page.  It passes the English raw page [1] plus the feature to:
2. scrape_page(), which extracts the specification and compatibility data
   from the page, by parsing it into a node tree with:
3. page_grammar, a parsing expression grammar in the Parsimonious [2] syntax,
   which is then passed to:
4. PageVisitor, which "visits" each node, extracting data, rendering
   KumaScript, matching to existing API features, and detecting errors.
5. The extracted data is returned to scrape_featurepage, which turns it into
   JSON-API in the view_feature format [3], with scrape-specific metadata.
6. The JSON can be used to view the scraped data, plan fixes to the MDN page,
   or be fed back into the API.

[1] https://developer.mozilla.org/en-US/docs/Web/API/CSSMediaRule?raw
[2] https://github.com/erikrose/parsimonious
[3] api/v1/view_features/1.json
"""
from __future__ import unicode_literals
from collections import OrderedDict
from itertools import chain
import re
import string

from django.utils.encoding import python_2_unicode_compatible
from django.utils.six import text_type
from parsimonious import IncompleteParseError, ParseError
from parsimonious.grammar import Grammar
from parsimonious.nodes import Node, NodeVisitor

from webplatformcompat.models import (
    Browser, Feature, Section, Specification, Support, Version)


# Parsimonious grammar for an MDN page
page_grammar = Grammar(
    r"""
# A whole raw MDN page
doc = other_text other_section* spec_section? compat_section?
    other_section* last_section?

# Sections that we don't care about
other_text = ~r".*?(?=<h2)"s
other_section = _ !(spec_h2 / compat_h2) other_h2 _ other_text
other_h2 = "<h2 " _ attrs? _ ">" _ ~r"(?P<content>.*?(?=</h2>))"s _ "</h2>"
last_section = _ other_h2 _ ~r".*(?!=<h2)"s

#
# Specifications section
#
spec_section = _ spec_h2 _ spec_table
spec_h2 = "<h2 " _ attrs? _ ">" _ spec_title _ "</h2>"
spec_title = ~r"(?P<content>[sS]pecifications?)"
spec_table = "<table class=\"standard-table\">" _ spec_head _ spec_body
    _ "</table>" _

spec_head = spec_thead_headers / spec_tbody_headers
spec_thead_headers = "<thead>" _ spec_headers "</thead>" _ spec_tbody _
spec_tbody_headers = spec_tbody _ spec_headers
spec_headers =  "<tr>" _ th_elems _ "</tr>" _
spec_tbody = "<tbody>"

spec_body = spec_rows "</tbody>"
spec_rows = spec_row+
spec_row = tr_open _ specname_td _ spec2_td _ specdesc_td _ "</tr>" _
specname_td = td_open _ specname_text "</td>"
specname_text = kumascript / inner_td
spec2_td = td_open _ spec2_text "</td>"
spec2_text = kumascript / inner_td
specdesc_td = td_open _ specdesc_text _ "</td>"
specdesc_text = specdesc_token*
specdesc_token = kumascript / code_block / spec_other
spec_other = ~r"(?P<content>[^{<]+)\s*"s
inner_td = ~r"(?P<content>.*?(?=</td>))"s

#
# Browser Compatibility section
#
compat_section = _ compat_h2 _ compat_kumascript _ compat_divs
    compat_footnotes?
compat_h2 = "<h2 " _ attrs? _ ">" _ compat_title _ "</h2>"
compat_title = ~r"(?P<content>Browser [cC]ompat[ai]bility)"
compat_kumascript = (compat_kumascript_div / compat_kumascript_p)
compat_kumascript_div = "<div>" _ kumascript "</div>"
compat_kumascript_p = "<p>" _ kumascript "</p>"
compat_divs = compat_div+
compat_div = "<div" _ "id" _ equals _ compat_div_id ">" _ compat_table
    _ "</div>" _
compat_div_id = qtext
compat_table = "<table class=\"compat-table\">" _ compat_body _ "</table>" _
compat_body = "<tbody>" _ compat_headers _ compat_rows* _ "</tbody>"
compat_headers = tr_open _ feature_cell _ compat_client_cells _
    "</tr>" _
feature_cell = th_elem
compat_client_cells = th_elems
compat_rows = compat_row* _
compat_row = tr_open _ compat_row_cells _ "</tr>" _
compat_row_cells = compat_row_cell+
compat_row_cell = td_open _ compat_cell _ "</td>" _

#
# A cell in the Compat table
#   Due to rowspan and colspan usage, we won't know if a cell is a feature
#   or a support until we visit the table.
#
compat_cell = compat_cell_token*
compat_cell_token = (kumascript / break / code_block / p_open / p_close /
    cell_version / cell_footnote_id / cell_removed / cell_other)
code_block = "<code>" _ code_text _ "</code>" _
code_text = ~r"(?P<content>.*?(?=</code>))"s
cell_version = ~r"(?P<version>\d+(\.\d+)*)"""
    r"""(\s+\((?P<eng_version>\d+(\.\d+)*)\))?\s*"s
cell_removed = ~r"[Rr]emoved\s+[Ii]n\s*"s
cell_footnote_id = "<sup>"? _ a_open? _ ~r"\[(?P<footnote_id>\d+|\*+)\]\s*"s _
    "</a>"? _ "</sup>"?
cell_other = ~r"(?P<content>[^{<[]+)\s*"s

#
# Optional footnotes after the Browser Compatibility Tables
#
compat_footnotes = footnote_token* _
footnote_token = (kumascript / p_open / p_close / pre_block / footnote_id /
    cell_other)
footnote_id = "[" ~r"(?P<content>\d+|\*+)" "]"

#
# Common tokens
#
kumascript = ks_esc_start ks_name ks_arglist? ks_esc_end
ks_esc_start = "{{" _
ks_name = ~r"(?P<content>[^\(\}\s]*)\s*"s
ks_arglist = ks_func_start ks_arg ks_arg_rest* ks_func_end
ks_func_start = "(" _
ks_func_arg = _ "," _
ks_func_end = _ ")" _
ks_esc_end = "}}" _
ks_arg = (double_quoted_text / single_quoted_text / ks_bare_arg)
ks_bare_arg = ~r"(?P<content>.*?(?=[,)]))"
ks_arg_rest = ks_func_arg ks_arg

th_elems = th_elem+
th_elem = th_open _ (strong_text / bare_text) "</th>" _
tr_open = "<tr" _ opt_attrs ">"
th_open = "<th" _ opt_attrs ">"
td_open = "<td" _ opt_attrs ">"
a_open = "<a" _  opt_attrs ">"
a_both = _ a_open _ "</a>" _
p_open = "<p>" _
p_close = "</p>" _
break = "<" _ "br" _ ("/>" / ">") _
pre_block = "<pre" attrs? ">" pre_text "</pre>" _
pre_text = ~r"(?P<content>.*?(?=</pre>))"s

attrs = attr+
opt_attrs = attr*
attr = _ ident _ equals _ qtext _
equals = "="
ident = ~r"(?P<content>[a-z][a-z0-9-:]*)"

text = (double_quoted_text / single_quoted_text / bare_text)
qtext = (double_quoted_text / single_quoted_text)
bare_text = ~r"(?P<content>[^<]*)"
strong_text = "<strong>" _ bare_text _ "</strong>" _
double_quoted_text = ~r'"(?P<content>[^"]*)"'
single_quoted_text = ~r"'(?P<content>[^']*)'"

# Whitespace
_ = ~r"[ \t\r\n]*"s
""")


@python_2_unicode_compatible
class EmptyString(object):
    """Non-falsy placeholder for empty string"""

    def __str__(self):
        return text_type('')


class PageVisitor(NodeVisitor):
    """Extract and validate data from a parsed MDN page.

    visit_<rule> is the function called when a node matching a rule is
    visited.  For reference, visit_* functions are roughly in the order
    they appear in page_grammar.

    When visiting a full document, the desired output is a dictionary
    with the keys:

    - 'locale': The locale of the page (passed in)
    - 'specs': Data scraped from Specifications section
    - 'compat': Data scraped from the Browser Compatibility table
    - 'footnotes': Footnotes appearing after the Browser Compatibility table,
      but not referenced in the table
    - 'issues': Issues with the parsed page
    """
    def __init__(self, feature, locale='en'):
        super(PageVisitor, self).__init__()
        self.feature = feature
        assert isinstance(feature, Feature), type(feature)
        self.locale = locale
        self.specs = []
        self.issues = []
        self.compat = []
        self.footnotes = None
        self._browser_data = None
        self._feature_data = None

    def generic_visit(self, node, visited_children):
        """Visitor when none is specified."""
        return visited_children or node

    def _visit_content(self, node, children):
        """Vistor for re nodes with a named (?P<content>) section."""
        return node.match.group('content')

    def _visit_token(self, node, children):
        """Visitor for one of many tokenized items"""
        token = children[0]
        assert isinstance(token, dict), type(token)
        return token

    def visit_doc(self, node, children):
        """At the top level, return all the collected data."""
        return {
            'specs': self.specs,
            'locale': self.locale,
            'issues': self.issues,
            'compat': self.compat,
            'footnotes': self.footnotes,
        }

    re_h2 = re.compile(r'''(?x)(?s)     # Be verbose, and don't stop at newline
    <h2[^>]*>           # Look for h2 open tag
    (?P<title>[^<]+)    # Capture the h2 title
    </h2>               # The h2 close tag
    ''')

    def visit_other_section(self, section_node, children):
        """Find "other" sections that should have been parsed.

        Because spec_section and compat_section are optional,
        unexpected elements cause them to be treated as other sections.
        This turns these into errors for further cleanp.
        """
        sections = {
            'browser compatibility': 'compat_section',
            'specifications': 'spec_section',
            'specification': 'spec_section'
        }

        for h2 in self.re_h2.finditer(section_node.text):
            title = h2.group('title')
            section = sections.get(title.lower().strip())
            if section:
                # Failed to parse an <h2>.  Add an error
                start = section_node.start + h2.start()
                text = section_node.text[h2.start():]
                try:
                    page_grammar[section].parse(text)
                except ParseError as pe:
                    expr = pe.expr
                    self.issues.append((
                        'section_skipped',
                        pe.pos + start, end_of_line(pe.text, pe.pos) + start,
                        {'rule_name': expr.name, 'title': title,
                         'rule': expr.as_rule()}))
                else:
                    self.issues.append((
                        'section_missed',
                        start,
                        end_of_line(text, 0) + start,
                        {'title': title}))

    visit_last_section = visit_other_section

    #
    # Specification section
    #
    def visit_spec_h2(self, node, children):
        attrs_list = children[2][0]
        assert isinstance(attrs_list, list), type(attrs_list)
        h2_id = None
        expected = ('Specifications', 'Specification')
        for attr in attrs_list:
            assert isinstance(attr, dict), type(attr)
            if attr['ident'] == 'id':
                h2_id = attr['value']
                if h2_id not in expected:
                    self.issues.append((
                        'spec_h2_id', attr['start'], attr['end'],
                        {'h2_id': h2_id}))
            elif attr['ident'] == 'name':
                h2_name = attr['value']
                if h2_name not in expected:
                    self.issues.append((
                        'spec_h2_name', attr['start'], attr['end'],
                        {'h2_name': h2_name}))

    def visit_spec_row(self, node, children):
        specname = children[2]
        assert isinstance(specname, tuple), type(specname)
        key, spec_id, path, name = specname

        spec2 = children[4]
        if isinstance(spec2, text_type):
            # Standard Spec2 KumaScript
            if spec2 and spec2 != key:
                self.issues.append((
                    'spec_mismatch', node.start, node.end,
                    {'spec2_key': spec2, 'specname_key': key}))
        else:
            # Text like 'Standard'
            assert isinstance(spec2, dict), spec2
            assert spec2['type'] == 'text', spec2
            self.issues.append((
                'spec2_converted', spec2['start'], spec2['end'],
                {'key': key, 'original': spec2['content']}))

        desc = children[6]
        assert isinstance(desc, text_type)

        section_id = None
        if spec_id:
            for section in Section.objects.filter(specification_id=spec_id):
                if section.subpath.get(self.locale) == path:
                    section_id = section.id
                    break
        self.specs.append({
            'specification.mdn_key': key,
            'specification.id': spec_id,
            'section.subpath': path,
            'section.name': name,
            'section.note': self.cleanup_whitespace(desc),
            'section.id': section_id})

    def visit_specname_td(self, node, children):
        specname_text = children[2]
        assert isinstance(specname_text, list)
        assert len(specname_text) == 1, specname_text
        assert isinstance(specname_text[0], dict)
        item = specname_text[0]
        if item['type'] == 'kumascript':
            assert item['name'].lower() == 'specname'
            key = self.unquote(item["args"][0])
            subpath = ""
            name = ""
            try:
                subpath = self.unquote(item["args"][1])
                name = self.unquote(item["args"][2])
            except IndexError:
                pass  # subpath and name can be empty
        else:
            assert item['type'] == 'text', item
            legacy_specs = {
                'ECMAScript 1st Edition.': 'ES1',
                'ECMAScript 3rd Edition.': 'ES3'}
            key = legacy_specs.get(item['content'], '')
            subpath = ''
            name = ''
            if key:
                self.issues.append((
                    'specname_converted', item['start'], item['end'],
                    {'original': item['content'], 'key': key}))
            else:
                self.issues.append((
                    'specname_not_kumascript', item['start'], item['end'],
                    {'original': item['content']}))

        if key:
            try:
                spec = Specification.objects.get(mdn_key=key)
            except Specification.DoesNotExist:
                spec_id = None
                self.issues.append((
                    'unknown_spec', item['start'], item['end'], {'key': key}))
            else:
                spec_id = spec.id
        else:
            if item['type'] == 'kumascript':
                self.issues.append((
                    'specname_blank_key', item['start'], item['end'], {}))
            spec_id = None

        return (key, spec_id, subpath, name)

    def visit_spec2_td(self, node, children):
        spec2_text = children[2]
        assert isinstance(spec2_text, list), type(spec2_text)
        assert len(spec2_text) == 1, spec2_text
        assert isinstance(spec2_text[0], dict)
        item = spec2_text[0]
        if item['type'] == 'kumascript':
            if item['name'].lower() != 'spec2':
                self.issues.append(
                    self.kumascript_issue(
                        'spec2_wrong_kumascript', item, 'spec2'))
            if len(item['args']) != 1:
                self.issues.append(
                    self.kumascript_issue('spec2_arg_count', item, 'spec2'))
                return ''
            key = self.unquote(item["args"][0])
        else:
            assert item['type'] == 'text', item
            return item  # Handle errors at row level
        assert isinstance(key, text_type), type(key)
        return key

    def visit_specdesc_td(self, node, children):
        specdesc = children[2]
        bits = []
        if isinstance(specdesc, Node):
            assert specdesc.start == specdesc.end
        else:
            assert isinstance(specdesc, list), type(specdesc)
            for item in specdesc:
                if item['type'] == 'kumascript':
                    text = self.kumascript_to_text(item, 'specdesc')
                    if text:
                        bits.append(text)
                elif item['type'] == 'code_block':
                    bits.append("<code>{}</code>".format(item['content']))
                else:
                    assert item['type'] == 'text'
                    bits.append(item['content'])
        return self.join_content(bits)

    visit_specdesc_token = _visit_token

    def visit_inner_td(self, node, children):
        text = self.cleanup_whitespace(node.text)
        assert 'td>' not in text
        return {
            'type': 'text', 'content': text,
            'start': node.start, 'end': node.end}

    visit_spec_other = visit_inner_td

    #
    # Browser Compatibility section
    #
    def visit_compat_section(self, node, children):
        compat_divs = children[5]
        footnotes = children[6][0]

        assert isinstance(compat_divs, list), type(compat_divs)
        for div in compat_divs:
            assert isinstance(div, dict), type(div)
        assert isinstance(footnotes, OrderedDict), type(footnotes)

        # Merge footnotes into supports
        used_footnotes = set()
        for div in compat_divs:
            for support in div['supports']:
                if 'footnote_id' in support:
                    f_id, f_start, f_end = support['footnote_id']
                    try:
                        text, start, end = footnotes[f_id]
                    except KeyError:
                        self.issues.append((
                            'footnote_missing', f_start, f_end,
                            {'footnote_id': f_id}))
                    else:
                        support['footnote'] = text
                        used_footnotes.add(f_id)

        for f_id in used_footnotes:
            del footnotes[f_id]

        for f_id, (text, start, end) in footnotes.items():
            self.issues.append((
                'footnote_unused', start, end, {'footnote_id': f_id}))

        self.compat = compat_divs
        self.footnotes = footnotes

    def visit_compat_kumascript(self, node, children):
        assert isinstance(children, list), type(children)
        kumascript = children[0][2]
        assert isinstance(kumascript, dict), type(kumascript)
        assert kumascript['type'] == 'kumascript'
        assert kumascript['name'].lower() == 'compatibilitytable'

    def visit_compat_div(self, node, children):
        compat_div_id = children[6][0]
        compat_table = children[9]

        pre, div_id = compat_div_id.split('-', 1)
        assert isinstance(div_id, text_type), type(div_id)
        assert isinstance(compat_table, dict), type(compat_table)

        div = compat_table.copy()
        div['name'] = div_id
        return div

    def visit_compat_table(self, node, children):
        compat_body = children[2]
        assert isinstance(compat_body, dict), type(compat_body)
        return compat_body

    def visit_compat_body(self, node, children):
        compat_headers = children[2]
        compat_rows = children[4][0]

        assert isinstance(compat_headers, list), type(compat_headers)
        for header in compat_headers:
            assert isinstance(header, dict), type(header)
        assert isinstance(compat_rows, list), type(compat_rows)
        for row in compat_rows:
            assert isinstance(row, dict), type(row)

        browsers = OrderedDict()
        features = OrderedDict()
        versions = OrderedDict()
        supports = OrderedDict()

        # Gather the browsers and determine # of columns
        columns = [None]
        for browser in compat_headers:
            colspan = int(browser.pop('colspan', 1))
            browser_id = browser['id']
            browsers[browser_id] = browser
            for i in range(colspan):
                columns.append(browser_id)

        # Create an empty row grid
        table = []
        for row in range(len(compat_rows)):
            table_row = []
            for col in range(len(columns)):
                table_row.append(None)
            table.append(table_row)

        # Parse the rows for features and supports
        for row, compat_row in enumerate(compat_rows):
            for cell in compat_row['cells']:
                td = cell[0]
                try:
                    col = table[row].index(None)
                except ValueError:
                    self.issues.append((
                        'extra_cell', td['start'], cell[-1]['end'], {}))
                    continue
                rowspan = int(td.get('rowspan', 1))
                colspan = int(td.get('colspan', 1))
                if col == 0:
                    # Insert as feature
                    feature = self.cell_to_feature(cell)
                    cell_id = feature['id']
                    features[feature['id']] = feature
                else:
                    # Insert as support
                    feature_id = table[row][0]
                    assert feature_id
                    feature = features[feature_id]
                    browser_id = columns[col]
                    browser = browsers[browser_id]
                    cell_versions, cell_supports = self.cell_to_support(
                        cell, feature, browser)
                    cell_id = []
                    for version in cell_versions:
                        versions[version['id']] = version
                    for support in cell_supports:
                        cell_id.append(support['id'])
                        supports[support['id']] = support
                # Insert IDs into table
                for r in range(rowspan):
                    for c in range(colspan):
                        table[row + r][col + c] = cell_id

        return {
            'browsers': list(browsers.values()),
            'versions': list(versions.values()),
            'features': list(features.values()),
            'supports': list(supports.values()),
        }

    def visit_compat_headers(self, node, children):
        feature = children[2]
        compat_client_cells = children[4]
        assert isinstance(feature, dict), type(feature)
        assert isinstance(compat_client_cells, list), type(compat_client_cells)

        # Verify feature header
        fcontent = feature['content']
        if fcontent['text'] != 'Feature':
            self.issues.append((
                'feature_header', fcontent['start'], fcontent['end'],
                {'header': fcontent['text']}))

        # Process client headers
        expected_attrs = ('colspan',)
        clients = []
        for raw_cell in compat_client_cells:
            assert isinstance(raw_cell, dict), type(raw_cell)
            assert raw_cell['type'] == 'th'
            cell = self._consume_attributes(raw_cell, expected_attrs)
            content = cell['content']
            name = content['text']
            assert isinstance(name, text_type), type(name)
            b_id, b_name, b_slug = self.browser_id_name_and_slug(name)
            if is_fake_id(b_id):
                self.issues.append((
                    'unknown_browser', content['start'], content['end'],
                    {'name': name}))
            client = {
                'name': b_name,
                'id': b_id,
                'slug': b_slug
            }
            if 'colspan' in cell:
                client['colspan'] = cell['colspan']
            clients.append(client)

        return clients

    def visit_compat_rows(self, node, children):
        compat_rows = children[0]

        assert isinstance(compat_rows, list), type(compat_rows)
        for row in compat_rows:
            assert isinstance(row, dict), type(row)
        return compat_rows

    def visit_compat_row(self, node, children):
        tr_open = children[0]
        compat_row_cells = children[2]

        assert isinstance(tr_open, dict), type(tr_open)
        assert isinstance(compat_row_cells, list), type(compat_row_cells)
        for cell_list in compat_row_cells:
            assert isinstance(cell_list, list), type(cell_list)
            for cell in cell_list:
                assert isinstance(cell, dict), type(cell)
        row_dict = {
            'cells': compat_row_cells,
        }
        row_dict.update(tr_open)
        return row_dict

    def visit_compat_row_cell(self, node, children):
        td_open = children[0]
        assert isinstance(td_open, dict), type(td_open)
        assert td_open['type'] == 'td'
        compat_row = [
            self._consume_attributes(td_open, ('rowspan', 'colspan'))]

        compat_cell = children[2]
        if isinstance(compat_cell, Node):
            assert compat_cell.start == compat_cell.end
            compat_cell = []
        else:
            assert isinstance(compat_cell, list), type(compat_cell)
            for item in compat_cell:
                assert isinstance(item, dict)
                compat_row.append(item)

        return compat_row

    #
    # Browser Compatibility table cells
    #  Due to rowspan and colspan usage, we won't know if a cell is a feature
    #  or a support until visit_compat_body
    visit_compat_cell_token = _visit_token

    def visit_code_block(self, node, children):
        text = children[2].text
        assert isinstance(text, text_type), type(text)
        return {
            'type': 'code_block',
            'content': self.cleanup_whitespace(text),
            'start': node.start, 'end': node.end}

    def visit_cell_version(self, node, children):
        return {
            'type': 'version',
            'version': node.match.group('version'),
            'eng_version': node.match.group('eng_version'),
            'start': node.start, 'end': node.end}

    def visit_cell_footnote_id(self, node, children):
        item = children[4]
        raw_id = item.match.group('footnote_id')
        if raw_id.isnumeric():
            footnote_id = raw_id
        else:
            footnote_id = text_type(len(raw_id))
        return {
            'type': 'footnote_id',
            'footnote_id': footnote_id,
            'start': node.start, 'end': node.end}

    def visit_cell_removed(self, node, children):
        return {'type': 'removed', 'start': node.start, 'end': node.end}

    def visit_cell_other(self, node, children):
        text = self.cleanup_whitespace(node.text)
        assert 'td>' not in text
        return {
            'type': 'text', 'content': text,
            'start': node.start, 'end': node.end}

    #
    # Optional footnotes after the Browser Compatibility Tables
    #

    def visit_compat_footnotes(self, node, children):
        items = children[0]
        if isinstance(items, Node):
            assert items.start == items.end  # Empty
            return OrderedDict()
        assert isinstance(items, list), type(items)
        for item in items:
            assert isinstance(item, dict), type(item)

        class NoFootnote(object):
            """Placeholder for section without a footnote"""

        # Split tokens into footnote sections
        sections = OrderedDict()
        section = []
        footnote_id = NoFootnote()
        for item in items:
            close_section = False
            item_type = item['type']
            if item_type == 'p_close':
                close_section = True
            elif item_type == 'pre':
                assert not section  # <pre> should be only item
                close_section = True
            elif item_type == 'footnote_id':
                footnote_id = item['footnote_id']
                assert footnote_id not in sections
            elif item_type == 'text':
                if not item['content']:
                    continue
            section.append(item)

            if close_section:
                sections.setdefault(footnote_id, []).append(section)
                if isinstance(footnote_id, NoFootnote):
                    footnote_id = NoFootnote()
                section = []
        assert not section

        # Convert sections
        footnotes = OrderedDict()
        for footnote_id, paragraphs in sections.items():
            start = None
            lines = []
            include_p = (len(paragraphs) > 1)
            for section in paragraphs:
                bits = []
                wrap_p = False
                for item in section:
                    if start is None:
                        start = item['start']
                    item_type = item['type']
                    if item_type == 'p_open':
                        wrap_p = True
                    elif item_type == 'p_close':
                        assert wrap_p
                    elif item_type == 'footnote_id':
                        assert footnote_id == item['footnote_id']
                    elif item_type == 'text':
                        bits.append(item['content'])
                    elif item_type == 'kumascript':
                        text = self.kumascript_to_text(item, 'footnote')
                        if text:
                            bits.append(text)
                    else:
                        assert item_type == 'pre'
                        allowed = {
                            'class': ['brush:css'],
                        }
                        attrs = []
                        for name, vitem in item['attributes'].items():
                            assert name in allowed
                            value = vitem['value']
                            assert value in allowed[name]
                            attrs.append((name, value))
                        attrs.sort()
                        attr_out = " ".join('%s="%s"' % a for a in attrs)
                        attr_space = ' ' if attr_out else ''
                        bits.append('<pre{}{}>{}</pre>'.format(
                            attr_space, attr_out, item['content']))
                line = self.join_content(bits)
                if line:
                    if include_p and wrap_p:
                        lines.append('<p>' + line + '</p>')
                    else:
                        lines.append(line)
            if lines:
                if isinstance(footnote_id, NoFootnote):
                    self.issues.append(
                        ('footnote_no_id', start, item['end'], {}))
                else:
                    footnotes[footnote_id] = (
                        '\n'.join(lines), start, item['end'])
        return footnotes

    visit_footnote_token = _visit_token

    def visit_footnote_id(self, node, children):
        raw_id = children[1].match.group('content')
        if raw_id.isnumeric():
            footnote_id = raw_id
        else:
            footnote_id = text_type(len(raw_id))
        return {
            'type': 'footnote_id',
            'footnote_id': footnote_id,
            'start': node.start, 'end': node.end}

    #
    # Other visitors
    #
    def visit_kumascript(self, node, children):
        name = children[1]
        assert isinstance(name, text_type), type(name)

        argslist = children[2]
        if isinstance(argslist, Node):
            assert argslist.start == argslist.end
            args = []
        else:
            assert isinstance(argslist, list), type(argslist)
            assert len(argslist) == 1
            args = argslist[0]
        assert isinstance(args, list), type(args)
        if args == ['']:
            args = []

        return {
            'type': 'kumascript', 'name': name, 'args': args,
            'start': node.start, 'end': node.end}

    visit_ks_name = _visit_content

    def visit_ks_arglist(self, node, children):
        arg0 = children[1]
        argrest = children[2]
        args = [arg0]
        if isinstance(argrest, Node):
            # No additional args
            assert argrest.start == argrest.end
        else:
            for _, arg in argrest:
                args.append(arg)
        arglist = [text_type(a) for a in args]
        return arglist

    def visit_ks_arg(self, node, children):
        assert isinstance(children, list)
        assert len(children) == 1
        item = children[0]
        assert isinstance(item, text_type)
        return item or EmptyString()

    visit_ks_bare_arg = _visit_content

    def visit_attrs(self, node, children):
        return children  # Even if empty list

    visit_opt_attrs = visit_attrs

    def visit_attr(self, node, children):
        ident = children[1]
        value = children[5][0]

        assert isinstance(ident, text_type), type(ident)
        assert isinstance(value, text_type), type(value)

        return {
            'ident': ident,
            'value': value,
            'start': node.start,
            'end': node.end,
        }

    visit_ident = _visit_content
    visit_bare_text = _visit_content
    visit_single_quoted_text = _visit_content
    visit_double_quoted_text = _visit_content

    def _visit_open(self, node, children, tag):
        """Parse an opening tag with an expected attributes list"""
        attrs = children[2]
        assert isinstance(attrs, list), type(attrs)
        for attr in attrs:
            assert isinstance(attr, dict)

        # Index by attribute ident
        attr_dict = {}
        for attr in attrs:
            ident = attr.pop('ident')
            assert ident not in attr_dict
            attr_dict[ident] = attr

        return {
            'type': tag,
            'attributes': attr_dict,
            'start': node.start,
            'end': node.end,
        }

    def _consume_attributes(self, node_dict, expected):
        """Move attributes to node dict, or add issue."""
        node_out = node_dict.copy()
        attrs = node_out.pop('attributes', {})
        for ident, attr in attrs.items():
            if ident in expected:
                assert ident not in node_out
                node_out[ident] = attr['value']
            else:
                expected_text = (
                    ', '.join(expected[:-1]) + ' or ' + expected[-1])
                self.issues.append((
                    'unexpected_attribute', attr['start'], attr['end'],
                    {'node_type': node_dict['type'], 'ident': ident,
                        'value': attr['value'], 'expected': expected_text}))
        return node_out

    def visit_th_elem(self, node, children):
        th_open = children[0]
        content = children[2][0]
        assert isinstance(th_open, dict), type(th_open)
        if isinstance(content, dict):
            th_open['content'] = content
        else:
            assert isinstance(content, text_type)
            th_open['content'] = {
                'start': children[1].end,
                'end': children[3].start,
                'text': self.cleanup_whitespace(content)
            }
        return th_open

    def visit_td_open(self, node, children):
        return self._visit_open(node, children, 'td')

    def visit_p_open(self, node, children):
        return {'type': 'p_open', 'start': node.start, 'end': node.end}

    def visit_p_close(self, node, children):
        return {'type': 'p_close', 'start': node.start, 'end': node.end}

    def visit_break(self, node, children):
        return {'type': 'break', 'start': node.start, 'end': node.end}

    def visit_pre_block(self, node, children):
        attrs_node = children[1]
        if isinstance(attrs_node, Node):
            attrs = []
        else:
            assert isinstance(attrs_node, list), type(attrs_node)
            attrs = attrs_node[0]
        assert isinstance(attrs, list), type(attrs)

        attr_dict = {}
        for attr in attrs:
            ident = attr.pop('ident')
            assert ident not in attr_dict
            attr_dict[ident] = attr

        text = children[3]
        assert isinstance(text, text_type), type(text)
        return {
            'type': 'pre', 'attributes': attr_dict, 'content': text,
            'start': node.start, 'end': node.end}

    visit_pre_text = _visit_content

    def visit_th_open(self, node, children):
        return self._visit_open(node, children, 'th')

    def visit_tr_open(self, node, children):
        return self._visit_open(node, children, 'tr')

    def visit_strong_text(self, node, children):
        text = children[2]
        assert isinstance(text, text_type), type(text)
        return {
            'start': children[1].end,
            'end': children[3].start,
            'text': self.cleanup_whitespace(text),
            'strong': True
        }

    #
    # Utility methods
    #
    re_whitespace = re.compile(r'''(?x)  # Be verbose
    (\s|                # Any whitespace, or
     (<\s*br\s*/?>)|    # A variant of <br>, or
     \xa0|              # Unicode non-breaking space, or
     (\&nbsp;)          # HTML nbsp character
    )+                  # One or more in a row
    ''')

    def cleanup_whitespace(self, text):
        """Normalize whitespace"""
        normal = self.re_whitespace.sub(' ', text)
        assert '  ' not in normal
        return normal.strip()

    def unquote(self, text):
        """Unquote strings."""
        if text.startswith('"') or text.startswith("'"):
            if text[0] == text[-1]:
                return text[1:-1]
            elif (text.count(text[0]) % 2) != 0:
                raise ValueError(text)
        return text

    def kumascript_issue(self, issue, item, scope):
        """Create an kumascript issue."""
        if item['args']:
            args = '(' + ', '.join(item['args']) + ')'
        else:
            args = ''
        return (
            issue, item['start'], item['end'],
            {'name': item['name'], 'args': item['args'], 'scope': scope,
             'kumascript': "{{%s%s}}" % (item['name'], args)})

    def kumascript_to_text(self, item, scope):
        """Convert kumascript to plain text."""
        assert item['type'] == 'kumascript'
        name = item['name']
        args = item['args']
        if name in (
                'xref_csslength', 'xref_csspercentage',
                'xref_cssstring', 'xref_cssimage'):
            assert not args
            content = name[len('xref_css'):]
            return "<code>&lt;{}&gt;</code>".format(content)
        elif name == 'xref_csscolorvalue':
            assert not args
            return "<code>&lt;color&gt;</code>"
        elif name == 'xref_cssvisual':
            assert not args
            return "<code>visual</code>"
        elif name.lower() in ('cssxref', 'domxref', 'htmlelement', 'jsxref'):
            if len(args) > 1:
                content = args[1]
            else:
                content = args[0]
            return "<code>{}</code>".format(content)
        elif name.lower() == 'specname':
            assert len(args) >= 1
            return 'specification ' + args[0]
        elif name.lower() == 'spec2' and scope == 'specdesc':
            assert len(args) >= 1
            self.issues.append(self.kumascript_issue(
                'specdesc_spec2_invalid', item, scope))
            return 'specification ' + args[0]
        elif name == 'experimental_inline':
            # Don't include beaker in output
            assert not args
        else:
            self.issues.append(
                self.kumascript_issue('unknown_kumascript', item, scope))

    def join_content(self, content_bits):
        """Construct a string with just the right whitespace."""
        out = ""
        nospace_before = '!,.;? '
        nospace_after = ' '
        for bit in content_bits:
            if (out and out[-1] not in nospace_after and
                    bit[0] not in nospace_before):
                out += " "
            out += bit
        return out

    #
    # API lookup methods
    #
    browser_name_fixes = {
        'Firefox (Gecko)': 'Firefox',
        'Firefox Mobile (Gecko)': 'Firefox Mobile',
        'Firefox OS (Gecko)': 'Firefox OS',
        'Safari (WebKit)': 'Safari',
        'Windows Phone': 'IE Mobile',
        'IE Phone': 'IE Mobile',
        'IE': 'Internet Explorer',
    }

    def browser_id_name_and_slug(self, name):
        # Normalize the name
        nname = self.cleanup_whitespace(name)
        fixed_name = self.browser_name_fixes.get(nname, nname)

        # Load existing browser data
        if self._browser_data is None:
            self._browser_data = {}
            for browser in Browser.objects.all():
                key = browser.name[self.locale]
                self._browser_data[key] = (browser.pk, key, browser.slug)

        # Select the Browser ID and slug
        if fixed_name not in self._browser_data:
            browser_id = '_' + nname
            self._browser_data[fixed_name] = (
                browser_id, fixed_name, browser_id)
        return self._browser_data[fixed_name]

    def feature_id_and_slug(self, name):
        """Get or create the feature ID and slug given a name."""
        def normalized(n):
            return n.lower().replace('<code>', '').replace('</code>', '')
        nname = normalized(name)

        # Initialize Feature IDs
        if self._feature_data is None:
            self._feature_data = {}
            for feature in Feature.objects.filter(parent=self.feature):
                if 'zxx' in feature.name:
                    fname = feature.name['zxx']
                else:
                    fname = feature.name.get(self.locale, feature.name['en'])
                fname = normalized(fname)
                self._feature_data[fname] = (feature.id, feature.slug)

        # Select the Feature ID and slug
        if nname not in self._feature_data:
            feature_id = '_' + nname
            attempt = 0
            feature_slug = None
            while not feature_slug:
                base_slug = self.feature.slug + '_' + nname
                feature_slug = slugify(base_slug, suffix=attempt)
                if Feature.objects.filter(slug=feature_slug).exists():
                    attempt += 1
                    feature_slug = ''
            self._feature_data[nname] = (feature_id, feature_slug)

        return self._feature_data[nname]

    def version_id_and_name(self, raw_version, browser):
        version = None

        # Version is format 'x.0', 'x.y', or '' (unknown)
        if not raw_version:
            clean_version = ''
        elif '.' in raw_version:
            clean_version = raw_version
        else:
            clean_version = raw_version + '.0'
        if not is_fake_id(browser['id']):
            # Might be known version
            try:
                version = Version.objects.get(
                    browser=browser['id'], version=clean_version)
            except Version.DoesNotExist:
                pass
        if version:
            # Known version
            version_id = version.id
            version_name = version.version
        else:
            # New version
            version_id = "_%s-%s" % (browser['name'], clean_version)
            version_name = clean_version or ''

        return version_id, version_name

    def support_id(self, version_id, feature_id):
        support = None
        real_version = not is_fake_id(version_id)
        real_feature = not is_fake_id(feature_id)
        if real_version and real_feature:
            # Might be known version
            try:
                support = Support.objects.get(
                    version=version_id, feature=feature_id)
            except Support.DoesNotExist:
                pass
        if support:
            # Known support
            support_id = support.id
        else:
            # New support
            support_id = "_%s-%s" % (feature_id, version_id)
        return support_id

    #
    # Cell parsing
    #
    def cell_to_feature(self, cell):
        """Parse cell items as a feature (first column)"""
        name_bits = []
        name_replacements = [('</code> ,', '</code>,')]
        feature = {}
        assert cell[0]['type'] == 'td'
        for item in cell[1:]:
            if item['type'] == 'break':
                pass  # Discard breaks in feature names
            elif item['type'] == 'text':
                name_bits.append(item['content'])
            elif item['type'] == 'version':
                # Not really a version - need to strip the trailing space
                v = item['version']
                name_replacements.append(('%s ' % v, '%s' % v))
                name_bits.append(v)
            elif item['type'] == 'code_block':
                name_bits.append('<code>%s</code>' % item['content'])
            elif item['type'] == 'kumascript':
                kname = item['name'].lower()
                if kname == 'experimental_inline':
                    assert 'experimental' not in feature
                    feature['experimental'] = True
                elif kname == 'non-standard_inline':
                    assert 'standardized' not in feature
                    feature['standardized'] = False
                elif kname == 'not_standard_inline':
                    assert 'standardized' not in feature
                    feature['standardized'] = False
                elif kname == 'deprecated_inline':
                    assert 'obsolete' not in feature
                    feature['obsolete'] = True
                elif kname == 'htmlelement':
                    name_bits.append(
                        '<code>&lt;%s&gt;</code>' %
                        self.unquote(item['args'][0]))
                elif kname == 'domxref':
                    name_bits.append(self.unquote(item['args'][0]))
                else:
                    self.issues.append(self.kumascript_issue(
                        'unknown_kumascript', item, 'compatibility feature'))
            elif item['type'] == 'footnote_id':
                self.issues.append((
                    'footnote_feature', item['start'], item['end'], {}))
            else:
                raise ValueError("Unknown item!", item)
        assert name_bits
        if (len(name_bits) == 1 and isinstance(name_bits[0], text_type) and
                name_bits[0].startswith('<code>')):
            feature['canonical'] = True
            name = name_bits[0][6:-7]  # Trim out surrounding <code>xx</code>
        else:
            name = ' '.join(name_bits)
            for old, new in name_replacements:
                name = name.replace(old, new)
        f_id, slug = self.feature_id_and_slug(name)
        feature['name'] = name
        feature['id'] = f_id
        feature['slug'] = slug
        return feature

    # From https://developer.mozilla.org/en-US/docs/Template:CompatGeckoDesktop
    geckodesktop_to_firefox = {
        '1': '1.0',
        '1.0': '1.0',
        '1.7 or earlier': '1.0',
        '1.7': '1.0',
        '1.8': '1.5',
        '1.8.1': '2.0',
        '1.9': '3.0',
        '1.9.1': '3.5',
        '1.9.1.4': '3.5.4',
        '1.9.2': '3.6',
        '1.9.2.4': '3.6.4',
        '1.9.2.5': '3.6.5',
        '1.9.2.9': '3.6.9',
        '2': '4.0',
        '2.0': '4.0',
    }

    def cell_to_support(self, cell, feature, browser):
        """Parse a cell as a support (middle cell)."""
        assert feature
        assert browser

        versions = []
        supports = []
        version = {'browser': browser['id']}
        support = {}
        p_depth = 0

        kumascript_compat_versions = [
            'compat' + b for b in ('android', 'chrome', 'ie', 'opera',
                                   'operamobile', 'safari')]

        assert cell[0]['type'] == 'td'
        for item in cell[1:]:
            version_found = None
            version_name = version.get('name')
            if item['type'] == 'version':
                version_found = item['version']
            elif item['type'] == 'footnote_id':
                if 'footnote_id' in support:
                    self.issues.append((
                        'footnote_multiple', item['start'], item['end'],
                        {'prev_footnote_id': support['footnote_id'][0],
                         'footnote_id': item['footnote_id']}))
                else:
                    support['footnote_id'] = (
                        item['footnote_id'], item['start'], item['end'])
            elif item['type'] == 'kumascript':
                kname = item['name'].lower()
                # See https://developer.mozilla.org/en-US/docs/Template:<name>
                if kname == 'compatversionunknown':
                    version_found = ''
                elif kname == 'compatunknown':
                    # Could use support = unknown, but don't bother
                    pass
                elif kname == 'compatno':
                    version_found = ''
                    support['support'] = 'no'
                elif kname == 'property_prefix':
                    support['prefix'] = self.unquote(item['args'][0])
                elif kname == 'compatgeckodesktop':
                    gversion = self.unquote(item['args'][0])
                    version_found = self.geckodesktop_to_firefox.get(gversion)
                    if not version_found:
                        try:
                            nversion = float(gversion)
                        except ValueError:
                            nversion = 0
                        if nversion >= 5:
                            version_found = text_type(nversion)
                        else:
                            version_found = None
                            self.issues.append((
                                'compatgeckodesktop_unknown',
                                item['start'], item['end'],
                                {'version': gversion}))
                elif kname == 'compatgeckofxos':
                    gversion = self.unquote(item['args'][0])
                    try:
                        oversion = self.unquote(item['args'][1])
                    except IndexError:
                        oversion = ''
                    try:
                        nversion = float(gversion)
                    except ValueError:
                        nversion = -1
                    if (nversion >= 0 and nversion < 19 and
                       oversion in ('', '1.0')):
                        version_found = '1.0'
                    elif (nversion >= 0 and nversion < 21 and
                          oversion == '1.0.1'):
                        version_found = '1.0.1'
                    elif (nversion >= 0 and nversion < 24 and
                          oversion in ('1.1', '1.1.0', '1.1.1')):
                        version_found = '1.1'
                    elif (nversion >= 19 and nversion < 27 and
                          oversion in ('', '1.2')):
                        version_found = '1.2'
                    elif (nversion >= 27 and nversion < 29 and
                          oversion in ('', '1.3')):
                        version_found = '1.3'
                    elif (nversion >= 29 and nversion < 31 and
                          oversion in ('', '1.4')):
                        version_found = '1.4'
                    elif (nversion >= 31 and nversion < 33 and
                          oversion in ('', '2.0')):
                        version_found = '2.0'
                    elif (nversion >= 33 and nversion < 35 and
                          oversion in ('', '2.1')):
                        version_found = '2.1'
                    elif (nversion >= 35 and nversion < 38 and
                          oversion in ('', '2.2')):
                        version_found = '2.2'
                    elif nversion < 0 or nversion >= 38:
                        self.issues.append((
                            'compatgeckofxos_unknown',
                            item['start'], item['end'], {'version': gversion}))
                    else:
                        self.issues.append((
                            'compatgeckofxos_override',
                            item['start'], item['end'],
                            {'override': oversion, 'version': gversion}))
                elif kname == 'compatgeckomobile':
                    gversion = self.unquote(item['args'][0])
                    version_found = gversion.split('.', 1)[0]
                    if version_found == '2':
                        version_found = '4'
                elif kname in kumascript_compat_versions:
                    version_found = self.unquote(item['args'][0])
                else:
                    self.issues.append(self.kumascript_issue(
                        'unknown_kumascript', item, 'compatibility cell'))
            elif item['type'] == 'p_open':
                p_depth += 1
                if p_depth > 1:
                    self.issues.append((
                        'nested_p', item['start'], item['end'], {}))
            elif item['type'] == 'p_close' and p_depth > 1:
                # No support for nested <p> tags
                p_depth -= 1
                version = {}
                support = {}
            elif item['type'] == 'break' or (
                    item['type'] == 'p_close' and p_depth == 1):
                # Multi-support cell?
                if version.get('id') and support.get('id'):
                    # We have a complete version and support
                    versions.append(version)
                    supports.append(support)
                    version = {'browser': browser['id']}
                    support = {}
                else:
                    # We don't have a complete version and support
                    assert not version.get('id')
                    assert not support.get('id')
                if item['type'] == 'p_close':
                    p_depth = 0
            elif item['type'] == 'removed':
                support['support'] = 'no'
            elif item['type'] == 'text':
                if item['content']:
                    self.issues.append((
                        'inline_text', item['start'], item['end'],
                        {'text': item['content']}))
            elif item['type'] == 'code_block':
                self.issues.append((
                    'inline_text', item['start'], item['end'],
                    {'text': '<code>{}</code>'.format(item['content'])}))
            else:
                raise ValueError("Unknown item", item)

            # Attempt to find the version in the existing verisons
            if version_found is not None:
                version_id, version_name = self.version_id_and_name(
                    version_found, browser)
                new_version = is_fake_id(version_id)
                new_browser = is_fake_id(browser['id'])
                if new_version and not new_browser:
                    self.issues.append((
                        'unknown_version', item['start'], item['end'],
                        {'browser_id': browser['id'],
                         'browser_name': browser['name'],
                         'version': version_found,
                         'browser_slug': browser.get('slug', '<not loaded>')}))
                version['id'] = version_id
                version['version'] = version_name
                support_id = self.support_id(version_id, feature['id'])
                support['id'] = support_id
                support.setdefault('support', 'yes')
                support['version'] = version_id
                support['feature'] = feature['id']

            # Footnote + prefix => support=partial
            if (support.get('support') == 'yes' and
                    support.get('prefix') and support.get('footnote_id')):
                support['support'] = 'partial'

        if version.get('id') and support.get('id'):
            versions.append(version)
            supports.append(support)
        else:
            assert not version.get('id')
            assert not support.get('id')
            if versions and supports:
                versions[-1].update(version)
                supports[-1].update(support)
        return versions, supports


def scrape_page(mdn_page, feature, locale='en'):
    data = OrderedDict((
        ('locale', locale),
        ('specs', []),
        ('compat', []),
        ('footnotes', None),
        ('issues', []),
    ))
    if not mdn_page.strip():
        return data

    try:
        page_parsed = page_grammar.parse(mdn_page)
    except IncompleteParseError as ipe:
        data['issues'].append((
            'halt_import', ipe.pos, end_of_line(ipe.text, ipe.pos), {}))
        return data
    except ParseError as pe:
        if pe.expr.name == 'doc':
            data['issues'].append((
                'doc_parse_error', pe.pos, end_of_line(pe.text, pe.pos), {}))
            return data
        else:  # pragma: no cover
            # Raise as 'exception' issue to flag for future work
            raise pe

    page_data = PageVisitor(feature).visit(page_parsed)

    data['specs'] = page_data.get('specs', [])
    data['compat'] = page_data.get('compat', [])
    data['issues'] = page_data.get('issues', [])
    data['footnotes'] = page_data.get('footnotes', None)
    return data


class ScrapedViewFeature(object):
    """Combine a scraped MDN page with existing API data.

    This code works with scraping of English feature pages that aren't
    already in the API. Modifications may be needed to:
    - Update API resources from updated MDN pages
    - Scrape pages in non-English languages
    """

    tab_name = {
        'desktop': 'Desktop Browsers',
        'mobile': 'Mobile Browsers',
    }

    def __init__(self, feature_page, scraped_data):
        self.feature_page = feature_page
        self.feature = feature_page.feature
        self.scraped_data = scraped_data
        self.resources = OrderedDict()
        for resource_type in (
                'specifications', 'maturities', 'sections', 'browsers',
                'versions', 'features', 'supports'):
            self.resources[resource_type] = {}
        self.tabs = []
        self.compat_table_supports = OrderedDict(
            ((text_type(self.feature.id), {}),))
        self.notes = OrderedDict()

    def generate_data(self):
        """Combine the page and scraped data into view_feature structure."""
        fp_data = self.feature_page.reset_data()
        fp_data['meta']['scrape']['raw'] = self.scraped_data

        for spec_row in self.scraped_data['specs']:
            self.load_specification_row(spec_row)
        for table in self.scraped_data['compat']:
            self.load_compat_table(table)
        for section in self.resources['sections'].values():
            fp_data['features']['links']['sections'].append(section['id'])

        for resource_type, resources in self.resources.items():
            fp_data['linked'][resource_type] = self.sort_values(resources)
        languages = fp_data['features']['mdn_uri'].keys()
        fp_data['meta']['compat_table']['languages'] = list(languages)
        fp_data['meta']['compat_table']['tabs'] = self.tabs
        fp_data['meta']['compat_table']['supports'] = (
            self.compat_table_supports)
        fp_data['meta']['compat_table']['notes'] = self.notes
        return fp_data

    def load_specification_row(self, spec_row):
        """Load Specification, Maturity, and Section"""
        # Load Specification and Maturity
        if spec_row['specification.id']:
            spec_content, mat_content = self.load_specification(
                spec_row['specification.id'])
        else:
            spec_content, mat_content = self.new_specification(spec_row)
        self.add_resource('specifications', spec_content)
        self.add_resource('maturities', mat_content)

        # Load Specification Section
        if spec_row['section.id']:
            section_content = self.load_section(spec_row['section.id'])
            section_content['name']['en'] = spec_row['section.name']
            section_content['subpath']['en'] = spec_row['section.subpath']
            section_content['note']['en'] = spec_row['section.note']
        else:
            section_content = self.new_section(spec_row, spec_content['id'])
        self.add_resource('sections', section_content)

    def load_compat_table(self, table):
        """Load a compat table."""
        tab = OrderedDict((
            ("name",
             {"en": self.tab_name.get(table['name'], 'Other Environments')}),
            ("browsers", []),
        ))
        # Load Browsers (first row)
        for browser_entry in table['browsers']:
            if is_fake_id(browser_entry['id']):
                browser_content = self.new_browser(browser_entry)
            else:
                browser_content = self.load_browser(browser_entry['id'])
            self.add_resource('browsers', browser_content)
            tab['browsers'].append(text_type(browser_content['id']))

        # Load Features (first column)
        for feature_entry in table['features']:
            if is_fake_id(feature_entry['id']):
                feature_content = self.new_feature(feature_entry)
            else:
                feature_content = self.load_feature(feature_entry['id'])
            self.add_resource_if_new('features', feature_content)
            self.compat_table_supports.setdefault(
                text_type(feature_content['id']), OrderedDict())

        # Load Versions (explicit or implied in cells)
        for version_entry in table['versions']:
            if is_fake_id(version_entry['id']):
                version_content = self.new_version(version_entry)
            else:
                version_content = self.load_version(version_entry['id'])
            self.add_resource_if_new('versions', version_content)

        # Load Supports (cells)
        for support_entry in table['supports']:
            if is_fake_id(support_entry['id']):
                support_content = self.new_support(support_entry)
            else:
                support_content = self.load_support(support_entry['id'])
            self.add_resource_if_new('supports', support_content)
            if support_content['note']:
                note_id = len(self.notes) + 1
                self.notes[support_content['id']] = note_id

            # Set the meta lookup
            version = self.get_resource(
                'versions', support_content['links']['version'])
            feature_id = support_content['links']['feature']
            browser_id = version['links']['browser']
            supports = self.compat_table_supports[feature_id]
            supports.setdefault(browser_id, [])
            supports[browser_id].append(support_entry['id'])
        self.tabs.append(tab)

    def add_resource(self, resource_type, content):
        """Add a linked resource, replacing any existing resource."""
        resource_id = content['id']
        self.resources[resource_type][resource_id] = content

    def add_resource_if_new(self, resource_type, content):
        """Add a linked resource only if there is no existing resource."""
        resource_id = content['id']
        return self.resources[resource_type].setdefault(resource_id, content)

    def get_resource(self, resource_type, resource_id):
        """Get an existing linked resource."""
        return self.resources[resource_type][resource_id]

    def sort_values(self, d):
        """Return dictionary values, sorted by keys."""
        existing_keys = sorted([k for k in d.keys() if not is_fake_id(k)])
        new_keys = sorted([k for k in d.keys() if is_fake_id(k)])
        return list(d[k] for k in chain(existing_keys, new_keys))

    def load_specification(self, spec_id):
        """Serialize an existing specification."""
        spec = Specification.objects.get(id=spec_id)
        section_ids = [
            text_type(s_id) for s_id in spec.sections.values_list(
                'id', flat=True)]
        spec_content = OrderedDict((
            ('id', text_type(spec_id)),
            ('slug', spec.slug),
            ('mdn_key', spec.mdn_key),
            ('name', spec.name),
            ('uri', spec.uri),
            ('links', OrderedDict((
                ('maturity', text_type(spec.maturity_id)),
                ('sections', section_ids)
            )))))
        mat = spec.maturity
        mat_content = OrderedDict((
            ('id', text_type(mat.id)),
            ('slug', mat.slug),
            ('name', mat.name)))
        return spec_content, mat_content

    def new_specification(self, spec_row):
        """Serialize a new specification."""
        spec_id = '_' + spec_row['specification.mdn_key']
        mat_id = '_unknown'
        spec_content = OrderedDict((
            ('id', spec_id),
            ('mdn_key', spec_row['specification.mdn_key']),
            ('links', OrderedDict((
                ('maturity', mat_id),
                ('sections', [])
            )))))
        mat_content = self.add_resource_if_new(
            'maturities', OrderedDict((
                ('id', mat_id),
                ('slug', ''),
                ('name', {'en': 'Unknown'}),
                ('links', {'specifications': []}))))
        return spec_content, mat_content

    def load_section(self, section_id):
        """Serialize an existing section."""
        section = Section.objects.get(id=section_id)
        section_content = OrderedDict((
            ('id', text_type(section_id)),
            ('number', section.number or None),
            ('name', section.name),
            ('subpath', section.subpath),
            ('note', section.note),
            ('links', OrderedDict((
                ('specification', text_type(section.specification_id)),)))))
        return section_content

    def new_section(self, spec_row, spec_id):
        """Serialize a new section."""
        section_id = text_type(spec_id) + '_' + spec_row['section.subpath']
        section_content = OrderedDict((
            ('id', section_id),
            ('number', None),
            ('name', OrderedDict()),
            ('subpath', OrderedDict()),
            ('note', OrderedDict()),
            ('links', OrderedDict((
                ('specification', text_type(spec_id)),)))))
        section_content['name']['en'] = spec_row['section.name']
        section_content['subpath']['en'] = spec_row['section.subpath']
        section_content['note']['en'] = spec_row['section.note']
        return section_content

    def load_browser(self, browser_id):
        """Serialize an existing browser."""
        browser = Browser.objects.get(id=browser_id)
        browser_content = OrderedDict((
            ('id', text_type(browser.id)),
            ('slug', browser.slug),
            ('name', browser.name),
            ('note', browser.note or None),
        ))
        return browser_content

    def new_browser(self, browser_entry):
        """Serialize a new browser."""
        browser_content = OrderedDict((
            ('id', browser_entry['id']),
            ('slug', ''),
            ('name', {'en': browser_entry['name']}),
            ('note', None),
        ))
        return browser_content

    def load_feature(self, feature_id):
        """Serialize an existing feature."""
        feature = Feature.objects.get(id=feature_id)
        section_ids = [
            text_type(s_id) for s_id in
            feature.sections.values_list('pk', flat=True)]
        support_ids = [
            text_type(s_id) for s_id in
            sorted(feature.supports.values_list('pk', flat=True))]
        parent_id = (
            text_type(feature.parent_id) if feature.parent_id
            else None)
        children_ids = [
            text_type(c_id) for c_id in
            feature.children.values_list('pk', flat=True)]
        feature_content = OrderedDict((
            ('id', text_type(feature_id)),
            ('slug', feature.slug),
            ('mdn_uri', feature.mdn_uri or None),
            ('experimental', feature.experimental),
            ('standardized', feature.standardized),
            ('stable', feature.stable),
            ('obsolete', feature.obsolete),
            ('name', feature.name),
            ('links', OrderedDict((
                ('sections', section_ids),
                ('supports', support_ids),
                ('parent', parent_id),
                ('children', children_ids))))))
        if list(feature.name.keys()) == ['zxx']:
            feature_content['name'] = feature.name['zxx']
        return feature_content

    def new_feature(self, feature_entry):
        """Serialize a new feature."""
        if feature_entry.get('canonical'):
            fname = feature_entry['name']
        else:
            fname = {'en': feature_entry['name']}
        feature_content = OrderedDict((
            ('id', feature_entry['id']),
            ('slug', feature_entry['slug']),
            ('mdn_uri', None),
            ('experimental', feature_entry.get('experimental', False)),
            ('standardized', feature_entry.get('standardized', True)),
            ('stable', feature_entry.get('stable', True)),
            ('obsolete', feature_entry.get('obsolete', False)),
            ('name', fname),
            ('links', OrderedDict((
                ('sections', []),
                ('supports', []),
                ('parent', text_type(self.feature.id)),
                ('children', []))))))
        return feature_content

    def load_version(self, version_id):
        """Serialize an existing version."""
        version = Version.objects.get(id=version_id)
        version_content = OrderedDict((
            ('id', text_type(version.id)),
            ('version', version.version or None),
            ('release_day', date_to_iso(version.release_day)),
            ('retirement_day', date_to_iso(version.retirement_day)),
            ('status', version.status),
            ('release_notes_uri', version.release_notes_uri or None),
            ('note', version.note or None),
            ('order', version._order),
            ('links', OrderedDict((
                ('browser', text_type(version.browser_id)),)))))
        return version_content

    def new_version(self, version_entry):
        """Serialize a new version."""
        version_content = OrderedDict((
            ('id', version_entry['id']),
            ('version', version_entry['version'] or None),
            ('release_day', None),
            ('retirement_day', None),
            ('status', 'unknown'),
            ('release_notes_uri', None),
            ('note', None),
            ('links', OrderedDict((
                ('browser', text_type(version_entry['browser'])),)))))
        return version_content

    def load_support(self, support_id):
        """Serialize an existing support."""
        support = Support.objects.get(id=support_id)
        support_content = OrderedDict((
            ('id', text_type(support.id)),
            ('support', support.support),
            ('prefix', support.prefix or None),
            ('prefix_mandatory', support.prefix_mandatory),
            ('alternate_name', support.alternate_name or None),
            ('alternate_mandatory', support.alternate_mandatory),
            ('requires_config', support.requires_config or None),
            ('default_config', support.default_config or None),
            ('protected', support.protected),
            ('note', support.note or None),
            ('links', OrderedDict((
                ('version', text_type(support.version_id)),
                ('feature', text_type(support.feature_id)))))))
        return support_content

    def new_support(self, support_entry):
        """Serialize a new support."""
        support_content = OrderedDict((
            ('id', support_entry['id']),
            ('support', support_entry['support']),
            ('prefix', support_entry.get('prefix')),
            ('prefix_mandatory', bool(support_entry.get('prefix', False))),
            ('alternate_name', support_entry.get('alternate_name')),
            ('alternate_mandatory',
                support_entry.get('alternate_mandatory', False)),
            ('requires_config', support_entry.get('requires_config')),
            ('default_config', support_entry.get('default_config')),
            ('protected', support_entry.get('protected', False)),
            ('note', None),
            ('links', OrderedDict((
                ('version', text_type(support_entry['version'])),
                ('feature', text_type(support_entry['feature'])))))))
        if support_entry.get('footnote'):
            support_content['note'] = {'en': support_entry['footnote']}
        return support_content


def scrape_feature_page(feature_page):
    """Scrape a FeaturePage object"""
    en_content = feature_page.translatedcontent_set.get(locale='en-US')
    scraped_data = scrape_page(en_content.raw, feature_page.feature)
    view_feature = ScrapedViewFeature(feature_page, scraped_data)
    merged_data = view_feature.generate_data()

    # Add issues
    for issue in scraped_data['issues']:
        feature_page.add_issue(issue, 'en-US')
    merged_data['meta']['scrape']['issues'] = (
        feature_page.data['meta']['scrape']['issues'])

    # Update status, issues
    has_data = (scraped_data['specs'] or scraped_data['compat'] or
                scraped_data['issues'])
    if has_data:
        feature_page.status = feature_page.STATUS_PARSED
    else:
        feature_page.status = feature_page.STATUS_NO_DATA
    merged_data['meta']['scrape']['phase'] = feature_page.get_status_display()
    feature_page.data = merged_data
    feature_page.save()


#
# Utility methods
#
def date_to_iso(date):
    """Convert a datetime.Date to the ISO 8601 format, or None"""
    if date:
        return date.isoformat()
    else:
        return None


def end_of_line(text, pos):
    """Get the position of the end of the line from pos"""
    try:
        return text.index('\n', pos)
    except ValueError:
        return len(text)


def is_fake_id(_id):
    # Detect if an ID is a real ID
    return isinstance(_id, text_type) and _id[0] == '_'


def slugify(word, length=50, suffix=""):
    """Create a slugged version of a word or phrase"""
    raw = word.lower()
    out = []
    acceptable = string.ascii_lowercase + string.digits + '_-'
    for c in raw:
        if c in acceptable:
            out.append(c)
        else:
            out.append('_')
    slugged = ''.join(out)
    while '__' in slugged:
        slugged = slugged.replace('__', '_')
    suffix = text_type(suffix) if suffix else ""
    with_suffix = slugged[slice(length - len(suffix))] + suffix
    return with_suffix
