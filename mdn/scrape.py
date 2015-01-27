"""Parsing Expression Grammar for MDN pages."""
from __future__ import unicode_literals
from collections import OrderedDict
from itertools import chain
import string

from django.utils.html import escape
from django.utils.six import text_type
from parsimonious import IncompleteParseError, ParseError
from parsimonious.grammar import Grammar
from parsimonious.nodes import NodeVisitor

from webplatformcompat.models import Browser, Feature, Section, Specification


# Parsimonious grammar for an MDN page
page_grammar = r"""
doc = other_text other_section* spec_section? compat_section?
    other_section* last_section?

other_text = ~r".*?(?=<h2)"s
other_section = _ !(spec_h2 / compat_h2) other_h2 _ other_text
other_h2 = "<h2 " _ attrs? _ ">" _ bare_text _ "</h2>"
last_section = _ other_h2 _ ~r".*(?!=<h2)"s

spec_section = _ spec_h2 _ spec_table
spec_h2 = "<h2 " _ attrs? _ ">" _ "Specifications" _ "</h2>"
spec_table = "<table class=\"standard-table\">" _ spec_head _ spec_body
    _ "</table>" _

spec_head = "<thead>" _ "<tr>" _ th_elems _ "</tr>" _ "</thead>"
th_elems = th_elem+
th_elem = "<th scope=\"col\">" _ (!"</th>" bare_text) _ "</th>" _
old_th_elem = "<th scope=\"col\">" _ inside_th _ "</th>" _
inside_th = !"</th>" bare_text

spec_body = "<tbody>" _ spec_rows "</tbody>"
spec_rows = spec_row+
spec_row = "<tr>" _ specname_td _ spec2_td _ specdesc_td _ "</tr>" _
specname_td = "<td>" kuma_esc_start "SpecName" kuma_func_start qtext
    kuma_func_arg qtext kuma_func_arg qtext kuma_func_end kuma_esc_end
    "</td>"
spec2_td = "<td>" kuma_esc_start "Spec2" kuma_func_start qtext
    kuma_func_end kuma_esc_end "</td>"
specdesc_td = "<td>" _ inner_td _ "</td>"
inner_td = ~r"(?P<content>.*?(?=</td>))"s

compat_section = _ compat_h2 _ compat_kuma _ compat_divs compat_footnotes?
compat_h2 = "<h2 " _ attrs? _ ">" _ compat_title _ "</h2>"
compat_title = ~r"(?P<content>Browser [cC]ompat[ai]bility)"
compat_kuma = (compat_kuma_div / compat_kuma_p)
compat_kuma_div = "<div>" _ kuma_esc_start _ "CompatibilityTable" "()"? _
    kuma_esc_end _ "</div>"
compat_kuma_p = "<p>" _ kuma_esc_start _ "CompatibilityTable" "()"? _
    kuma_esc_end _ "</p>"
compat_divs = compat_div+
compat_div = "<div" _ "id" _ equals _ compat_div_id ">" _ compat_table
    _ "</div>" _
compat_div_id = qtext
compat_table = "<table class=\"compat-table\">" _ compat_body _ "</table>" _
compat_body = "<tbody>" _ compat_headers _ compat_rows* _ "</tbody>"
compat_headers = tr_open _ "<th>Feature</th>" _ compat_client_cells _ "</tr>" _
compat_client_cells = compat_client_cell*
compat_client_cell = th_open _ compat_client_name _ "</th>" _
compat_client_name = ~r"(?P<content>.*?(?=</th>))"s
compat_rows = compat_row* _
compat_row = tr_open _ compat_row_cells _ "</tr>" _
compat_row_cells = compat_row_cell+
compat_row_cell = td_open _ compat_cell _ "</td>" _
compat_cell = ~r"(?P<content>.*?(?=</td>))"s
compat_footnotes = ~r"(?P<content>.*?(?=<h2))"s

kuma_esc_start = _ "{{" _
kuma_func_start = "(" _
kuma_func_arg = _ "," _
kuma_func_end = _ ")" _
kuma_esc_end = _ "}}" _

tr_open = "<tr" _ opt_attrs ">"
th_open = "<th" _ opt_attrs ">"
td_open = "<td" _ opt_attrs ">"

attrs = attr+
opt_attrs = attr*
attr = _ ident _ equals _ qtext _
equals = "="
ident = ~r"(?P<content>[a-z][a-z0-9-:]*)"

text = (double_quoted_text / single_quoted_text / bare_text)
qtext = (double_quoted_text / single_quoted_text)
bare_text = ~r"(?P<content>[^<]*)"
double_quoted_text = ~r'"(?P<content>[^"]*)"'
single_quoted_text = ~r"'(?P<content>[^']*)'"

_ = ~r"[ \t\r\n]*"
"""


