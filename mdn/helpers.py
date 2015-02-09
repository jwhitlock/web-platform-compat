"""Helper functions for Jinja2 templates

This file is loaded by jingo and must be named helpers.py
"""

from jinja2 import contextfunction, Markup
from jingo import register

from .views import can_create, can_refresh


def page_list(page_obj):
    """Determine list of pages for pagination control.

    The goals are:
    - If less than 8 pages, show them all
    - Show three numbers around current page
    - Always have 7 entries (don't move click targets)
    Return is a list like [1, None, 5, 6, 7, None, 66].

    In separate function to facilitate unit testing.
    """
    paginator = page_obj.paginator
    current = page_obj.number
    end = paginator.num_pages
    if end <= 7:
        return paginator.page_range

    if current <= 4:
        pages = list(range(1, max(6, current + 2))) + [None, end]
    elif current >= (end - 3):
        pages = [1, None] + list(range(end - 4, end + 1))
    else:
        pages = [1, None] + list(range(current - 1, current + 2)) + [None, end]
    return pages


@register.function
@contextfunction
def pagination_control(context, page_obj, url):
    """Add a bootstrap-style pagination control.

    The basic pagination control is:
    << - previous page
    1, 2 - First two pages
    ... - Break
    n-1, n, n+1 - Current page and context
    total-1, total - End pages
    >> - Next page

    This breaks down when the current page is low or high, or the total
    number of pages is low.  So, done as a function.
    """
    if not page_obj.has_other_pages():
        return ""
    if page_obj.has_previous():
        prev_page = page_obj.previous_page_number()
        if prev_page == 1:
            prev_url = url
        else:
            prev_url = url + '?page=%d' % prev_page
        previous_nav = (
            '<li><a href="{prev_url}" aria-label="Previous">'
            '<span aria-hidden="true">&laquo;</span></a></li>'
        ).format(prev_url=prev_url)
    else:
        previous_nav = (
            '<li class="disabled"><span aria-hidden="true">&laquo;</span>'
            '</li>')

    pages = page_list(page_obj)
    page_navs = []
    current = page_obj.number
    for page in pages:
        if page is None:
            page_navs.append(
                '<li class="disabled"><span aria-hidden="true">&hellip;</span>'
                '</li>')
            continue
        if page == current:
            active = ' class="active"'
        else:
            active = ''
        if page == 1:
            page_query = ''
        else:
            page_query = "?page=%d" % page
        page_navs.append(
            '<li{active}><a href="{url}{page_query}">'
            '{page}</a></li>'.format(
                active=active, url=url, page_query=page_query, page=page))
    page_nav = "\n    ".join(page_navs)

    if page_obj.has_next():
        next_nav = """<li>
      <a href="{url}?page={page}" aria-label="Next">
        <span aria-hidden="true">&raquo;</span>
      </a>
    </li>""".format(url=url, page=page_obj.next_page_number())
    else:
        next_nav = """\
    <li class="disabled"><span aria-hidden="true">&raquo;</span></li>"""

    return Markup("""\
<nav>
  <ul class="pagination">
    {previous_nav}
    {page_nav}
    {next_nav}
  </ul>
</nav>
""".format(previous_nav=previous_nav, page_nav=page_nav, next_nav=next_nav))


@register.function
@contextfunction
def can_create_mdn_import(context, user):
    return can_create(user)


@register.function
@contextfunction
def can_refresh_mdn_import(context, user):
    return can_refresh(user)


@register.function
@contextfunction
def can_reparse_mdn_import(context, user):
    return can_create(user)
