from __future__ import unicode_literals

import django
from django.db.models import sql
from django.utils.lru_cache import lru_cache

from .options import SchemaOptions


class SchemaQuery(sql.Query):
    def __init__(self, *args, **kwargs):
        self.table_schemas = kwargs.pop('table_schemas', {})
        super(SchemaQuery, self).__init__(*args, **kwargs)

    def get_meta(self):
        opts = super(SchemaQuery, self).get_meta()
        schema = self.table_schemas.get(opts.db_table)
        if schema:
            return SchemaOptions(schema, opts)
        return opts

    def join(self, join, *args, **kwargs):
        schema = self.table_schemas.get(join.table_name)
        if schema:
            join.table_name = '"%s"."%s"' % (schema, join.table_name)
        return super(SchemaQuery, self).join(join, *args, **kwargs)

    if django.VERSION >= (2, 0):
        def clone(self):
            clone = super(SchemaQuery, self).clone()
            clone.__class__ = schema_query_class_factory(self.__class__)
            clone.table_schemas = self.table_schemas
            return clone
    else:
        def clone(self, klass=None, *args, **kwargs):
            klass = schema_query_class_factory(klass or self.__class__)
            return super(SchemaQuery, self).clone(klass=klass, *args, table_schemas=self.table_schemas, **kwargs)

    def chain(self, klass=None):
        klass = schema_query_class_factory(klass or self.__class__)
        return super(SchemaQuery, self).chain(klass)


@lru_cache()
def schema_query_class_factory(query_class):
    if issubclass(query_class, SchemaQuery):
        return query_class
    return type(
        str('Schema%s' % query_class.__name__), (SchemaQuery, query_class), {}
    )


SchemaInsertQuery = schema_query_class_factory(sql.InsertQuery)
SchemaUpdateQuery = schema_query_class_factory(sql.UpdateQuery)
SchemaDeleteQuery = schema_query_class_factory(sql.DeleteQuery)
