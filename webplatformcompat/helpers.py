"""Helper functions for Jinja2 templates

This file is loaded by jingo and must be named helper.py
"""

from datetime import date

from django.contrib.staticfiles.templatetags.staticfiles import static
from django.utils.html import escape

from allauth.account.utils import user_display
from allauth.socialaccount import providers
from jinja2 import contextfunction, Markup
from jingo import register


def pick_translation(context, trans_obj):
    """Pick a translation from a translation object.

    A translation object may be:
    Empty -- No content, return ('', None)
    A string -- A canonical string, return (string, None)
    A dictionary -- Language/string pairs, return (string, language)
    """
    if not trans_obj:
        return '', None
    if not hasattr(trans_obj, 'keys'):
        return trans_obj, None
    lang = context.get('lang', 'en')
    if lang not in trans_obj:
        assert 'en' in trans_obj
        lang = 'en'
    return trans_obj[lang], lang


@register.function
@contextfunction
def trans_span(context, trans_obj, **attrs):
    """Pick a translation for an HTML element.

    The text is HTML-escaped and marked HTML-safe.  If the requested language
    does not match, the result is wrapped in a <span> with a lang= attribute.
    Other key=value pairs are added as span attributes.  If the requested
    language matches, and there are no span attributes, the <span> element is
    omitted and plain (HTML-safe) text is returned.
    """
    desired_lang = context.get('lang', 'en')
    trans, lang = pick_translation(context, trans_obj)
    if not lang:
        if trans:
            return Markup(u'<code>{0}</code>'.format(escape(trans)))
        else:
            return ''
    if desired_lang != lang:
        attrs['lang'] = lang
    if attrs:
        attrstr = ' '.join(
            ['{0}="{1}"'.format(k, attrs[k]) for k in sorted(attrs.keys())])
        return Markup(u'<span {1}>{0}</span>'.format(trans, attrstr))
    else:
        return Markup(trans)


@register.function
@contextfunction
def trans_str(context, trans_obj):
    """Pick a translation as an unescaped string.

    The string is not wrapped in an HTML element and not marked as HTML safe.
    """
    return pick_translation(context, trans_obj)[0]


@register.function
def current_year():
    return date.today().year


@register.function
@contextfunction
def providers_media_js(context):
    """Get a list of socialaccount providers.

    Jingo version of providers_media_js from
    allauth/socialaccount/templatetags/socialaccount.py
    """
    request = context['request']
    ret = '\n'.join(
        [p.media_js(request) for p in providers.registry.get_list()])
    return ret


@register.function
def provider_login_url(
        request, provider_id, process, scope=None, auth_params=None,
        next=None):
    """Get the login URL for a socialaccount provider.

    Jingo version of provider_login_url from
    allauth/socialaccount/templatetags/socialaccount.py
    """
    provider = providers.registry.by_id(provider_id)
    query = {'process': process}
    if scope:
        query['scope'] = scope
    if auth_params:
        query['auth_params'] = auth_params
    if next:
        query['next'] = next
    else:
        next = request.POST.get('next') or request.GET.get('next')
        if next:
            query['next'] = next
        elif process == 'redirect':
            query['next'] = request.get_full_path()

    # get the login url and append query as url parameters
    return provider.get_login_url(request, **query)


register.function(static)
register.function(user_display)
