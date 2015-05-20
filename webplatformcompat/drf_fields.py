# -*- coding: utf-8 -*-
"""Fields for Django REST Framework serializers."""
from __future__ import unicode_literals

from collections import OrderedDict
import json

from django.core.exceptions import ValidationError
from django.utils import six
from rest_framework.relations import PKOnlyObject
from rest_framework.serializers import (
    CharField, IntegerField, PrimaryKeyRelatedField, ManyRelatedField,
    MANY_RELATION_KWARGS)


class CurrentHistoryField(PrimaryKeyRelatedField):
    """Field is the current history object

    To use this field, initialize the manager to the name of the
    HistoricalRecords object (defaults to 'history')
    """

    def __init__(self, *args, **kwargs):
        self.manager = kwargs.pop('manager', 'history')
        read_only = kwargs.pop('read_only', None)
        queryset = None if read_only else 'to do'
        required = kwargs.pop('required', False)
        assert not required, 'required must be False'
        super(CurrentHistoryField, self).__init__(
            required=required, queryset=queryset, read_only=read_only,
            *args, **kwargs)

    def bind(self, field_name, parent):
        """Initialize the field_name and parent for the instance

        history_current only makes sense in the context of an object.
        However, some views, such as the browsable API, might try to access
        the queryset outside of an object context.  We initialize the
        queryset to the none() queryset, so certain operations (such as
        determining the model or calling all()) will return expected data.
        """
        self.full_queryset = getattr(parent.Meta.model, self.manager)
        self.queryset = self.full_queryset
        super(CurrentHistoryField, self).bind(field_name, parent)

    def get_attribute(self, obj):
        """Return the entire object versus just the attribute value."""
        self.queryset = getattr(obj, self.manager)
        return obj

    def to_representation(self, obj):
        """Convert to the ID of the current history

        With a valid object, the queryset can be set to the proper history for
        this object.  In some views, such as the browsable API for the list,
        the object is not set, so we leave it as the none() queryset set in
        initialize.
        """
        return self.queryset.values_list('history_id', flat=True)[0]


class HistoricalObjectField(PrimaryKeyRelatedField):
    """Field is the ID of the historical object"""

    def __init__(self, *args, **kwargs):
        source = kwargs.pop('source', 'history_object')
        assert source == 'history_object'
        read_only = kwargs.pop('read_only', True)
        assert read_only, 'read_only must be True'
        super(HistoricalObjectField, self).__init__(
            source=source, read_only=read_only, *args, **kwargs)

    def get_attribute(self, instance):
        """Return the entire object versus just the attribute value."""
        self.queryset = type(instance.history_object)._default_manager
        return PKOnlyObject(
            pk=instance.serializable_value('history_object').pk)


class HistoryField(PrimaryKeyRelatedField):
    """Field is the history manager

    To use this field, initialize 'source' to the name of the
    HistoricalRecords object (defaults to 'history')
    """

    def __init__(self, *args, **kwargs):
        read_only = kwargs.pop('read_only', True)
        assert read_only, 'read_only must be True'
        super(HistoryField, self).__init__(
            read_only=read_only, *args, **kwargs)

    @classmethod
    def many_init(cls, *args, **kwargs):
        list_kwargs = {'child_relation': cls(*args, **kwargs)}
        for key in kwargs.keys():
            assert key in MANY_RELATION_KWARGS
            list_kwargs[key] = kwargs[key]
        return ManyHistoryField(**list_kwargs)


class ManyHistoryField(ManyRelatedField):
    def get_attribute(self, instance):
        """Set the queryset when the instance is available."""
        queryset = super(ManyHistoryField, self).get_attribute(instance)
        self.queryset = queryset
        self.child_relation.queryset = queryset
        return queryset


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

    def __init__(self, **kwargs):
        self.relation = kwargs.pop('source', None)
        read_only = kwargs.pop('read_only', True)
        assert read_only, 'read_only must be True'
        super(MPTTRelationField, self).__init__(
            read_only=read_only, **kwargs)


class OptionalCharField(CharField):
    """Field is a CharField that serializes as None when omitted"""
    def to_representation(self, value):
        if value:
            return value
        else:
            return None

    def to_internal_value(self, value):
        if value:
            return value
        else:
            return ''

    def run_validation(self, value):
        """Validate nulls from to_representation."""
        if value is None:
            return ''
        return super(OptionalCharField, self).run_validation(value)


class OptionalIntegerField(IntegerField):
    """Field is a IntegerField that serialized as None when 0"""

    def to_representation(self, value):
        if value:
            return value
        else:
            return None

    def to_internal_value(self, value):
        if value:
            return int(value)
        else:
            return 0


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
        super(TranslatedTextField, self).__init__(*args, **kwargs)

    def to_representation(self, value):
        """Convert from model Python to serializable data"""
        if value:
            if list(value.keys()) == ['zxx']:
                if self.allow_canonical:
                    return value['zxx']
                else:
                    return None
            else:
                out = OrderedDict()
                if 'en' in value:
                    out['en'] = value['en']
                for lang in sorted(value.keys()):
                    if lang != 'en':
                        out[lang] = value[lang]
                return out
        else:
            return None

    def to_internal_value(self, value):
        """Convert from serializable data to model"""
        if isinstance(value, dict):
            return value or None
        if value:
            value = value.strip()
        if value:
            if value[0] in '"{':
                try:
                    native = json.loads(value)
                except ValueError as e:
                    if self.allow_canonical:
                        native = value
                    else:
                        raise ValidationError(str(e))
            else:
                native = value
            if isinstance(native, six.string_types) and self.allow_canonical:
                return {'zxx': native}
            else:
                return native
        else:
            return None

    def run_validation(self, value):
        """Validate nulls from to_representation."""
        if value is None:
            return None
        return super(TranslatedTextField, self).run_validation(value)
