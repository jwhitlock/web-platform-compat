from rest_framework_json_api.parsers import JsonApiParser \
    as BaseJsonApiParser
from rest_framework_json_api.parsers import JsonApiMixin
from rest_framework_json_api.utils import snakecase


class JsonApiParser(BaseJsonApiParser):
    def model_to_resource_type(self, model):
        if model:
            return snakecase(model._meta.verbose_name_plural)
        else:
            return 'data'

    def parse(self, stream, media_type=None, parser_context=None):
        """Parse JSON API representation into DRF native format.

        Same as rest_framework_json_api.parsers.JsonApiMixin.parse,
        except that linked and meta sections are put into _view_extra
        """
        data = super(JsonApiMixin, self).parse(stream, media_type=media_type,
                                               parser_context=parser_context)

        view = parser_context.get("view", None)

        model = self.model_from_obj(view)
        resource_type = self.model_to_resource_type(model)

        resource = {}

        if resource_type in data:
            resource = data[resource_type]

        if isinstance(resource, list):  # pragma: nocover
            resource = [self.convert_resource(r, view) for r in resource]
        else:
            resource = self.convert_resource(resource, view)

        # Add extra data to _view_extra
        # This should mirror .renderers.JsonApiRenderer.wrap_view_extra
        view_extra = {}
        if 'meta' in data:
            view_extra['meta'] = data['meta']
        if 'linked' in data:
            assert 'meta' not in data['linked']
            view_extra.update(data['linked'])
        if view_extra:
            resource['_view_extra'] = view_extra

        return resource
