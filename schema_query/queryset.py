from __future__ import unicode_literals

from functools import partial

from django.db import models

from .deletion import Collector
from .managers import SchemaBaseManager
from .query import SchemaDeleteQuery, SchemaInsertQuery, SchemaQuery


class SchemaIterableClass(models.query.ModelIterable):
    def __iter__(self):
        table_schemas = self.queryset._table_schemas
        iterator = super(SchemaIterableClass, self).__iter__()
        for obj in iterator:
            obj._state.table_schemas = table_schemas
            yield obj


class SchemaQuerySet(models.QuerySet):
    base_manager_class = SchemaBaseManager

    def __init__(self, model=None, query=None, *args, **kwargs):
        self._table_schemas = kwargs.pop('table_schemas', {})
        if query is None:
            query = SchemaQuery(model, table_schemas=self._table_schemas)
        super(SchemaQuerySet, self).__init__(model=model, query=query, *args, **kwargs)
        self._iterable_class = SchemaIterableClass

    def _clone(self, **kwargs):
        table_schemas = kwargs.pop('table_schemas', self._table_schemas)
        clone = super(SchemaQuerySet, self)._clone(**kwargs)
        clone._table_schemas = table_schemas
        return clone

    def as_manager(cls):
        # Obligatory copy-pasta of QuerySet.as_manager because the latter
        # doesn't allow specifying a custom base manager class.
        manager = cls.base_manager_class.from_queryset(cls)()
        manager._built_with_as_manager = True
        return manager
    as_manager.queryset_only = True
    as_manager = classmethod(as_manager)

    def create(self, **kwargs):
        """
        Creates a new object with the given kwargs, saving it to the database
        and returning the created object.
        """
        obj = self.model(**kwargs)
        self._for_write = True
        obj.save(force_insert=True, using=self.db, table_schemas=self._table_schemas)
        return obj

    @property
    def insert_query_class(self):
        return partial(SchemaInsertQuery, table_schemas=self.query.table_schemas)

    def _insert(self, objs, fields, return_id=False, raw=False, using=None):
        """
        Inserts a new record for the given model. This provides an interface to
        the InsertQuery class and is how Model.save() is implemented.
        """
        self._for_write = True
        if using is None:
            using = self.db
        query = self.insert_query_class(self.model)
        query.insert_values(fields, objs, raw=raw)
        return query.get_compiler(using=using).execute_sql(return_id)
    _insert.alters_data = True
    _insert.queryset_only = False

    @property
    def delete_query_class(self):
        return partial(SchemaDeleteQuery, table_schemas=self.query.table_schemas)

    @property
    def deletion_collector_class(self):
        return partial(Collector, table_schemas=self._table_schemas)

    def delete(self):
        """
        Deletes the records in the current QuerySet.
        """
        # Obligatory copy-pasta of django.db.models.QuerySet.delete because
        # the former doesn't allow specifying a custom deletion collector
        # class.
        assert self.query.can_filter(), \
            "Cannot use 'limit' or 'offset' with delete."

        if self._fields is not None:
            raise TypeError("Cannot call delete() after .values() or .values_list()")

        del_query = self._clone()

        # The delete is actually 2 queries - one to find related objects,
        # and one to delete. Make sure that the discovery of related
        # objects is performed on the same database as the deletion.
        del_query._for_write = True

        # Disable non-supported fields.
        del_query.query.select_for_update = False
        del_query.query.select_related = False
        del_query.query.clear_ordering(force_empty=True)

        collector = self.deletion_collector_class(using=del_query.db)
        collector.collect(del_query)
        deleted, _rows_count = collector.delete()

        # Clear the result cache, in case this QuerySet gets reused.
        self._result_cache = None
        return deleted, _rows_count
    delete.alters_data = True
    delete.queryset_only = True

    def _raw_delete(self, using):
        """
        Deletes objects found from the given queryset in single direct SQL
        query. No signals are sent, and there is no protection for cascades.
        """
        # Obligatory copy-pasta of django.db.models.QuerySet.delete because
        # the former doesn't allow specifying a custom delete query class.
        return self.delete_query_class(self.model).delete_qs(self, using)
    _raw_delete.alters_data = True
