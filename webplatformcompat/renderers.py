try:
    from collections import OrderedDict
except ImportError:  # pragma: no cover
    # py26 doesn't get ordered dicts
    OrderedDict = dict

from django.utils import encoding

from rest_framework.utils.encoders import JSONEncoder
from rest_framework_json_api.renderers import JsonApiRenderer \
    as BaseJsonApiRender
from rest_framework_json_api.renderers import WrapperNotApplicable
from rest_framework_json_api.utils import snakecase


class JsonApiRenderer(BaseJsonApiRender):
    encoder_class = JSONEncoder
    wrappers = ([
        'wrap_jsonapi_aware',
        'wrap_paginated',
        ] + BaseJsonApiRender.wrappers)
    dict_class = OrderedDict

    def wrap_jsonapi_aware(self, data, renderer_context):
        jsonapi = renderer_context.get('jsonapi', {})
        direct = jsonapi.get('direct')
        if not jsonapi or not direct:
            raise WrapperNotApplicable('No jsonapi in context')
        return data

    def wrap_paginated(self, data, renderer_context):
        pagination_keys = ['count', 'next', 'previous', 'results']
        for key in pagination_keys:
            if not (data and key in data):
                raise WrapperNotApplicable('Not paginated results')

        view = renderer_context.get("view", None)
        model = self.model_from_obj(view)
        resource_type = self.model_to_resource_type(model)

        # Use default wrapper for results
        wrapper = self.wrap_default(data['results'], renderer_context)

        # Add pagination metadata
        pagination = self.dict_class()
        pagination['previous'] = data['previous']
        pagination['next'] = data['next']
        pagination['count'] = data['count']
        wrapper.setdefault('meta', self.dict_class())
        wrapper['meta'].setdefault('pagination', self.dict_class())
        wrapper['meta']['pagination'].setdefault(
            resource_type, self.dict_class()).update(pagination)
        return wrapper

    def wrap_error(
            self, data, renderer_context, keys_are_fields, issue_is_title):
        # Fix bug about wrong name for non_field_error
        wrapper = super(JsonApiRenderer, self).wrap_error(
            data, renderer_context, keys_are_fields, issue_is_title)
        for error in wrapper['errors']:
            if error.get("path") == '/__all__':
                error["path"] = '/-'
        return wrapper

    def model_to_resource_type(self, model):
        if model:
            return snakecase(model._meta.verbose_name_plural)
        else:
            return 'data'

    def handle_related_field(self, resource, field, field_name, request):
        '''Handle PrimaryKeyRelatedField

        Same as base handle_related_field, but:
        - adds href to links, using DRF default name
        - doesn't handle data not in fields
        '''
        links = self.dict_class()
        linked_ids = self.dict_class()

        model = self.model_from_obj(field)
        resource_type = self.model_to_resource_type(model)

        format_kwargs = {
            'model_name': model._meta.object_name.lower()
        }
        view_name = '%(model_name)s-detail' % format_kwargs

        assert field_name in resource
        links[field_name] = {
            "type": resource_type,
            "href": self.url_to_template(view_name, request, field_name)
        }

        if field.many:
            pks = resource[field_name]
        else:
            pks = [resource[field_name]]

        link_data = []
        for pk in pks:
            if pk is None:
                link_data.append(None)
            else:
                link_data.append(encoding.force_text(pk))

        if field.many:
            linked_ids[field_name] = link_data
        else:
            linked_ids[field_name] = link_data[0]

        return {"linked_ids": linked_ids, "links": links}
