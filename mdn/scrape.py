"""Parsing Expression Grammar for MDN pages."""
from __future__ import unicode_literals
from collections import OrderedDict
from itertools import chain

from django.utils.html import escape
from django.utils.six import text_type
from parsimonious import IncompleteParseError, ParseError
from parsimonious.grammar import Grammar
from parsimonious.nodes import NodeVisitor

from webplatformcompat.models import Section, Specification


# Parsimonious grammar for an MDN page
page_grammar = r"""
doc = other_text other_section* spec_section other_section* last_section?

other_text = ~r".*?(?=<h2)"s
other_section = _ !spec_h2 other_h2 _ other_text
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

kuma_esc_start = _ "{{" _
kuma_func_start = "(" _
kuma_func_arg = _ "," _
kuma_func_end = _ ")" _
kuma_esc_end = _ "}}" _

attrs = attr+
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


def scrape_page(mdn_page, locale='en'):
    data = {
        'specs': [],
        'locale': locale,
        'issues': [],
        'errors': [],
    }
    if '<h2' not in mdn_page:
        data['errors'].append('No <h2> found in page')
        return data

    grammar = Grammar(page_grammar)
    try:
        page_parsed = grammar.parse(mdn_page)
    except IncompleteParseError as ipe:  # pragma: no cover
        error = (
            ipe.pos, ipe.text.index('\n', ipe.pos),
            'Unable to finish parsing MDN page, starting at this position.')
        data['errors'].append(error)
        return data
    except ParseError as pe:
        rule = pe.expr
        error = (
            pe.pos, pe.text.index('\n', pe.pos),
            'Rule "%s" failed to match.  Rule definition:' % rule.name,
            rule.as_rule())
        data['errors'].append(error)
        return data
    page_data = PageVisitor().visit(page_parsed)

    data['specs'] = page_data.get('specs', [])
    data['issues'] = page_data.get('issues', [])
    data['errors'] = page_data.get('errors', [])
    return data


class PageVisitor(NodeVisitor):
    """Extract and validate data from a parsed Specification section."""

    def __init__(self, locale='en'):
        super(PageVisitor, self).__init__()
        self.locale = locale
        self.specs = []
        self.issues = []
        self.errors = []

    def generic_visit(self, node, visited_children):
        return visited_children or node

    def visit_doc(self, node, children):
        return {
            'specs': self.specs,
            'locale': self.locale,
            'issues': self.issues,
            'errors': self.errors,
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

    def visit_spec_h2(self, node, children):
        attrs_list = children[2][0]
        attrs = dict(attrs_list)
        h2_id = attrs.get('id')
        if h2_id != 'Specifications':
            self.issues.append(
                (node.start, node.end,
                 ('In Specifications section, expected <h3'
                  ' id="Specifications">, actual id="%s"' % h2_id)))

        h2_name = attrs.get('name')
        if h2_name is not None and h2_name != 'Specifications':
            self.issues.append(
                (node.start, node.end,
                 ('In Specifications section, expected <h3'
                  ' name="Specifications"> or no name attribute,'
                  ' actual name="%s"' % h2_name)))

    def generic_visit_content(self, node, args):
        return node.match.group('content')

    visit_single_quoted_text = generic_visit_content
    visit_double_quoted_text = generic_visit_content
    visit_bare_text = generic_visit_content
    visit_ident = generic_visit_content
    visit_inner_td = generic_visit_content


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
    for p, c in enumerate(page):  # pragma: nocover
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
    data = scrape_page(en_content.raw)
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

    # Add linked data
    fp_data['linked']['specifications'] = list(specifications.values())
    fp_data['linked']['maturities'] = list(maturities.values())
    fp_data['linked']['sections'] = list(sections.values())
    languages = fp_data['features']['mdn_uri'].keys()
    fp_data['meta']['compat_table']['languages'] = list(languages)
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
