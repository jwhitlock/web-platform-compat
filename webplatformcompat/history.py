# -*- coding: utf-8 -*-
"""Extensions of simplehistory for webplatformcompat"""

from __future__ import unicode_literals
from json import dumps

from django.conf import settings
from django.db import models
from django.http import HttpResponseBadRequest
from django.utils.timezone import now

from simple_history.middleware import (
    HistoryRequestMiddleware as BaseHistoryRequestMiddleware)
from simple_history.models import HistoricalRecords as BaseHistoricalRecords


user_model = getattr(settings, 'AUTH_USER_MODEL', 'auth.User')


def register(
        model, app=None, manager_name='history', records_class=None,
        **records_config):
    """
    Create historical model for `model` and attach history manager to `model`.

    Variant of simple_history.register that allows override of records class
    """
    from simple_history import models
    if model._meta.db_table not in models.registered_models:
        records_class = records_class or HistoricalRecords
        records = records_class(**records_config)
        records.manager_name = manager_name
        records.module = app and ("%s.models" % app) or model.__module__
        records.add_extra_methods(model)
        records.finalize(model)
        models.registered_models[model._meta.db_table] = model
    else:
        pass  # pragma: nocover


class Changeset(models.Model):
    """Changeset combining historical records"""

    TARGET_RESOURCES = [
        'browsers', 'features', 'maturities', 'sections', 'specifications',
        'supports', 'versions',
    ]

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(user_model, related_name="changesets")
    closed = models.BooleanField(
        help_text="Is the changeset closed to new changes?",
        default=False)
    target_resource_type = models.CharField(
        help_text="Type of target resource",
        max_length=12, blank=True, choices=[(r, r) for r in TARGET_RESOURCES])
    target_resource_id = models.PositiveIntegerField(
        default=0, help_text="ID of target resource")

    def save(self, update_cache=True, *args, **kwargs):
        """Refresh cache of the items updated in changeset"""
        super(Changeset, self).save(*args, **kwargs)
        if self.closed and update_cache:
            from .tasks import update_cache_for_instance
            for relation in self._meta.get_all_related_objects():
                related = getattr(self, relation.get_accessor_name())
                type_name = related.model.instance_type.__name__
                ids = related.values_list('id', flat=True)
                for i in ids:
                    update_cache_for_instance.delay(type_name, i)


class HistoricalRecords(BaseHistoricalRecords):
    """simplehistory.HistoricalRecords with modifications

    Can easily add additional fields
    References a history_changeset instead of a history_user
    """
    additional_fields = {}

    def copy_fields(self, model):
        """Add additional_fields to the historic model"""
        fields = super(HistoricalRecords, self).copy_fields(model)
        for name, field in self.additional_fields.items():
            assert name not in fields
            assert hasattr(self, 'get_%s_value' % name)
            fields[name] = field
        return fields

    def get_extra_fields(self, model, fields):
        """Remove fields moved to changeset"""
        extra_fields = super(HistoricalRecords, self).get_extra_fields(
            model, fields)
        related_name = 'historical_' + model._meta.verbose_name_plural.lower()
        extra_fields['history_changeset'] = models.ForeignKey(
            'Changeset', related_name=related_name)
        return extra_fields

    def get_history_changeset(self, instance):
        """Get the changeset from the instance or middleware"""
        try:
            changeset = instance._history_changeset
        except AttributeError:
            changeset = self.thread.request.changeset
        user = self.get_history_user(instance)
        assert user, 'History User is required'
        if not changeset.user_id:
            changeset.user = user
        else:
            # These should be verified in the middleware before the instance
            # is saved, but let's be sure
            assert user == changeset.user, 'User must match changeset user'
            assert not changeset.closed, 'Changeset is closed'
        return changeset

    def create_historical_record(self, instance, history_type):
        """Create the historical record and associated objects

        Add data from additional_fields
        Change history_user to history_changeset
        """
        history_date = getattr(instance, '_history_date', now())
        history_changeset = self.get_history_changeset(instance)
        manager = getattr(instance, self.manager_name)
        attrs = {}
        for field in instance._meta.fields:
            attrs[field.attname] = getattr(instance, field.attname)

        for field_name in self.additional_fields:
            loader = getattr(self, 'get_%s_value' % field_name)
            value = loader(instance, type)
            attrs[field_name] = value

        if not history_changeset.id:
            history_changeset.closed = True
            update_cache = self.thread.request.delay_cache
            history_changeset.save(update_cache=update_cache)
        else:
            update_cache = False
        manager.create(
            history_date=history_date, history_type=history_type,
            history_changeset=history_changeset, **attrs)


class HistoryChangesetRequestMiddleware(BaseHistoryRequestMiddleware):
    """Add a changeset to the HistoricalRecords request"""
    def process_request(self, request):
        super(HistoryChangesetRequestMiddleware, self).process_request(request)
        if request.META.get('REQUEST_METHOD') in ('GET', 'HEAD'):
            return
        changeset_id = request.GET.get('changeset')
        if changeset_id:
            changeset = Changeset.objects.get(id=changeset_id)
            if changeset.user != request.user:
                message = (
                    'Changeset %s has a different user.' % changeset_id)
                return self.bad_request(request, message)
            if changeset.closed:
                message = 'Changeset %s is closed.' % changeset_id
                return self.bad_request(request, message)
            request.changeset = changeset
            request.delay_cache = True
        else:
            request.changeset = Changeset()
            request.delay_cache = False

    def bad_request(self, request, message):
        if request.META.get('CONTENT_TYPE') == 'application/vnd.api+json':
            content = {'errors': {'changeset': message}}
            return HttpResponseBadRequest(
                dumps(content), content_type='application/vnd.api+json')
        else:
            return HttpResponseBadRequest(message)
