"""Views for MDN migration app."""
from collections import Counter

from django import forms
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, JsonResponse
from django.utils.six.moves.urllib.parse import urlparse, urlunparse
from django.views.generic import DetailView, ListView, TemplateView
from django.views.generic.base import TemplateResponseMixin, View
from django.views.generic.detail import BaseDetailView
from django.views.generic.edit import CreateView, FormMixin, UpdateView

from .models import FeaturePage, Issue, ISSUES, SEVERITIES, validate_mdn_url
from .tasks import start_crawl, parse_page

DEV_PREFIX = 'https://developer.mozilla.org/en-US/docs/'


def can_create(user):
    return user.has_perm('mdn.add_featurepage')


def can_refresh(user):
    return True


class FeaturePageListView(ListView):
    model = FeaturePage
    template_name = "mdn/feature_page_list.jinja2"
    paginate_by = 50

    def get_queryset(self):
        qs = FeaturePage.objects.order_by('url')
        topic = self.request.GET.get('topic')
        if topic:
            qs = qs.filter(url__startswith=DEV_PREFIX + topic)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super(FeaturePageListView, self).get_context_data(**kwargs)
        ctx['request'] = self.request
        ctx['topic'] = self.request.GET.get('topic')
        ctx['topics'] = sorted((
            'Web/API',
            'Web/Accessibility',
            'Web/CSS',
            'Web/Events',
            'Web/Guide',
            'Web/HTML',
            'Web/JavaScript',
            'Web/MathML',
            'Web/SVG',
            'Web/XPath',
            'Web/XSLT',
        ))
        return ctx


class FeaturePageCreateView(CreateView):
    model = FeaturePage
    template_name = "mdn/feature_page_form.jinja2"
    fields = ['url', 'feature']

    def get_initial(self):
        initial = self.initial.copy()
        url = self.request.GET.get('url')
        if url:
            initial['url'] = url
        return initial

    def form_valid(self, form):
        """Start the parsing process on submission."""
        redirect = super(FeaturePageCreateView, self).form_valid(form)
        assert self.object and self.object.id
        self.object.reset()
        start_crawl.delay(self.object.id)
        return redirect


class FeaturePageDetailView(DetailView):
    model = FeaturePage
    template_name = "mdn/feature_page_detail.jinja2"

    def get_context_data(self, **kwargs):
        ctx = super(FeaturePageDetailView, self).get_context_data(**kwargs)
        ctx['request'] = self.request
        return ctx


class FeaturePageJSONView(BaseDetailView):
    model = FeaturePage

    def render_to_response(self, context):
        obj = context['object']
        return JsonResponse(obj.data)


class SearchForm(forms.Form):
    url = forms.URLField(
        label='MDN URL',
        widget=forms.URLInput(attrs={'placeholder': DEV_PREFIX + '...'}))

    def clean_url(self):
        data = self.cleaned_data['url']
        scheme, netloc, path, params, query, fragment = urlparse(data)
        cleaned = urlunparse((scheme, netloc, path, '', '', ''))
        validate_mdn_url(cleaned)
        return cleaned


