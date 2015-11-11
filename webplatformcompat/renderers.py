from collections import OrderedDict
from json import loads

from django.core.urlresolvers import get_resolver
from django.template import loader, Context
from django.utils import encoding, translation
from django.utils.six.moves.urllib.parse import urlparse, urlunparse

from rest_framework.relations import ManyRelatedField
from rest_framework.renderers import TemplateHTMLRenderer
from rest_framework.renderers import BrowsableAPIRenderer as BaseAPIRenderer
from rest_framework.serializers import ListSerializer
from rest_framework.status import HTTP_200_OK, HTTP_204_NO_CONTENT
from rest_framework.utils.encoders import JSONEncoder
from rest_framework.utils.serializer_helpers import ReturnList
from rest_framework_json_api.renderers import JsonApiRenderer \
    as BaseJsonApiRender
from rest_framework_json_api.renderers import WrapperNotApplicable
from rest_framework_json_api.utils import snakecase, model_from_obj


class JsonApiRenderer(BaseJsonApiRender):
    convert_by_name = BaseJsonApiRender.convert_by_name
    convert_by_name.update({
        'meta': 'add_meta',
    })
    convert_by_type = BaseJsonApiRender.convert_by_type
    convert_by_type.update({
        ManyRelatedField: 'handle_related_field',
        ListSerializer: 'handle_list_serializer',
    })
    dict_class = OrderedDict
    encoder_class = JSONEncoder
    wrappers = ([
        'wrap_view_extra',
        'wrap_view_extra_error',
    ] + BaseJsonApiRender.wrappers)

    def add_meta(self, resource, field, field_name, request):
        """Add metadata."""
        data = resource[field_name]
        return {'meta': data}

    def wrap_paginated(self, data, renderer_context):
        """Convert paginated data to JSON API with meta"""
        pagination_keys = ['count', 'next', 'previous', 'results']
        for key in pagination_keys:
            if not (data and key in data):
                raise WrapperNotApplicable('Not paginated results')

        view = renderer_context.get("view", None)
        model = self.model_from_obj(view)
        resource_type = self.model_to_resource_type(model)

        # Use default wrapper for results
        # DRF 3.x - data['results'] is ReturnList
        assert isinstance(data['results'], ReturnList)
        results = []
        fields = self.fields_from_resource(data['results'].serializer.child)
        assert fields
        for result in data['results']:
            result.fields = fields
            results.append(result)
        wrapper = self.wrap_default(results, renderer_context)

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

    def handle_list_serializer(self, resource, field, field_name, request):
        serializer = field.child
        model = serializer.Meta.model
        resource_type = self.model_to_resource_type(model)

        linked_ids = self.dict_class()
        links = self.dict_class()
        linked = self.dict_class()
        linked[resource_type] = []

        many = field.many
        assert many
        items = resource[field_name]

        obj_ids = []
        for item in items:
            item.serializer = serializer
            item.serializer.model = model
            converted = self.convert_resource(item, request)
            linked_obj = converted["data"]
            converted_ids = converted.pop("linked_ids", {})
            assert converted_ids
            linked_obj["links"] = converted_ids
            obj_ids.append(converted["data"]["id"])

            field_links = self.prepend_links_with_name(
                converted.get("links", {}), resource_type)
            links.update(field_links)

            linked[resource_type].append(linked_obj)

        linked_ids[field_name] = obj_ids
        return {"linked_ids": linked_ids, "links": links, "linked": linked}

    def wrap_view_extra(self, data, renderer_context):
        """Add nested data w/o adding links to main resource."""
        if not (data and '_view_extra' in data):
            raise WrapperNotApplicable('Not linked results')
        response = renderer_context.get("response", None)
        status_code = response and response.status_code
        if status_code == 400:
            raise WrapperNotApplicable('Status code must not be 400.')

        linked = data.pop('_view_extra')
        data.serializer.fields.pop('_view_extra')
        wrapper = self.wrap_default(data, renderer_context)
        assert 'linked' not in wrapper

        wrapper_linked = self.wrap_default(linked, renderer_context)
        to_transfer = ('links', 'linked', 'meta')
        for key, value in wrapper_linked.items():
            if key in to_transfer:
                wrapper.setdefault(key, self.dict_class()).update(value)
        return wrapper

    def wrap_view_extra_error(self, data, renderer_context):
        """Convert field errors involving _view_extra"""
        response = renderer_context.get("response", None)
        status_code = response and response.status_code
        if status_code != 400:
            raise WrapperNotApplicable('Status code must be 400.')
        if not (data and '_view_extra' in data):
            raise WrapperNotApplicable('Not linked results')

        view_extra = data.pop('_view_extra')
        assert isinstance(view_extra, dict)
        converted = {}
        for rname, error_dict in view_extra.items():
            assert rname != 'meta'
            for seq, errors in error_dict.items():
                for fieldname, error in errors.items():
                    name = 'linked.%s.%d.%s' % (rname, seq, fieldname)
                    converted[name] = error
        data.update(converted)

        return self.wrap_error(
            data, renderer_context, keys_are_fields=True, issue_is_title=False)

    def model_to_resource_type(self, model):
        if model:
            return snakecase(model._meta.verbose_name_plural)
        else:
            return 'data'

    def handle_related_field(self, resource, field, field_name, request):
        """Handle PrimaryKeyRelatedField

        Same as base handle_related_field, but:
        - adds href to links, using DRF default name
        - doesn't handle data not in fields
        - uses presence of child_relation attribute to signify "many"
        """
        links = self.dict_class()
        linked_ids = self.dict_class()

        many = hasattr(field, 'child_relation')
        model = self.model_from_obj(field)
        if model:
            resource_type = self.model_to_resource_type(model)

            format_kwargs = {
                'model_name': model._meta.object_name.lower()
            }
            view_name = '%(model_name)s-detail' % format_kwargs

            links[field_name] = self.dict_class((
                ("type", resource_type),
                ("href", self.url_to_template(view_name, request, field_name)),
            ))

        assert field_name in resource
        if many:
            pks = resource[field_name]
        else:
            pks = [resource[field_name]]

        link_data = []
        for pk in pks:
            if pk is None:
                link_data.append(None)
            else:
                link_data.append(encoding.force_text(pk))

        if many:
            linked_ids[field_name] = link_data
        else:
            linked_ids[field_name] = link_data[0]

        return {"linked_ids": linked_ids, "links": links}

    def model_from_obj(self, obj):
        model = model_from_obj(obj)
        if not model and hasattr(obj, 'child_relation'):
            model = model_from_obj(obj.child_relation)
        if (not model and hasattr(obj, 'parent') and
                hasattr(obj.parent, 'instance') and hasattr(obj, 'source')):
            instance = obj.parent.instance
            if instance:
                if isinstance(instance, list):
                    instance = instance[0]
                model = model_from_obj(getattr(instance, obj.source))
                if not model:
                    model = type(getattr(instance, obj.source))
        return model

    def fields_from_resource(self, resource):
        if hasattr(resource, 'serializer'):
            return getattr(resource.serializer, 'fields', None)
        else:
            return super(JsonApiRenderer, self).fields_from_resource(resource)

    def url_to_template(self, view_name, request, template_name):
        prefix, resolver = get_resolver(None).namespace_dict['v1']
        info = resolver.reverse_dict[view_name]
        path_template = info[0][0][0]
        id_field = info[0][0][1][0]
        path = prefix + path_template % {id_field: '{%s}' % template_name}
        parsed_url = urlparse(request.build_absolute_uri())
        return urlunparse(
            [parsed_url.scheme, parsed_url.netloc, path, '', '', '']
        )


