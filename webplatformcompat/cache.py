'''Cache functions'''

from django.contrib.auth.models import User

from drf_cached_reads.cache import BaseCache
from .models import Browser, Feature, Maturity, Support, Version


class Cache(BaseCache):
    '''Instance Cache for webplatformcompat'''
    versions = ('v1',)
    default_version = 'v1'

    def browser_v1_serializer(self, obj):
        if not obj:
            return None

        history_pks = getattr(obj, '_history_pks', None)
        if history_pks is None:
            history_pks = list(
                obj.history.all().values_list('history_id', flat=True))

        versions_pks = getattr(obj, '_version_pks', None)
        if versions_pks is None:
            versions_pks = list(
                obj.versions.values_list('pk', flat=True))

        return dict((
            ('id', obj.pk),
            ('slug', obj.slug),
            ('name', obj.name),
            ('note', obj.note),
            self.field_to_json(
                'PKList', 'history', model=obj.history.model,
                pks=history_pks),
            self.field_to_json(
                'PK', 'history_current', model=obj.history.model,
                pk=history_pks[0]),
            self.field_to_json(
                'PKList', 'versions', model=Version, pks=versions_pks),
        ))

    def browser_v1_loader(self, pk):
        queryset = Browser.objects.all()
        try:
            obj = queryset.get(pk=pk)
        except Browser.DoesNotExist:
            return None
        else:
            obj._history_pks = list(
                obj.history.all().values_list('history_id', flat=True))
            obj._version_pks = list(
                obj.versions.values_list('pk', flat=True))
            return obj

    def browser_v1_invalidator(self, obj):
        return []

    def feature_v1_serializer(self, obj):
        if not obj:
            return None

        history_pks = getattr(obj, '_history_pks', None)
        if history_pks is None:
            history_pks = list(
                obj.history.all().values_list('history_id', flat=True))

        children_pks = getattr(obj, '_children_pks', None)
        if children_pks is None:
            children_pks = list(obj.children.values_list('pk', flat=True))

        support_pks = getattr(obj, '_support_pks', None)
        if support_pks is None:
            support_pks = list(obj.supports.values_list('pk', flat=True))

        return dict((
            ('id', obj.pk),
            ('slug', obj.slug),
            ('mdn_path', obj.mdn_path),
            ('experimental', obj.experimental),
            ('standardized', obj.standardized),
            ('stable', obj.stable),
            ('obsolete', obj.obsolete),
            ('name', obj.name),
            self.field_to_json(
                'PKList', 'supports', model=Support, pks=support_pks),
            self.field_to_json(
                'PK', 'parent', model=Feature, pk=obj.parent_id),
            self.field_to_json(
                'PKList', 'children', model=Feature, pks=children_pks),
            self.field_to_json(
                'PKList', 'history', model=obj.history.model,
                pks=history_pks),
            self.field_to_json(
                'PK', 'history_current', model=obj.history.model,
                pk=history_pks[0]),
        ))

    def feature_v1_loader(self, pk):
        queryset = Feature.objects
        try:
            obj = queryset.get(pk=pk)
        except Feature.DoesNotExist:
            return None
        else:
            obj._history_pks = list(
                obj.history.all().values_list('history_id', flat=True))
            obj._children_pks = list(obj.children.values_list('pk', flat=True))
            obj._support_pks = list(obj.supports.values_list('pk', flat=True))
            return obj

    def feature_v1_invalidator(self, obj):
        pks = []
        if obj.parent_id:
            pks.append(obj.parent_id)
        else:
            pks += list(obj.get_siblings().values_list('pk', flat=True))
        children_pks = getattr(
            obj, '_children_pks',
            list(obj.children.values_list('pk', flat=True)))
        pks += children_pks
        return [('Feature', pk, False) for pk in pks]

    def maturity_v1_serializer(self, obj):
        if not obj:
            return None

        history_pks = getattr(obj, '_history_pks', None)
        if history_pks is None:
            history_pks = list(
                obj.history.all().values_list('history_id', flat=True))

        return dict((
            ('id', obj.pk),
            ('key', obj.key),
            ('name', obj.name),
            self.field_to_json(
                'PKList', 'history', model=obj.history.model,
                pks=history_pks),
            self.field_to_json(
                'PK', 'history_current', model=obj.history.model,
                pk=history_pks[0]),
        ))

    def maturity_v1_loader(self, pk):
        queryset = Maturity.objects
        try:
            obj = queryset.get(pk=pk)
        except Maturity.DoesNotExist:
            return None
        else:
            obj._history_pks = list(
                obj.history.all().values_list('history_id', flat=True))
            return obj

    def maturity_v1_invalidator(self, obj):
        return []

    def support_v1_serializer(self, obj):
        if not obj:
            return None

        history_pks = getattr(obj, '_history_pks', None)
        if history_pks is None:
            history_pks = list(
                obj.history.all().values_list('history_id', flat=True))

        return dict((
            ('id', obj.pk),
            ('support', obj.support),
            ('prefix', obj.prefix),
            ('prefix_mandatory', obj.prefix_mandatory),
            ('alternate_name', obj.alternate_name),
            ('alternate_mandatory', obj.alternate_mandatory),
            ('requires_config', obj.requires_config),
            ('default_config', obj.default_config),
            ('protected', obj.protected),
            ('note', obj.note),
            ('footnote', obj.footnote),
            self.field_to_json(
                'PK', 'version', model=Version, pk=obj.version_id),
            self.field_to_json(
                'PK', 'feature', model=Feature, pk=obj.feature_id),
            self.field_to_json(
                'PKList', 'history', model=obj.history.model,
                pks=history_pks),
            self.field_to_json(
                'PK', 'history_current', model=obj.history.model,
                pk=history_pks[0]),
        ))

    def support_v1_loader(self, pk):
        queryset = Support.objects
        try:
            obj = queryset.get(pk=pk)
        except Support.DoesNotExist:
            return None
        else:
            obj._history_pks = list(
                obj.history.all().values_list('history_id', flat=True))
            return obj

    def support_v1_invalidator(self, obj):
        return [
            ("Version", obj.version_id, True),
            ("Feature", obj.feature_id, True),
        ]

    def version_v1_serializer(self, obj):
        if not obj:
            return None

        support_pks = getattr(obj, '_support_pks', None)
        if support_pks is None:
            support_pks = list(obj.supports.values_list('pk', flat=True))

        history_pks = getattr(obj, '_history_pks', None)
        if history_pks is None:
            history_pks = list(
                obj.history.all().values_list('history_id', flat=True))

        return dict((
            ('id', obj.pk),
            ('version', obj.version),
            self.field_to_json('Date', 'release_day', obj.release_day),
            self.field_to_json('Date', 'retirement_day', obj.retirement_day),
            ('status', obj.status),
            ('release_notes_uri', obj.release_notes_uri),
            ('note', obj.note),
            ('_order', obj._order),
            self.field_to_json(
                'PK', 'browser', model=Browser, pk=obj.browser_id),
            self.field_to_json(
                'PKList', 'supports', model=Support, pks=support_pks),
            self.field_to_json(
                'PKList', 'history', model=obj.history.model,
                pks=history_pks),
            self.field_to_json(
                'PK', 'history_current', model=obj.history.model,
                pk=history_pks[0]),
        ))

    def version_v1_loader(self, pk):
        queryset = Version.objects
        try:
            obj = queryset.select_related('supports__pk').get(pk=pk)
        except Version.DoesNotExist:
            return None
        else:
            obj._support_pks = list(obj.supports.values_list('pk', flat=True))
            obj._history_pks = list(
                obj.history.all().values_list('history_id', flat=True))
            return obj

    def version_v1_invalidator(self, obj):
        return [
            ("Browser", obj.browser_id, True)]

    def historicalbrowser_v1_serializer(self, obj):
        if not obj:
            return None
        return dict((
            ('id', obj.history_id),
            self.field_to_json('DateTime', 'date', obj.history_date),
            ('event', obj.get_history_type_display().lower()),
            self.field_to_json(
                'PK', 'user', model=User, pk=obj.history_user_id),
            self.field_to_json(
                'PK', 'browser', model=Browser, pk=obj.id),
            ('browsers', {
                'id': obj.id,
                'slug': obj.slug,
                'name': obj.name,
                'note': obj.note,
                'history_current': obj.history_id
            }),
        ))

    def historicalbrowser_v1_loader(self, pk):
        queryset = Browser.history
        try:
            return queryset.get(history_id=pk)
        except Browser.history.model.DoesNotExist:
            return None

    def historicalbrowser_v1_invalidator(self, obj):
        return []

    def user_v1_serializer(self, obj):
        if not obj or not obj.is_active:
            return None
        return dict((
            ('id', obj.id),
            ('username', obj.username),
            self.field_to_json('DateTime', 'date_joined', obj.date_joined),
        ))

    def user_v1_loader(self, pk):
        try:
            return User.objects.get(pk=pk)
        except User.DoesNotExist:
            return None

    def user_v1_invalidator(self, obj):
        return []
