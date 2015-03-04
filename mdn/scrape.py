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

from django.utils.html import escape
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
specname_td = td_open _ kuma "</td>"
spec2_td = td_open _ kuma "</td>"
specdesc_td = td_open _ inner_td _ "</td>"
inner_td = ~r"(?P<content>.*?(?=</td>))"s

#
# Browser Compatibility section
#
compat_section = _ compat_h2 _ compat_kuma _ compat_divs p_empty*
    compat_footnotes?
compat_h2 = "<h2 " _ attrs? _ ">" _ compat_title _ "</h2>"
compat_title = ~r"(?P<content>Browser [cC]ompat[ai]bility)"
compat_kuma = (compat_kuma_div / compat_kuma_p)
compat_kuma_div = "<div>" _ kuma "</div>"
compat_kuma_p = "<p>" _ kuma "</p>"
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
compat_cell = compat_cell_item*
compat_cell_item = (kuma / cell_break / code_block / cell_p_open /
    cell_p_close / cell_version / cell_footnote_id / cell_removed / cell_other)
cell_break = "<" _ "br" _ ("/>" / ">") _
code_block = "<code>" _ code_text _ "</code>" _
code_text = ~r"(?P<content>.*?(?=</code>))"s
cell_p_open = "<p>" _
cell_p_close = "</p>" _
cell_version = ~r"(?P<version>\d+(\.\d+)*)"""
    r"""(\s+\((?P<eng_version>\d+(\.\d+)*)\))?\s*"s
cell_removed = ~r"[Rr]emoved\s+[Ii]n\s*"s
cell_footnote_id = "<sup>"? _ a_open? _ ~r"\[(?P<footnote_id>\d+|\*+)\]\s*"s _
    "</a>"? _ "</sup>"?
cell_other = ~r"(?P<content>[^{<[]+)\s*"s

#
# Optional footnotes after the Browser Compatibility Tables
#
compat_footnotes = footnote_item* _
footnote_item = (footnote_p / footnote_pre)
footnote_p = "<p>" a_both? _ footnote_id? _ footnote_p_text "</p>" _
footnote_id = "[" ~r"(?P<content>\d+|\*+)" "]"
footnote_p_text = ~r"(?P<content>.*?(?=</p>))"s
footnote_pre = "<pre" attrs? ">" footnote_pre_text "</pre>" _
footnote_pre_text = ~r"(?P<content>.*?(?=</pre>))"s

#
# Common tokens
#
kuma = kuma_esc_start kuma_name kuma_arglist? kuma_esc_end
kuma_esc_start = "{{" _
kuma_name = ~r"(?P<content>[^\(\}\s]*)\s*"s
kuma_arglist = kuma_func_start kuma_arg kuma_arg_rest* kuma_func_end
kuma_func_start = "(" _
kuma_func_arg = _ "," _
kuma_func_end = _ ")" _
kuma_esc_end = "}}" _
kuma_arg = (double_quoted_text / single_quoted_text / kuma_bare_arg)
kuma_bare_arg = ~r"(?P<content>.*?(?=[,)]))"
kuma_arg_rest = kuma_func_arg kuma_arg

th_elems = th_elem+
th_elem = th_open _ (strong_text / bare_text) "</th>" _
tr_open = "<tr" _ opt_attrs ">"
th_open = "<th" _ opt_attrs ">"
td_open = "<td" _ opt_attrs ">"
a_open = "<a" _  opt_attrs ">"
a_both = _ a_open _ "</a>" _

p_empty = _ "<p>" _ "&nbsp;"* _ "</p>" _

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
    - 'issues': Ignorable issues with the parsed page
    - 'errors': Problems that a human should deal with.
    """
    def __init__(self, feature, locale='en'):
        super(PageVisitor, self).__init__()
        self.feature = feature
        assert isinstance(feature, Feature), type(feature)
        self.locale = locale
        self.specs = []
        self.issues = []
        self.errors = []
        self.compat = []
        self.footnotes = None
        self._browser_data = None
        self._feature_data = None

    def generic_visit(self, node, visited_children):
        """Visitor when none is specified."""
        return visited_children or node

    def _visit_content(self, node, args):
        """Vistor for re nodes with a named (?P<content>) section."""
        return node.match.group('content')

    def visit_doc(self, node, children):
        """At the top level, return all the collected data."""
        return {
            'specs': self.specs,
            'locale': self.locale,
            'issues': self.issues,
            'errors': self.errors,
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
                    if self.errors:
                        rule = pe.expr
                        description = (
                            'Section <h2>%s</h2> was not parsed.'
                            ' The parser failed on rule "%s", but the real'
                            ' cause is probably earlier issues. Definition:'
                            % (title, rule.name))
                        self.errors.append((
                            pe.pos + start,
                            end_of_line(pe.text, pe.pos) + start,
                            description, rule.as_rule()))
                    else:
                        rule = pe.expr
                        description = (
                            'Section <h2>%s</h2> was not parsed. The parser'
                            ' failed on rule "%s", but the real cause may be'
                            ' unexpected content after this position.'
                            ' Definition:' % (title, rule.name))
                        self.errors.append((
                            pe.pos + start,
                            end_of_line(pe.text, pe.pos) + start,
                            description, rule.as_rule()))

                else:  # pragma: nocover
                    error = (
                        start, end_of_line(text, 0) + start,
                        "Section %s not parsed, probably due to earlier"
                        " errors." % title)
                    self.errors.append(error)

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
                    issue = (
                        'In Specifications section, expected <h2'
                        ' id="Specifications">, actual id=' '"%s"' % h2_id)
                    self.issues.append((attr['start'], attr['end'], issue))
            elif attr['ident'] == 'name':
                h2_name = attr['value']
                if h2_name not in expected:
                    issue = (
                        'In Specifications section, expected <h2'
                        ' name="Specifications"> or no name attribute,'
                        ' actual name="%s"' % h2_name)
                    self.issues.append((attr['start'], attr['end'], issue))

    def visit_spec_row(self, node, children):
        specname = children[2]
        assert isinstance(specname, tuple), type(specname)
        key, spec_id, path, name = specname

        spec2_key = children[4]
        assert isinstance(spec2_key, text_type), spec2_key
        if spec2_key != key:
            self.errors.append((
                node.start, node.end,
                ('SpecName(%s, ...) does not match Spec2(%s)'
                 % (spec2_key, key))))
            spec2_key = key

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
        kuma = children[2]
        assert isinstance(kuma, dict), type(kuma)
        assert kuma['name'].lower() == 'specname'
        key = self.unquote(kuma["args"][0])
        subpath = ""
        name = ""
        try:
            subpath = self.unquote(kuma["args"][1])
            name = self.unquote(kuma["args"][2])
        except IndexError:
            pass  # subpath and name can be empty

        try:
            spec = Specification.objects.get(mdn_key=key)
        except Specification.DoesNotExist:
            spec_id = None
            self.errors.append(
                (node.start, node.end, 'Unknown Specification "%s"' % key))
        else:
            spec_id = spec.id
        return (key, spec_id, subpath, name)

    def visit_spec2_td(self, node, children):
        kuma = children[2]
        assert isinstance(kuma, dict), type(kuma)
        assert kuma['name'].lower() == 'spec2'
        assert len(kuma["args"]) == 1
        key = self.unquote(kuma["args"][0])
        assert isinstance(key, text_type), type(key)
        return key

    def visit_specdesc_td(self, node, children):
        text = children[2]
        assert isinstance(text, text_type), type(text)
        return text

    visit_inner_td = _visit_content

    #
    # Browser Compatibility section
    #
    def visit_compat_section(self, node, children):
        compat_divs = children[5]
        footnotes = children[7][0]

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
                        self.errors.append(
                            (f_start, f_end,
                             'Footnote [%s] not found' % f_id))
                    else:
                        support['footnote'] = text
                        used_footnotes.add(f_id)

        for f_id in used_footnotes:
            del footnotes[f_id]

        for f_id, (text, start, end) in footnotes.items():
            self.errors.append(
                (start, end, 'Footnote [%s] not used' % f_id))

        self.compat = compat_divs
        self.footnotes = footnotes

    def visit_compat_kuma(self, node, children):
        assert isinstance(children, list), type(children)
        kuma = children[0][2]
        assert isinstance(kuma, dict), type(kuma)
        assert kuma['type'] == 'kuma'
        assert kuma['name'].lower() == 'compatibilitytable'

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
                col = table[row].index(None)
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
            issue = 'Expected header "Feature"'
            self.issues.append((fcontent['start'], fcontent['end'], issue))

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
                issue = 'Unknown Browser "%s"' % name
                self.errors.append((content['start'], content['end'], issue))
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

    def visit_compat_cell_item(self, node, children):
        item = children[0]
        assert isinstance(item, dict), type(item)
        return item

    def visit_cell_break(self, node, children):
        return {'type': 'break', 'start': node.start, 'end': node.end}

    def visit_code_block(self, node, children):
        text = children[2].text
        assert isinstance(text, text_type), type(text)
        return {
            'type': 'code_block',
            'content': self.cleanup_whitespace(text),
            'start': node.start, 'end': node.end}

    def visit_cell_p_open(self, node, children):
        return {'type': 'p_open', 'start': node.start, 'end': node.end}

    def visit_cell_p_close(self, node, children):
        return {'type': 'p_close', 'start': node.start, 'end': node.end}

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
            footnote_id = str(len(raw_id))
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

        footnotes = OrderedDict()
        footnote = []

        def add_footnote(footnote):
            f_id = footnote[0]['footnote_id']
            start = footnote[0]['start']
            end = footnote[-1]['end']
            assert f_id not in footnotes
            text = self.format_footnote(footnote)
            footnotes[f_id] = (text, start, end)

        for item in items:
            if not footnote:
                # First should be a footnote
                if 'footnote_id' in item:
                    footnote.append(item)
                else:
                    self.errors.append((
                        item['start'], item['end'], "No ID in footnote."))
            elif item.get('footnote_id'):
                # New footnote
                add_footnote(footnote)
                footnote = [item]
            else:
                # Continue footnote
                footnote.append(item)

        if footnote:
            add_footnote(footnote)
        return footnotes

    def visit_footnote_item(self, node, children):
        item = children[0]
        assert isinstance(item, dict), type(item)
        return item

    def visit_footnote_p(self, node, children):
        footnote_id = children[3]
        text = children[5]
        assert isinstance(text, text_type), type(text)
        fixed = self.render_footnote_kuma(text, node.children[4].start)
        data = {
            'type': 'p', 'content': fixed,
            'start': node.start, 'end': node.end}
        if isinstance(footnote_id, list):
            data['footnote_id'] = footnote_id[0]
        return data

    def visit_footnote_id(self, node, children):
        raw_id = children[1].match.group('content')
        if raw_id.isnumeric():
            footnote_id = raw_id
        else:
            footnote_id = str(len(raw_id))
        return footnote_id

    visit_footnote_p_text = _visit_content

    def visit_footnote_pre(self, node, children):
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

    visit_footnote_pre_text = _visit_content

    #
    # Other visitors
    #
    def visit_kuma(self, node, children):
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

        return {
            'type': 'kuma', 'name': name, 'args': args,
            'start': node.start, 'end': node.end}

    visit_kuma_name = _visit_content

    def visit_kuma_arglist(self, node, children):
        arg0 = children[1]
        argrest = children[2]
        args = []
        if arg0:
            args.append(arg0)
        if isinstance(argrest, Node):
            # No additional args
            assert argrest.start == argrest.end
        else:
            for _, arg in argrest:
                args.append(arg)
        return args

    def visit_kuma_arg(self, node, children):
        assert isinstance(children, list)
        assert len(children) == 1
        item = children[0]
        assert isinstance(item, text_type)
        return item

    visit_kuma_bare_arg = _visit_content

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
                self.issues.append((
                    attr['start'], attr['end'],
                    "Unexpected attribute <%s %s=\"%s\">" % (
                        node_dict['type'], ident, attr['value'])))
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
        """Unquote strings.

        Used in the footnotes parser.  Might be removed if it is replaced with
        a compat_cell tokenizer using kuma rule
        """
        if text.startswith('"') or text.startswith("'"):
            if text[0] != text[-1]:
                raise ValueError(text)
            return text[1:-1]
        return text

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
            elif item['type'] == 'kuma':
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
                    if item['args']:
                        args = '(' + ', '.join(item['args']) + ')'
                    else:
                        args = ''
                    self.errors.append((
                        item['start'], item['end'],
                        'Unknown kuma function %s%s' % (item['name'], args)))
            elif item['type'] == 'footnote_id':
                self.errors.append((
                    item['start'], item['end'],
                    'Footnotes are not allowed on features'))
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

        kuma_compat_versions = [
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
                    self.errors.append((
                        item['start'], item['end'],
                        'Only one footnote allowed.'))
                else:
                    support['footnote_id'] = (
                        item['footnote_id'], item['start'], item['end'])
            elif item['type'] == 'kuma':
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
                            self.errors.append((
                                item['start'], item['end'],
                                'Unknown Gecko version "%s"' % gversion))
                elif kname == 'compatgeckomobile':
                    gversion = self.unquote(item['args'][0])
                    version_found = gversion.split('.', 1)[0]
                    if version_found == '2':
                        version_found = '4'
                elif kname in kuma_compat_versions:
                    version_found = self.unquote(item['args'][0])
                else:
                    if item['args']:
                        args = '(' + ', '.join(item['args']) + ')'
                    else:
                        args = ''
                    self.errors.append((
                        item['start'], item['end'],
                        'Unknown kuma function %s%s' % (item['name'], args)))
            elif item['type'] == 'p_open':
                p_depth += 1
                if p_depth > 1:
                    self.errors.append((
                        item['start'], item['end'],
                        'Nested <p> tags not supported'))
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
                    # Inline text requires human intervention to move to a
                    #  footnote, convert to a normal version, or remove.
                    self.errors.append((
                        item['start'], item['end'],
                        'Unknown support text "%s"' % item['content']))
            elif item['type'] == 'code_block':
                self.errors.append((
                    item['start'], item['end'],
                    'Unknown support text <code>%s</code>' %
                    item['content']))
            else:
                raise ValueError("Unknown item", item)

            # Attempt to find the version in the existing verisons
            if version_found is not None:
                version_id, version_name = self.version_id_and_name(
                    version_found, browser)
                if is_fake_id(version_id) and not is_fake_id(browser['id']):
                    self.errors.append((
                        item['start'], item['end'],
                        'Unknown version "%s" for browser "%s"'
                        ' (id %d, slug "%s")' % (
                            version_found, browser['name'], browser['id'],
                            browser.get('slug', '<not loaded>'))))
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

    #
    # Footnote parsing
    #
    def format_footnote(self, footnote):
        if len(footnote) == 1 and footnote[0]['type'] in ('p',):
            return footnote[0]['content']
        else:
            bits = []
            fmt = "%(tag)s%(content)s</%(type)s>"
            for item in footnote:
                i = item.copy()
                if i.get('attributes'):
                    attrs = [
                        (k, v['value']) for k, v in i['attributes'].items()]
                    attrs.sort()
                    attr_out = " ".join('%s="%s"' % a for a in attrs)
                    i['tag'] = '<%s %s>' % (i['type'], attr_out)
                else:
                    i['tag'] = '<%s>' % i['type']
                bits.append(fmt % i)
            return "\n".join(bits)

    re_kuma = re.compile(r'''(?x)(?s)  # Be verbose, . include newlines
    {{\s*               # Kuma start, with optional whitespace
    (?P<name>\w+)       # Function name, optionally followed by...
      (\((?P<args>\s*   # Open parens and whitespace,
       [^)]+            # Stuff in front of the parens,
       )\))?            # Closing parens
    \s*}}               # Whitespace and Kuma close
    ''')

    def render_footnote_kuma(self, text, start):
        rendered = text
        for match in self.re_kuma.finditer(text):
            name = match.group('name')
            kname = name.lower()
            kuma = match.group()
            if match.group('args'):
                arglist = match.group('args').split(',')
            else:
                arglist = []

            if kname == 'cssxref':
                # https://developer.mozilla.org/en-US/docs/Template:cssxref
                # The MDN version does a lookup and creates a link
                # This version just turns it into a code block
                kuma = "<code>%s</code>" % self.unquote(arglist[0])
            else:
                kuma = ""
                if arglist:
                    args = '(' + ', '.join(arglist) + ')'
                else:
                    args = ''
                self.errors.append((
                    start + match.start(), start + match.end(),
                    "Unknown footnote kuma function %s%s" % (name, args)))
            rendered = (
                rendered[:match.start()] + kuma + rendered[match.end():])
        return rendered


def scrape_page(mdn_page, feature, locale='en'):
    data = OrderedDict((
        ('locale', locale),
        ('specs', []),
        ('compat', []),
        ('footnotes', None),
        ('issues', []),
        ('errors', []),
    ))
    if '<h2' not in mdn_page:
        data['errors'].append('No <h2> found in page')
        return data

    try:
        page_parsed = page_grammar.parse(mdn_page)
    except IncompleteParseError as ipe:
        error = (
            ipe.pos, end_of_line(ipe.text, ipe.pos),
            'Unable to finish parsing MDN page, starting at this position.')
        data['errors'].append(error)
        return data
    except ParseError as pe:  # pragma: no cover
        # TODO: Add a test once we know how to trigger
        # Because the rules include optional sections, parse issues mostly
        # appear as IncompleteParseError or skipping a section.  A small
        # change to the rules may turn these into ParseErrors instead.
        # PageVisitor.visit_other_section() handles skipped sections.
        rule = pe.expr
        error = (
            pe.pos, end_of_line(pe.text, pe.pos),
            'Rule "%s" failed to match.  Rule definition:' % rule.name,
            rule.as_rule())
        data['errors'].append(error)
        return data
    page_data = PageVisitor(feature).visit(page_parsed)

    data['specs'] = page_data.get('specs', [])
    data['compat'] = page_data.get('compat', [])
    data['issues'] = page_data.get('issues', [])
    data['errors'] = page_data.get('errors', [])
    data['footnotes'] = page_data.get('footnotes', None)
    return data


def scrape_feature_page(fp):
    """Scrape a FeaturePage object"""
    en_content = fp.translatedcontent_set.get(locale='en-US')
    fp_data = fp.reset_data()
    main_feature_id = text_type(fp.feature.id)
    data = scrape_page(en_content.raw, fp.feature)
    fp_data['meta']['scrape']['raw'] = data

    # Load specification section data
    specifications = {}
    maturities = {}
    sections = {}
    for row in data['specs']:
        # Load Specifications and Maturity
        spec_id = row['specification.id']
        if spec_id:
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
            specifications[spec_id] = spec_content

            mat = spec.maturity
            mat_content = OrderedDict((
                ('id', text_type(mat.id)),
                ('slug', mat.slug),
                ('name', mat.name)))
            maturities[mat.id] = mat_content
        else:
            spec_id = '_' + row['specification.mdn_key']
            spec_content = OrderedDict((
                ('id', spec_id),
                ('mdn_key', row['specification.mdn_key']),
                ('links', OrderedDict((
                    ('maturity', '_unknown'),
                    ('sections', [])
                )))))
            specifications[spec_id] = spec_content

            mat = maturities.get('_unknown', OrderedDict((
                ('id', '_unknown'),
                ('slug', ''),
                ('name', {'en': 'Unknown'}),
                ('links', {'specifications': []}))))
            maturities['_unknown'] = mat

        # Load (specification) Section
        section_id = row['section.id']
        if section_id:
            section = Section.objects.get(id=section_id)
            feature_ids = [
                text_type(f_id) for f_id in section.features.values_list(
                    'id', flat=True)]
            if main_feature_id not in feature_ids:
                feature_ids.append(main_feature_id)
            section_content = OrderedDict((
                ('id', text_type(section_id)),
                ('number', section.number or None),
                ('name', section.name),
                ('subpath', section.subpath),
                ('note', section.note),
                ('links', OrderedDict((
                    ('specification', text_type(spec_id)),)))))
        else:
            section_id = text_type(spec_id) + '_' + row['section.subpath']
            section_content = OrderedDict((
                ('id', section_id),
                ('number', None),
                ('name', OrderedDict()),
                ('subpath', OrderedDict()),
                ('note', OrderedDict()),
                ('links', OrderedDict((
                    ('specification', text_type(spec_id)),)))))
        section_content['name']['en'] = row['section.name']
        section_content['subpath']['en'] = row['section.subpath']
        section_content['note']['en'] = row['section.note']
        sections[section_id] = section_content
        fp_data['features']['links']['sections'].append(text_type(section_id))

    # Load compatibility section
    tabs = []
    browsers = {}
    versions = {}
    features = {}
    supports = {}
    compat_table_supports = OrderedDict(((text_type(fp.feature.id), {}),))
    footnotes = OrderedDict()
    tab_name = {
        'desktop': 'Desktop Browsers',
        'mobile': 'Mobile Browsers',
    }
    for table in data['compat']:
        tab = OrderedDict((
            ("name",
             {"en": tab_name.get(table['name'], 'Other Environments')}),
            ("browsers", []),
        ))
        # Load Browsers (first row)
        for b in table['browsers']:
            if is_fake_id(b['id']):
                browser_content = OrderedDict((
                    ('id', b['id']),
                    ('slug', ''),
                    ('name', {'en': b['name']}),
                    ('note', None),
                ))
            else:
                browser = Browser.objects.get(id=b['id'])
                browser_content = OrderedDict((
                    ('id', text_type(browser.id)),
                    ('slug', browser.slug),
                    ('name', browser.name),
                    ('note', browser.note or None),
                ))
            browsers[b['id']] = browser_content
            tab['browsers'].append(browser_content['id'])

        # Load Features (first column)
        for f in table['features']:
            if is_fake_id(f['id']):
                # Fake feature
                if f.get('canonical'):
                    fname = f['name']
                else:
                    fname = {'en': f['name']}
                feature_content = OrderedDict((
                    ('id', f['id']),
                    ('slug', f['slug']),
                    ('mdn_uri', None),
                    ('experimental', f.get('experimental', False)),
                    ('standardized', f.get('standardized', True)),
                    ('stable', f.get('stable', True)),
                    ('obsolete', f.get('obsolete', False)),
                    ('name', fname),
                    ('links', OrderedDict((
                        ('sections', []),
                        ('supports', []),
                        ('parent', text_type(fp.feature.id)),
                        ('children', []))))))
            else:
                feature = Feature.objects.get(id=f['id'])
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
                    ('id', text_type(f['id'])),
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
            features.setdefault(f['id'], feature_content)
            compat_table_supports.setdefault(f['id'], OrderedDict())

        # Load Versions
        for v in table['versions']:
            if is_fake_id(v['id']):
                # New Version
                version_content = OrderedDict((
                    ('id', v['id']),
                    ('version', v['version'] or None),
                    ('release_day', None),
                    ('retirement_day', None),
                    ('status', 'unknown'),
                    ('release_notes_uri', None),
                    ('note', None),
                    ('links', OrderedDict((
                        ('browser', text_type(v['browser'])),)))))
            else:
                # Existing Version
                version = Version.objects.get(id=v['id'])
                version_content = OrderedDict((
                    ('id', text_type(v['id'])),
                    ('version', version.version or None),
                    ('release_day', date_to_iso(version.release_day)),
                    ('retirement_day', date_to_iso(version.retirement_day)),
                    ('status', version.status),
                    ('release_notes_uri', version.release_notes_uri or None),
                    ('note', version.note or None),
                    ('order', version._order),
                    ('links', OrderedDict((
                        ('browser', text_type(version.browser_id)),)))))
            versions.setdefault(v['id'], version_content)

        # Load Supports
        for s in table['supports']:
            if is_fake_id(s['id']):
                # New support
                support_content = OrderedDict((
                    ('id', s['id']),
                    ('support', s['support']),
                    ('prefix', s.get('prefix')),
                    ('prefix_mandatory', bool(s.get('prefix', False))),
                    ('alternate_name', s.get('alternate_name')),
                    ('alternate_mandatory',
                     s.get('alternate_mandatory', False)),
                    ('requires_config', s.get('requires_config')),
                    ('default_config', s.get('default_config')),
                    ('protected', s.get('protected', False)),
                    ('note', s.get('note')),
                    ('footnote', None),
                    ('links', OrderedDict((
                        ('version', text_type(s['version'])),
                        ('feature', text_type(s['feature'])))))))
                if s.get('footnote'):
                    support_content['footnote'] = {'en': s['footnote']}
                version_id = s['version']
                feature_id = s['feature']
            else:
                # Existing support
                support = Support.objects.get(id=s['id'])
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
                    ('footnote', support.footnote or None),
                    ('links', OrderedDict((
                        ('version', text_type(support.version_id)),
                        ('feature', text_type(support.feature_id)))))))
                version_id = support.version_id
                feature_id = support.feature_id
            supports.setdefault(s['id'], support_content)
            if support_content['footnote']:
                footnotes[text_type(s['id'])] = len(footnotes) + 1

            # Set the meta lookup
            version = versions[version_id]
            browser_id = version['links']['browser']
            compat_table_supports[feature_id].setdefault(browser_id, [])
            compat_table_supports[feature_id][browser_id].append(
                text_type(s['id']))

        tabs.append(tab)

    # Add linked data, meta
    def sorted_values(d):
        int_keys = sorted([k for k in d.keys() if isinstance(k, int)])
        nonint_keys = sorted([k for k in d.keys() if not isinstance(k, int)])
        return list(d[k] for k in chain(int_keys, nonint_keys))

    fp_data['linked']['specifications'] = sorted_values(specifications)
    fp_data['linked']['maturities'] = sorted_values(maturities)
    fp_data['linked']['sections'] = sorted_values(sections)
    fp_data['linked']['browsers'] = sorted_values(browsers)
    fp_data['linked']['versions'] = sorted_values(versions)
    fp_data['linked']['features'] = sorted_values(features)
    fp_data['linked']['supports'] = sorted_values(supports)
    languages = fp_data['features']['mdn_uri'].keys()
    fp_data['meta']['compat_table']['languages'] = list(languages)
    fp_data['meta']['compat_table']['tabs'] = tabs
    fp_data['meta']['compat_table']['supports'] = compat_table_supports
    fp_data['meta']['compat_table']['footnotes'] = footnotes
    fp.data = fp_data

    # Add issues
    for err in chain(data['issues'], data['errors']):
        if isinstance(err, tuple):
            html = range_error_to_html(en_content.raw, *err)
            fp.add_error(html, True)
        else:
            fp.add_error(err)

    # Update status, issues
    fp.status = fp.STATUS_PARSED
    fp.save()


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