def end_of_line(text, pos):
    """Get the position of the end of the line from pos"""
    try:
        return text.index('\n', pos)
    except ValueError:
        return len(text)


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

    grammar = Grammar(page_grammar)
    try:
        page_parsed = grammar.parse(mdn_page)
    except IncompleteParseError as ipe:
        error = (
            ipe.pos, end_of_line(ipe.text, ipe.pos),
            'Unable to finish parsing MDN page, starting at this position.')
        data['errors'].append(error)
        return data
    except ParseError as pe:  # pragma: no cover - usually skips section
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


class PageVisitor(NodeVisitor):
    """Extract and validate data from a parsed Specification section."""

    browser_name_fixes = {
        'Firefox (Gecko)': 'Firefox',
        'Firefox Mobile (Gecko)': 'Firefox Mobile',
        'Safari (WebKit)': 'Safari',
        'Windows Phone': 'IE Mobile',
        'IE Phone': 'IE Mobile',
        'IE\xa0Phone': 'IE Mobile',
    }

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
        self._browser_ids = None
        self._feature_data = None

    @property
    def browser_ids(self):
        if not self._browser_ids:
            self._browser_ids = {}
            for browser in Browser.objects.all():
                self._browser_ids[browser.name[self.locale]] = browser.pk
        return self._browser_ids

    def feature_id_and_slug(self, name):
        """Get or create the feature ID and slug given a name."""
        # Initialize Feature IDs
        if not self._feature_data:
            self._feature_data = {}
            for feature in Feature.objects.filter(parent=self.feature):
                name = feature.name.get(self.locale, feature.name['en'])
                self._feature_data[name] = (feature.id, feature.slug)

        # Select the Feature ID and slug
        if name not in self._feature_data:
            feature_id = '_' + name
            attempt = 0
            feature_slug = None
            while not feature_slug:
                base_slug = self.feature.slug + '_' + name
                feature_slug = slugify(base_slug, suffix=attempt)
                if Feature.objects.filter(slug=feature_slug).exists():
                    attempt += 1
                    feature_slug = ''
            self._feature_data[name] = (feature_id, feature_slug)

        return self._feature_data[name]

    def generic_visit(self, node, visited_children):
        return visited_children or node

    def visit_doc(self, node, children):
        return {
            'specs': self.specs,
            'locale': self.locale,
            'issues': self.issues,
            'errors': self.errors,
            'compat': self.compat,
            'footnotes': self.footnotes,
        }

    visit_spec_section = visit_doc

    def visit_specname_td(self, node, children):
        key = children[4][0]
        subpath = children[6][0]
        name = children[8][0]
        assert isinstance(key, text_type), type(key)
        assert isinstance(subpath, text_type), type(subpath)
        assert isinstance(name, text_type), type(name)
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
        key = children[4][0]
        assert isinstance(key, text_type), type(key)
        return key

    def visit_specdesc_td(self, node, children):
        text = children[2]
        assert isinstance(text, text_type), type(text)
        return text

    def visit_spec_row(self, node, children):
        specname = children[2]
        assert isinstance(specname, tuple), type(specname)
        key, spec_id, path, name = specname

        spec2_key = children[4]
        assert isinstance(spec2_key, text_type), spec2_key
        assert spec2_key == key, (spec2_key, key)

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
            'section.note': desc,
            'section.id': section_id})

    def visit_attr(self, node, children):
        ident = children[1]
        value = children[5][0]

        assert isinstance(ident, text_type), type(ident)
        assert isinstance(value, text_type), type(value)

        return (ident, value)

    def visit_attrs(self, node, children):
        return children

    visit_opt_attrs = visit_attrs

    def visit_spec_h2(self, node, children):
        attrs_list = children[2][0]
        attrs = dict(attrs_list)
        h2_id = attrs.get('id')
        if h2_id != 'Specifications':
            self.issues.append(
                (node.start, node.end,
                 ('In Specifications section, expected <h2'
                  ' id="Specifications">, actual id="%s"' % h2_id)))

        h2_name = attrs.get('name')
        if h2_name is not None and h2_name != 'Specifications':
            self.issues.append(
                (node.start, node.end,
                 ('In Specifications section, expected <h2'
                  ' name="Specifications"> or no name attribute,'
                  ' actual name="%s"' % h2_name)))

    def visit_compat_section(self, node, children):
        compat_divs = children[5]
        compat_footnotes = children[6]

        assert isinstance(compat_divs, list), type(compat_divs)
        for div in compat_divs:
            assert isinstance(div, dict), type(div)
        self.compat = compat_divs
        self.footnotes = compat_footnotes[0].text or None

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
        versions = OrderedDict()
        features = OrderedDict()
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
        support_id = 0
        for row, compat_row in enumerate(compat_rows):
            for cell in compat_row['cells']:
                col = table[row].index(None)
                rowspan = int(cell.pop('rowspan', 1))
                colspan = int(cell.pop('colspan', 1))
                if col == 0:
                    # Insert as feature
                    name = cell['content']
                    cell_id, feature_slug = self.feature_id_and_slug(name)
                    feature = {
                        'name': name,
                        'id': cell_id,
                        'slug': feature_slug,
                        'experimental': False,
                        'standardized': True,
                        'stable': True,
                        'obsolete': False,
                    }
                    features[cell_id] = feature
                else:
                    # Insert as support
                    # support = {
                    #     'content': cell['content']
                    # }
                    cell_id = support_id
                    support_id += 1
                # Insert IDs into table
                for r in range(rowspan):
                    for c in range(colspan):
                        table[row + r][col + c] = cell_id

        return {
            'browsers': list(browsers.values()),
            'versions': list(versions.values()),
            'features': list(features.values()),
            'supports': list(supports.values())
        }

    def visit_compat_headers(self, node, children):
        compat_client_cells = children[4]
        assert isinstance(compat_client_cells, list), type(compat_client_cells)
        for cell in compat_client_cells:
            assert isinstance(cell, dict), type(cell)
        return compat_client_cells

    def visit_compat_client_cell(self, node, children):
        th_open = children[0]
        compat_client_name = children[2]
        assert isinstance(th_open, dict), type(th_open)
        assert isinstance(compat_client_name, dict), type(compat_client_name)
        client = compat_client_name.copy()
        client.update(th_open)
        return client

    def visit_compat_client_name(self, node, children):
        name = node.match.group('content')
        assert isinstance(name, text_type), type(name)

        fixed_name = self.browser_name_fixes.get(name, name)
        browser_id = self.browser_ids.get(fixed_name)
        if not browser_id:
            self.errors.append(
                (node.start, node.end, 'Unknown Browser "%s"' % name))
            browser_id = "_" + name

        return {
            'name': fixed_name,
            'id': browser_id,
        }

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
        for cell in compat_row_cells:
            assert isinstance(cell, dict), type(cell)
        row_dict = {
            'cells': compat_row_cells,
        }
        row_dict.update(tr_open)
        return row_dict

    def visit_compat_row_cell(self, node, children):
        td_open = children[0]
        compat_cell = children[2]

        assert isinstance(td_open, dict), type(td_open)
        assert isinstance(compat_cell, text_type), type(compat_cell)

        cell_dict = {
            'content': compat_cell,
        }
        cell_dict.update(td_open)
        return cell_dict

    def visit_generic_open(self, node, children, tag, expected):
        """Parse an opening tag with an expectd attributes list"""
        attrs = children[2]
        assert isinstance(attrs, list), type(attrs)
        for attr in attrs:
            assert len(attr) == 2, attr

        # Filter attributes
        attr_dict = {}
        for name, value in attrs:
            if name not in expected:
                self.issues.append((
                    node.start, node.end,
                    "Unexpected attribute <%s %s=\"%s\">" % (
                        tag, name, value)))
            else:
                attr_dict[name] = value
        return attr_dict

    def visit_td_open(self, node, children):
        expected = ('rowspan', 'colspan')
        return self.visit_generic_open(node, children, 'td', expected)

    def visit_th_open(self, node, children):
        expected = ('colspan',)
        return self.visit_generic_open(node, children, 'th', expected)

    def visit_tr_open(self, node, children):
        expected = []
        return self.visit_generic_open(node, children, 'tr', expected)

    def generic_visit_content(self, node, args):
        return node.match.group('content')

    visit_single_quoted_text = generic_visit_content
    visit_double_quoted_text = generic_visit_content
    visit_bare_text = generic_visit_content
    visit_ident = generic_visit_content
    visit_inner_td = generic_visit_content
    visit_compat_feature = generic_visit_content
    visit_compat_support = generic_visit_content
    visit_compat_cell = generic_visit_content


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
    digits = len(str(ctx_end_line))
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
        elif p < start or p > end:
            err_page_bits.append(' ')
        else:
            err_page_bits.append('^')
    err_page = ''.join(err_page_bits)
    err_lines = err_page.split('\n')[ctx_start_line:ctx_end_line]

    for num, (line, err_line) in enumerate(zip(context_lines, err_lines)):
        lnum = ctx_start_line + num
        html_bits.append(str(lnum).rjust(digits) + ' ' + escape(line) + '\n')
        if '^' in err_line:
            html_bits.append('*' * digits + ' ' + err_line + '\n')

    html_bits.append("</pre></p></div>")
    return ''.join(html_bits)


