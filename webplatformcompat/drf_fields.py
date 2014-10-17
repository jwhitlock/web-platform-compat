# -*- coding: utf-8 -*-
"""
Fields for Django REST Framework serializers
"""
from __future__ import unicode_literals

import json

from django.core.exceptions import ValidationError
from django.forms import Textarea
from django.utils import six
from rest_framework.serializers import CharField, PrimaryKeyRelatedField

from .validators import LanguageDictValidator


class CurrentHistoryField(PrimaryKeyRelatedField):
    """Field is the current history object

    To use this field, initialize the manager to the name of the
    HistoricalRecords object (defaults to 'history')
    """

    def __init__(self, *args, **kwargs):
        self.manager = kwargs.pop('manager', 'history')
        required = kwargs.pop('required', False)
        assert not required, 'required must be False'
        self.view_name = kwargs.pop('view_name', '')
        super(CurrentHistoryField, self).__init__(
            required=required, *args, **kwargs)

    def initialize(self, parent, field_name):
        """Initialize field

        history_current only makes sense in the context of an object.
        However, some views, such as the browsable API, might try to access
        the queryset outside of an object context.  We initialize the
        queryset to the none() queryset, so certain operations (such as
        determining the model or calling all()) will return expected data.
        """
        self.full_queryset = getattr(parent.opts.model, self.manager)
        self.queryset = self.full_queryset
        super(CurrentHistoryField, self).initialize(parent, field_name)

    def field_to_native(self, obj, field_name):
        """Convert to the ID of the current history

        With a valid object, the queryset can be set to the proper history for
        this object.  In some views, such as the browsable API for the list,
        the object is not set, so we leave it as the none() queryset set in
        initialize.
        """
        if obj is None:  # pragma: no cover
            # From Browsable API renderer, for example after a DELETE:
            # self.get_raw_data_form(view, 'POST', request)
            return None
        self.queryset = getattr(obj, self.manager)
        most_recent_id = self.queryset.values_list('history_id', flat=True)[0]
        return self.to_native(most_recent_id)


class HistoricalObjectField(PrimaryKeyRelatedField):
    """Field is the ID of the historical object"""

    def __init__(self, *args, **kwargs):
        source = kwargs.pop('source', 'history_object')
        assert source == 'history_object'
        read_only = kwargs.pop('read_only', True)
        assert read_only, 'read_only must be True'
        super(HistoricalObjectField, self).__init__(
            source=source, read_only=read_only, *args, **kwargs)

    def field_to_native(self, obj, field_name):
        """Convert to the primary key of the history object

        With a valid object, the queryset can be set to the proper model for
        this object.
        """
        self.queryset = type(obj.history_object)._default_manager
        return super(HistoricalObjectField, self).field_to_native(
            obj, field_name).pk


class HistoryField(PrimaryKeyRelatedField):
    """Field is the history manager

    To use this field, initialize 'source' to the name of the
    HistoricalRecords object (defaults to 'history')
    """

    def __init__(self, *args, **kwargs):
        many = kwargs.pop('many', True)
        assert many, 'many must be True'
        read_only = kwargs.pop('read_only', True)
        assert read_only, 'read_only must be True'
        self.view_name = kwargs.pop('view_name', '')
        super(HistoryField, self).__init__(
            many=many, read_only=read_only, *args, **kwargs)

    def initialize(self, parent, field_name):
        """Initialize field

        history only makes sense in the context of an object.  However, some
        views, such as the browsable API, might try to access the queryset
        outside of an object context.  We initialize the queryset to the none()
        queryset, so certain operations (such as determining the model or
        calling all()) will return expected data.
        """
        manager = getattr(parent.opts.model, self.source or field_name)
        self.full_queryset = manager
        self.queryset = manager.none()
        super(HistoryField, self).initialize(parent, field_name)

    def field_to_native(self, obj, field_name):
        """Convert a field to the native represenation

        With a valid object, the queryset can be set to the object's
        queryset, which may be more limited than the generic queryset.
        """
        assert obj
        self.queryset = getattr(obj, self.source or field_name)
        return super(HistoryField, self).field_to_native(obj, field_name)


class MPTTRelationField(PrimaryKeyRelatedField):
    """Field is a property returning an MPTT related queryset

    Used against a property, such as:

    class MyModel(MPTTModel):
        parent = TreeForeignKey(
            'self', null=True, blank=True, related_name='children')

        @property
        def ancestors(self):
            return self.get_ancestors(include_self=True)

    ancestors = MPTTRelationField(many=True, source="ancestors")
    """

    def __init__(self, *args, **kwargs):
        self.relation = kwargs.pop('source', None)
        read_only = kwargs.pop('read_only', True)
        assert read_only, 'read_only must be True'
        super(MPTTRelationField, self).__init__(
            read_only=read_only, *args, **kwargs)

    def field_to_native(self, obj, field_name):
        """Convert a field to the native represenation

        With a valid object, the queryset can be set to the related object's
        queryset, which may be more limited than the generic queryset.
        """
        assert obj
        self.queryset = getattr(obj, self.relation)
        return super(MPTTRelationField, self).field_to_native(obj, field_name)


class OptionalCharField(CharField):
    """Field is a CharField that serializes as None when omitted"""
    def to_native(self, value):
        if value:
            return value
        else:
            return None

    def from_native(self, value):
        if value:
            return value
        else:
            return ''


class TranslatedTextField(CharField):
    """Field is a dictionary of language codes to text

    If allow_canonical=True (default False), then a non-linguistic string is
    allowed, such as an HTML attribute like "<input>".  This is stored in the
    backend as the dictionary {"zxx": "<input>"}, so that is allowed as an
    alternate represenation.

    If blank=True, then empty strings and other falsy values are allowed, and
    are serialized as null.
    """
    def __init__(self, *args, **kwargs):
        self.allow_canonical = kwargs.pop('allow_canonical', False)
        widget = kwargs.pop('widget', Textarea)
        validators = kwargs.pop(
            'validators',
            [LanguageDictValidator(allow_canonical=self.allow_canonical)])
        super(TranslatedTextField, self).__init__(
            widget=widget, validators=validators, *args, **kwargs)

    def to_native(self, value):
        '''Convert from model Python to serializable data'''
        if value:
            if list(value.keys()) == ['zxx']:
                if self.allow_canonical:
                    return value['zxx']
                else:
                    return None
            else:
                return value
        else:
            return None

    def from_native(self, value):
        '''Convert from serializable data to model'''
        if isinstance(value, dict):
            return value
        value = value.strip()
        if value:
            try:
                native = json.loads(value)
            except ValueError as e:
                if self.allow_canonical:
                    native = str(value)
                else:
                    raise ValidationError(str(e))
            if isinstance(native, six.string_types) and self.allow_canonical:
                return {'zxx': native}
            else:
                return native
        else:
            return None
