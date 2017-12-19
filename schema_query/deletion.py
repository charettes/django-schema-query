from __future__ import unicode_literals

from collections import Counter
from functools import partial
from operator import attrgetter

from django.db import transaction
from django.db.models import signals
from django.db.models.deletion import Collector
from django.utils import six

from .query import SchemaDeleteQuery, SchemaUpdateQuery


class Collector(Collector):

    def __init__(self, using, table_schemas):
        self.table_schemas = table_schemas
        self.update_query_class = partial(SchemaUpdateQuery, table_schemas=table_schemas)
        self.delete_query_class = partial(SchemaDeleteQuery, table_schemas=table_schemas)
        super(Collector, self).__init__(using)

    def related_objects(self, related, objs):
        manager = related.related_model._base_manager
        queryset = manager.get_queryset(table_schemas=self.table_schemas).using(self.using)
        return queryset.filter(
            **{"%s__in" % related.field.name: objs}
        )

    def delete(self):
        # Obligatory copy-pasta of django.db.models.deletion.Collector.delete
        # because the former doesn't allow specifying a custom update and
        # delete query classes.

        # sort instance collections
        for model, instances in self.data.items():
            self.data[model] = sorted(instances, key=attrgetter("pk"))

        # if possible, bring the models in an order suitable for databases that
        # don't support transactions or cannot defer constraint checks until the
        # end of a transaction.
        self.sort()
        # number of objects deleted for each model label
        deleted_counter = Counter()

        with transaction.atomic(using=self.using, savepoint=False):
            # send pre_delete signals
            for model, obj in self.instances_with_model():
                if not model._meta.auto_created:
                    signals.pre_delete.send(
                        sender=model, instance=obj, using=self.using
                    )

            # fast deletes
            for qs in self.fast_deletes:
                count = qs._raw_delete(using=self.using)
                deleted_counter[qs.model._meta.label] += count

            # update fields
            for model, instances_for_fieldvalues in six.iteritems(self.field_updates):
                query = self.update_query_class(model)
                for (field, value), instances in six.iteritems(instances_for_fieldvalues):
                    query.update_batch([obj.pk for obj in instances],
                                       {field.name: value}, self.using)

            # reverse instance collections
            for instances in six.itervalues(self.data):
                instances.reverse()

            # delete instances
            for model, instances in six.iteritems(self.data):
                query = self.delete_query_class(model)
                pk_list = [obj.pk for obj in instances]
                count = query.delete_batch(pk_list, self.using)
                deleted_counter[model._meta.label] += count

                if not model._meta.auto_created:
                    for obj in instances:
                        signals.post_delete.send(
                            sender=model, instance=obj, using=self.using
                        )

        # update collected instances
        for model, instances_for_fieldvalues in six.iteritems(self.field_updates):
            for (field, value), instances in six.iteritems(instances_for_fieldvalues):
                for obj in instances:
                    setattr(obj, field.attname, value)
        for model, instances in six.iteritems(self.data):
            for instance in instances:
                setattr(instance, model._meta.pk.attname, None)
        return sum(deleted_counter.values()), dict(deleted_counter)