def range_error_to_html(page, start, end, reason, rule=None):
    """Convert a range error to HTML"""
    assert page, "Page can not be empty"
    html_bits = ["<div><p>", escape(reason), "</p>"]
    if rule:
        html_bits.extend(("<p><code>", escape(rule), "</code></p>"))

    # Get 2 lines of context around error
    html_bits.append('<p>Context:<pre>')
    start_line = page.count('\n', 0, start)
    end_line = page.count('\n', 0, end)
    ctx_start_line = max(0, start_line - 2)
    ctx_end_line = min(end_line + 3, page.count('\n'))
    digits = len(text_type(ctx_end_line))
    context_lines = page.split('\n')[ctx_start_line:ctx_end_line]

    # Highlight the errored portion
    err_page_bits = []
    err_line_count = 1
    assert page
    for p, c in enumerate(page):  # pragma: nocover - page always enumerates
        if c == '\n':
            err_page_bits.append(c)
            err_line_count += 1
            if err_line_count > ctx_end_line:
                break
        elif p < start or p >= end:
            err_page_bits.append(' ')
        else:
            err_page_bits.append('^')
    err_page = ''.join(err_page_bits)
    err_lines = err_page.split('\n')[ctx_start_line:ctx_end_line]

    for num, (line, err_line) in enumerate(zip(context_lines, err_lines)):
        lnum = ctx_start_line + num
        html_bits.append(
            text_type(lnum).rjust(digits) + ' ' + escape(line) + '\n')
        if '^' in err_line:
            html_bits.append('*' * digits + ' ' + err_line + '\n')

    html_bits.append("</pre></p></div>")
    return ''.join(html_bits)


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