class JsonApiTemplateHTMLRenderer(TemplateHTMLRenderer):
    """Render to a template, but use JSON API format as context."""

    def render(self, data, accepted_media_type=None, renderer_context=None):
        """Generate JSON API representation, as well as collection."""
        # Set the context to the JSON API represention
        json_api_renderer = JsonApiRenderer()
        json_api = json_api_renderer.render(
            data, accepted_media_type, renderer_context)
        context = loads(
            json_api.decode('utf-8'), object_pairs_hook=OrderedDict)

        # Is it an error?
        if 'errors' in context:
            error_context = Context(context)
            return super(JsonApiTemplateHTMLRenderer, self).render(
                error_context, accepted_media_type, renderer_context)

        # Copy main item to generic 'data' key
        other_keys = ('linked', 'links', 'meta')
        main_keys = [m for m in context.keys() if m not in other_keys]
        assert len(main_keys) == 1
        main_type = main_keys[0]
        main_obj = context[main_type].copy()
        main_id = main_obj['id']
        context['data'] = main_obj
        context['data']['type'] = main_type

        # Add a collection of types and IDs
        collection = {}
        for resource_type, resources in context.get('linked', {}).items():
            assert resource_type not in collection
            collection[resource_type] = {}
            for resource in resources:
                resource_id = resource['id']
                assert resource_id not in collection[resource_type]
                collection[resource_type][resource_id] = resource
        collection.setdefault(main_type, {})[main_id] = main_obj
        context['collection'] = collection

        # Add language
        request = renderer_context['request']
        lang = request.GET.get('lang', translation.get_language())
        context['lang'] = lang

        # Render HTML template w/ context
        return super(JsonApiTemplateHTMLRenderer, self).render(
            context, accepted_media_type, renderer_context)

    def resolve_context(self, data, request, response):
        """Resolve context without a RequestContext."""
        if response.exception:  # pragma: no cover
            data['status_code'] = response.status_code
        return data


class BrowsableAPIRenderer(BaseAPIRenderer):
    """Jinja2 renderer used to self-document the API."""
    def render(self, data, accepted_media_type=None, renderer_context=None):
        """
        Render the HTML for the browsable API representation.

        Same as base renderer, but uses a plain dict and request instead of
        constructing a RequestContext.
        """
        self.accepted_media_type = accepted_media_type or ''
        self.renderer_context = renderer_context or {}

        template = loader.get_template(self.template)
        context = self.get_context(data, accepted_media_type, renderer_context)
        ret = template.render(context, context.get('request'))

        # Munge DELETE Response code to allow us to return content
        # (Do this *after* we've rendered the template so that we include
        # the normal deletion response code in the output)
        response = renderer_context['response']
        if response.status_code == HTTP_204_NO_CONTENT:  # pragma: no cover
            response.status_code = HTTP_200_OK

        return ret