def scrape_feature_page(fp):
    """Scrape a FeaturePage object"""
    en_content = fp.translatedcontent_set.get(locale='en-US')
    fp_data = fp.reset_data()
    main_feature_id = str(fp.feature.id)
    data = scrape_page(en_content.raw, fp.feature)
    fp_data['meta']['scrape']['raw'] = data

    # Load specification section data
    specifications = OrderedDict()
    maturities = OrderedDict()
    sections = OrderedDict()
    for row in data['specs']:
        # Load Specifications and Maturity
        spec_id = row['specification.id']
        if spec_id:
            spec = Specification.objects.get(id=spec_id)
            section_ids = [
                str(s_id) for s_id in spec.sections.values_list(
                    'id', flat=True)]
            spec_content = OrderedDict((
                ('id', str(spec_id)),
                ('slug', spec.slug),
                ('mdn_key', spec.mdn_key),
                ('name', spec.name),
                ('uri', spec.uri),
                ('links', OrderedDict((
                    ('maturity', str(spec.maturity_id)),
                    ('sections', section_ids)
                )))))
            specifications[spec_id] = spec_content

            mat = spec.maturity
            spec_ids = [
                str(s_id) for s_id in mat.specifications.values_list(
                    'id', flat=True)]
            mat_content = OrderedDict((
                ('id', str(mat.id)),
                ('slug', mat.slug),
                ('name', mat.name),
                ('links', OrderedDict((
                    ('specifications', spec_ids),
                )))))
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
            mat['links']['specifications'].append(spec_id)
            maturities['_unknown'] = mat

        # Load Section
        section_id = row['section.id']
        if section_id:
            section = Section.objects.get(id=section_id)
            feature_ids = [
                str(f_id) for f_id in section.features.values_list(
                    'id', flat=True)]
            if main_feature_id not in feature_ids:
                feature_ids.append(main_feature_id)
            section_content = OrderedDict((
                ('id', str(section_id)),
                ('number', section.number),
                ('name', section.name),
                ('subpath', section.subpath),
                ('note', section.note),
                ('links', OrderedDict((
                    ('specification', spec_id),
                    ('features', feature_ids))))))
        else:
            section_id = str(spec_id) + '_' + row['section.subpath']
            section_content = OrderedDict((
                ('id', section_id),
                ('number', OrderedDict()),
                ('name', OrderedDict()),
                ('subpath', OrderedDict()),
                ('note', OrderedDict()),
                ('links', OrderedDict((
                    ('specification', spec_id),
                    ('features', [main_feature_id]))))))
        section_content['name']['en'] = row['section.name']
        section_content['subpath']['en'] = row['section.subpath']
        section_content['note']['en'] = row['section.note']
        sections[section_id] = section_content
        fp_data['features']['links']['sections'].append(str(section_id))

    tabs = []
    browsers = OrderedDict()
    versions = OrderedDict()
    features = OrderedDict()
    supports = OrderedDict()
    compat_table_supports = OrderedDict(((str(fp.feature.id), {}),))
    # Load compatibility section
    for table in data['compat']:
        tab = OrderedDict((
            ("name", {"en": table['name'].title()}),
            ("browsers", []),
        ))
        for b in table['browsers']:
            if str(b['id']).startswith('_'):
                browser_content = OrderedDict((
                    ('id', b['id']),
                    ('slug', ''),
                    ('name', {'en': b['name']}),
                    ('note', None),
                ))
            else:
                browser = Browser.objects.get(id=b['id'])
                browser_content = OrderedDict((
                    ('id', str(browser.id)),
                    ('slug', browser.slug),
                    ('name', browser.name),
                    ('note', browser.note),
                ))
            browsers[b['id']] = browser_content
            tab['browsers'].append(browser_content['id'])
        for f in table['features']:
            if str(f['id']).startswith('_'):
                # Fake feature
                feature_content = OrderedDict((
                    ('id', f['id']),
                    ('slug', f['slug']),
                    ('mdn_uri', None),
                    ('experimental', f['experimental']),
                    ('standardized', f['standardized']),
                    ('stable', f['stable']),
                    ('obsolete', f['obsolete']),
                    ('name', {'en': f['name']}),
                    ('links', OrderedDict((
                        ('sections', []),
                        ('supports', []),
                        ('parent', str(fp.feature.id)),
                        ('children', []))))))
            else:
                feature = Feature.objects.get(id=f['id'])
                section_ids = [
                    str(s_id) for s_id in
                    feature.sections.values_list('pk', flat=True)]
                support_ids = [
                    str(s_id) for s_id in
                    feature.supports.values_list('pk', flat=True)]
                parent_id = (
                    str(feature.parent_id) if feature.parent_id else None)
                children_ids = [
                    str(c_id) for c_id in
                    feature.children.values_list('pk', flat=True)]
                feature_content = OrderedDict((
                    ('id', str(f['id'])),
                    ('slug', feature.slug),
                    ('mdn_uri', feature.mdn_uri),
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
        tabs.append(tab)

    # Add linked data, meta
    fp_data['linked']['specifications'] = list(specifications.values())
    fp_data['linked']['maturities'] = list(maturities.values())
    fp_data['linked']['sections'] = list(sections.values())
    fp_data['linked']['browsers'] = list(browsers.values())
    fp_data['linked']['versions'] = list(versions.values())
    fp_data['linked']['features'] = list(features.values())
    fp_data['linked']['supports'] = list(supports.values())
    languages = fp_data['features']['mdn_uri'].keys()
    fp_data['meta']['compat_table']['languages'] = list(languages)
    fp_data['meta']['compat_table']['tabs'] = tabs
    fp_data['meta']['compat_table']['supports'] = compat_table_supports
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


def slugify(word, length=50, suffix=""):
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
    suffix = str(suffix) if suffix else ""
    with_suffix = slugged[slice(length - len(suffix))] + suffix
    return with_suffix