class FeaturePageSearch(TemplateResponseMixin, View, FormMixin):
    """Search for a MDN URI via GET"""
    form_class = SearchForm
    template_name = "mdn/feature_page_form.jinja2"

    def get_form_kwargs(self):
        kwargs = super(FeaturePageSearch, self).get_form_kwargs()
        kwargs.setdefault('data', {}).update(self.request.GET.dict())
        return kwargs

    def get(self, request, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        ctx = super(FeaturePageSearch, self).get_context_data(**kwargs)
        ctx['action'] = "Search by URL"
        ctx['action_url'] = reverse('feature_page_search')
        ctx['method'] = 'get'
        return ctx

    def form_valid(self, form):
        url = form.cleaned_data['url']
        next_url = None

        # Try loading a specific page
        try:
            fp = FeaturePage.objects.get(url=url)
        except FeaturePage.DoesNotExist:
            pass
        else:
            next_url = reverse('feature_page_detail', kwargs={'pk': fp.pk})

        # Try filtering by a subset of pages
        if (not next_url) and (url.startswith(DEV_PREFIX)):
            suburl = url
            while suburl.endswith('/'):
                suburl = suburl[:-1]
            fp_start = FeaturePage.objects.filter(url__startswith=suburl)
            if fp_start.exists():
                topic = suburl.replace(DEV_PREFIX, '', 1)
                next_url = reverse('feature_page_list')
                next_url += '?topic={}'.format(topic)

        # Page does not exist
        if not next_url:
            msg = 'URL "%s" has not been scraped.' % url
            if can_create(self.request.user):
                msg += ' Scrape it?'
                messages.add_message(self.request, messages.INFO, msg)
                next_url = reverse('feature_page_create') + '?url=' + url
            else:
                messages.add_message(self.request, messages.INFO, msg)
                next_url = reverse('feature_page_list')

        return HttpResponseRedirect(next_url)


class FeaturePageReParse(UpdateView):
    model = FeaturePage
    fields = []
    template_name = "mdn/feature_page_form.jinja2"

    def get_context_data(self, **kwargs):
        ctx = super(FeaturePageReParse, self).get_context_data(**kwargs)
        pk = ctx['object'].pk
        ctx['action'] = "Re-parse MDN Page"
        ctx['action_url'] = reverse(
            'feature_page_reparse', kwargs={'pk': pk})
        ctx['back_url'] = reverse(
            'feature_page_detail', kwargs={'pk': pk})
        ctx['back'] = "Back to Details"
        return ctx

    def form_valid(self, form):
        """Start reparsing the page on submission."""
        redirect = super(FeaturePageReParse, self).form_valid(form)
        assert self.object and self.object.id
        self.object.status = FeaturePage.STATUS_PARSING
        self.object.reset_data()
        self.object.save()
        messages.add_message(
            self.request, messages.INFO, "Re-parsed the page.")
        parse_page.delay(self.object.id)
        return redirect


class FeaturePageReset(UpdateView):
    model = FeaturePage
    fields = []
    template_name = "mdn/feature_page_form.jinja2"

    def get_context_data(self, **kwargs):
        ctx = super(FeaturePageReset, self).get_context_data(**kwargs)
        pk = ctx['object'].pk
        ctx['action'] = "Reset MDN Page"
        ctx['action_url'] = reverse(
            'feature_page_reset', kwargs={'pk': pk})
        ctx['back_url'] = reverse(
            'feature_page_detail', kwargs={'pk': pk})
        ctx['back'] = "Back to Details"
        return ctx

    def form_valid(self, form):
        """Start refetching the page on submission."""
        redirect = super(FeaturePageReset, self).form_valid(form)
        assert self.object and self.object.id
        self.object.reset()
        messages.add_message(
            self.request, messages.INFO,
            "Resetting cached MDN pages, re-parsing.")
        start_crawl.delay(self.object.id)
        return redirect


class IssuesSummary(TemplateView):
    template_name = "mdn/issues_summary.jinja2"

    def get_context_data(self, **kwargs):
        ctx = super(IssuesSummary, self).get_context_data(**kwargs)
        issues = []
        for slug, (severity_num, brief, lengthy) in ISSUES.items():
            severity = SEVERITIES[severity_num]
            target = Issue.objects.filter(slug=slug)
            count = target.count()
            raw = target.values_list('page__url', 'page_id')
            examples = sorted(set(
                (url.replace(DEV_PREFIX, '', 1), pid) for url, pid in raw))
            issues.append((count, slug, severity, brief, examples[:5]))
        issues.sort(reverse=True)
        ctx['total_issues'] = Issue.objects.count()
        ctx['issues'] = issues
        return ctx


class IssuesDetail(TemplateView):
    template_name = "mdn/issues_detail.jinja2"

    def get_context_data(self, **kwargs):
        ctx = super(IssuesDetail, self).get_context_data(**kwargs)
        slug = self.kwargs['slug']
        issues = Issue.objects.filter(slug=slug)
        if issues.exists():
            ctx['sample_issue'] = issues.first()
            ctx['count'] = issues.count()
            pages = Counter()
            for url, pid in issues.values_list('page__url', 'page_id'):
                key = (url.replace(DEV_PREFIX, '', 1), pid)
                pages[key] += 1
            ctx['pages'] = pages
        else:
            ctx['sample_issue'] = None
            ctx['count'] = 0
            ctx['pages'] = {}
        ctx['slug'] = slug
        return ctx


feature_page_create = user_passes_test(can_create)(
    FeaturePageCreateView.as_view())
feature_page_detail = FeaturePageDetailView.as_view()
feature_page_json = FeaturePageJSONView.as_view()
feature_page_search = FeaturePageSearch.as_view()
feature_page_list = FeaturePageListView.as_view()
feature_page_reset = user_passes_test(can_refresh)(
    FeaturePageReset.as_view())
feature_page_reparse = user_passes_test(can_refresh)(
    FeaturePageReParse.as_view())
issues_summary = IssuesSummary.as_view()
issues_detail = IssuesDetail.as_view()
