from collections import OrderedDict
from json import loads

from django.utils import encoding, translation

from rest_framework.renderers import TemplateHTMLRenderer
from rest_framework.utils.encoders import JSONEncoder
from rest_framework_json_api.renderers import JsonApiRenderer \
    as BaseJsonApiRender
from rest_framework_json_api.renderers import WrapperNotApplicable
from rest_framework_json_api.utils import snakecase


class JsonApiRenderer(BaseJsonApiRender):
    convert_by_name = BaseJsonApiRender.convert_by_name
    convert_by_name.update({
        'meta': 'add_meta',
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

    def wrap_view_extra(self, data, renderer_context):
        """Add nested data w/o adding links to main resource."""
        if not (data and '_view_extra' in data):
            raise WrapperNotApplicable('Not linked results')
        response = renderer_context.get("response", None)
        status_code = response and response.status_code
        if status_code == 400:
            raise WrapperNotApplicable('Status code must not be 400.')

        linked = data.pop('_view_extra')
        data.fields.pop('_view_extra')
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
        assert isinstance(view_extra, list)
        assert len(view_extra) == 1
        converted = {}
        for rname, error_dict in view_extra[0].items():
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
        """
        links = self.dict_class()
        linked_ids = self.dict_class()

        model = self.model_from_obj(field)
        resource_type = self.model_to_resource_type(model)

        format_kwargs = {
            'model_name': model._meta.object_name.lower()
        }
        view_name = '%(model_name)s-detail' % format_kwargs

        assert field_name in resource
        links[field_name] = self.dict_class((
            ("type", resource_type),
            ("href", self.url_to_template(view_name, request, field_name)),
        ))

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
