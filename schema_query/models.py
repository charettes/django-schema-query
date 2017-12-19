from __future__ import unicode_literals

from functools import partial

from django.db import models, router

from .deletion import Collector
from .queryset import SchemaQuerySet


class SchemaModel(models.Model):

    objects = SchemaQuerySet.as_manager()

    class Meta:
        abstract = True
        base_manager_name = 'objects'

    def save(self, *args, **kwargs):
        table_schemas = kwargs.pop('table_schemas', getattr(self._state, 'table_schemas', None))
        assert table_schemas
        self._save_table_schemas = table_schemas
        saved = super(SchemaModel, self).save(*args, **kwargs)
        self._state.table_schemas = table_schemas
        return saved

    def _do_insert(self, manager, *args, **kwargs):
        queryset = manager.get_queryset(table_schemas=self._save_table_schemas)
        return super(SchemaModel, self)._do_insert(queryset, *args, **kwargs)

    def _do_update(self, base_qs, *args, **keargs):
        base_qs = base_qs._clone(table_schemas=self._save_table_schemas)
        base_qs.query.table_schemas = self._save_table_schemas
        return super(SchemaModel, self)._do_update(base_qs, *args, **keargs)

    def delete(self, using=None, keep_parents=False):
        table_schemas = getattr(self._state, 'table_schemas', None)
        assert table_schemas
        delete_collector_class = partial(Collector, table_schemas=table_schemas)

        # Obligatory copy-pasta from Model.delete() because the latter doesn't
        # allow specifying a custom deletion collector class.
        using = using or router.db_for_write(self.__class__, instance=self)
        assert self._get_pk_val() is not None, (
            "%s object can't be deleted because its %s attribute is set to None." %
            (self._meta.object_name, self._meta.pk.attname)
        )

        collector = delete_collector_class(using=using)
        collector.collect([self], keep_parents=keep_parents)
        return collector.delete()
