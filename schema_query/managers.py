from __future__ import unicode_literals

from django.db.models.manager import BaseManager


class SchemaBaseManager(BaseManager):
    def get_queryset(self, **kwargs):
        instance = getattr(self, 'instance', self._hints.get('instance'))
        if instance:
            table_schemas = getattr(instance._state, 'table_schemas', {})
            kwargs.setdefault('table_schemas', table_schemas)
        return self._queryset_class(model=self.model, using=self._db, hints=self._hints, **kwargs)
