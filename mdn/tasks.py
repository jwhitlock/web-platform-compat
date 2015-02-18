"""Asyncronous tasks for MDN scraping."""

from json import dumps
from traceback import format_exc

from celery import shared_task
import requests

from .models import FeaturePage, TranslatedContent
from .scrape import scrape_feature_page


@shared_task(ignore_result=True)
def start_crawl(featurepage_id):
    """Start the calling process for an MDN page."""
    fp = FeaturePage.objects.get(id=featurepage_id)
    assert fp.status == fp.STATUS_STARTING, fp.status
    meta = fp.meta()

    # Determine next state / task
    next_task = lambda: None
    if meta.status == meta.STATUS_STARTING:
        fp.status = fp.STATUS_META
        next_task = lambda: fetch_meta.delay(fp.id)
    elif meta.status == meta.STATUS_FETCHING:
        fp.status = fp.STATUS_META
    elif meta.status == meta.STATUS_FETCHED:
        fp.status = fp.STATUS_PAGES
        next_task = lambda: fetch_all_translations.delay(fp.id)
    else:
        assert meta.status == meta.STATUS_ERROR, meta.status
        fp.status = fp.STATUS_ERROR
        fp.add_error("Failed to download %s: %s" % (meta.url(), meta.raw))
    fp.save()
    next_task()


@shared_task(ignore_result=True)
def fetch_meta(featurepage_id):
    """Fetch metadata for an MDN page."""
    fp = FeaturePage.objects.get(id=featurepage_id)
    assert fp.status == fp.STATUS_META, fp.status
    meta = fp.meta()
    assert meta.status == meta.STATUS_STARTING, meta.status

    # Avoid double fetching
    meta.status = meta.STATUS_FETCHING
    meta.save(update_fields=['status'])

    # Request and validate the metadata
    url = meta.url()
    r = requests.get(url)
    if r.status_code != requests.codes.ok:
        meta.raw = "Status %d, Content:\n%s" % (r.status_code, r.text)
        meta.status = meta.STATUS_ERROR
        next_task = r.raise_for_status
    else:
        try:
            meta.raw = dumps(r.json())
        except ValueError:
            meta.raw = "Response is not JSON:\n" + r.text
            meta.status = meta.STATUS_ERROR
            next_task = r.json
        else:
            meta.status = meta.STATUS_FETCHED
    meta.save()

    # Determine next state / task
    if meta.status == meta.STATUS_ERROR:
        fp.status = fp.STATUS_ERROR
        fp.add_error("Failed to download %s: %s" % (url, meta.raw))
    else:
        assert meta.status == meta.STATUS_FETCHED, meta.status
        fp.status = fp.STATUS_PAGES
        next_task = lambda: fetch_all_translations.delay(fp.id)
    fp.save()
    next_task()


@shared_task(ignore_result=True)
def fetch_all_translations(featurepage_id):
    """Fetch all translations for an MDN page."""
    fp = FeaturePage.objects.get(id=featurepage_id)
    assert fp.status == fp.STATUS_PAGES, fp.status
    translations = fp.translations()
    assert translations, translations

    # Gather / count by status
    to_fetch = []
    fetching = 0
    errored = 0
    for t in translations:
        if t.status == t.STATUS_STARTING:
            to_fetch.append(t)
        elif t.status == t.STATUS_FETCHING:
            fetching += 1
        elif t.status == t.STATUS_ERROR:
            fp.add_error("Failed to download %s: %s" % (t.url(), t.raw))
            errored += 1
        else:
            assert t.status == t.STATUS_FETCHED, t.status

    # Determine next status / task
    if errored:
        fp.status = fp.STATUS_ERROR
        fp.save()
    elif (not fetching) and (not to_fetch):
        fp.status = fp.STATUS_PARSING
        fp.save()
        parse_page.delay(fp.id)
    elif to_fetch:
        for t in to_fetch:
            fetch_translation.delay(fp.id, t.locale)


@shared_task(ignore_result=True)
def fetch_translation(featurepage_id, locale):
    """Fetch a translations for an MDN page."""
    fp = FeaturePage.objects.get(id=featurepage_id)
    if fp.status in (fp.STATUS_PARSING, fp.STATUS_PARSED):
        # Already fetched
        t = TranslatedContent.objects.get(page=fp, locale=locale)
        assert t.status == t.STATUS_FETCHED, t.status
        return
    assert fp.status == fp.STATUS_PAGES, fp.status
    t = TranslatedContent.objects.get(page=fp, locale=locale)
    assert t.status == t.STATUS_STARTING, t.status

    # Avoid double fetching
    t.status = t.STATUS_FETCHING
    t.save(update_fields=['status'])

    # Request the translation
    r = requests.get(t.url() + "?raw")
    t.raw = r.text
    if r.status_code != requests.codes.ok:
        t.status = t.STATUS_ERROR
        t.raw = "Status %d, Content:\n%s" % (r.status_code, r.text)
        next_task = r.raise_for_status
    else:
        t.status = t.STATUS_FETCHED
        next_task = lambda: fetch_all_translations.delay(fp.id)
    t.save()

    # Determine next state / task
    if t.status == t.STATUS_ERROR:
        fp.status = fp.STATUS_ERROR
        fp.add_error("Failed to download %s: %s" % (t.url(), t.raw))
        fp.save()
    next_task()


@shared_task(ignore_result=True)
def parse_page(featurepage_id):
    fp = FeaturePage.objects.get(id=featurepage_id)
    assert fp.status == fp.STATUS_PARSING, fp.status
    try:
        scrape_feature_page(fp)
    except:
        # Unexpected exceptions are added and re-raised
        # Expected exceptions are handled by scrape_feature_page
        fp.status = FeaturePage.STATUS_ERROR
        fp.add_error(format_exc())
        fp.save()
        raise
