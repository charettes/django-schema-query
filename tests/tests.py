from __future__ import unicode_literals

from unittest import expectedFailure

import django
from django.db.models import F
from django.db.models.aggregates import Count
from django.test.testcases import TestCase

from schema_query.queryset import SchemaQuerySet

from .models import (
    Bar, Foo, FooSubclass, UnmanagedBar, UnmanagedFoo, UnmanagedFooSubclass,
)


class SchemaQuerySetTests(TestCase):
    table_schemas = {
        UnmanagedFoo._meta.db_table: 'schema',
        UnmanagedBar._meta.db_table: 'schema',
        UnmanagedBar.foos.through._meta.db_table: 'schema',
        UnmanagedFooSubclass._meta.db_table: 'schema',
    }

    @classmethod
    def setUpTestData(cls):
        cls.foo = Foo.objects.create()
        cls.foo_subclass = FooSubclass.objects.create()

    def setUp(self):
        self.queryset = SchemaQuerySet(
            UnmanagedFoo,
            table_schemas=self.table_schemas,
        )

    def test_insert(self):
        self.assertEqual(self.queryset.create().pk, Foo.objects.values_list('pk', flat=True).latest('pk'))

    def test_select(self):
        self.assertEqual(self.queryset.get(pk=self.foo.pk).pk, self.foo.pk)

    def test_update(self):
        self.queryset.update(id=F('id') + 100)
        self.assertEqual(self.queryset.get(pk=self.foo.id + 100).id, self.foo.id + 100)

    def test_delete(self):
        self.queryset.delete()
        self.assertFalse(Foo.objects.exists())

    def test_select_related(self):
        self.assertEqual(
            self.queryset.select_related('foosubclass').latest('id').foosubclass.pk,
            self.foo_subclass.pk
        )

    def test_aggregate(self):
        self.assertEqual(self.queryset.count(), 2)
        self.assertEqual(self.queryset[0:1].count(), 1)
        self.assertEqual(self.queryset.distinct().count(), 2)
        self.queryset.aggregate(Count('pk'), Count('foosubclass'))
        self.queryset[0:1].aggregate(Count('pk'), Count('foosubclass'))
        self.queryset.distinct().aggregate(Count('pk'), Count('foosubclass'))


class SchemaModelTests(TestCase):
    table_schemas = {
        UnmanagedFoo._meta.db_table: 'schema',
        UnmanagedBar._meta.db_table: 'schema',
        UnmanagedBar.foos.through._meta.db_table: 'schema',
        UnmanagedFooSubclass._meta.db_table: 'schema',
    }

    @classmethod
    def setUpTestData(cls):
        cls.foo = Foo.objects.create()
        cls.foo_subclass = FooSubclass.objects.create(foo_ptr=cls.foo)
        cls.bar = Bar.objects.create(foo=cls.foo)
        cls.bar.foos.add(cls.foo)

    def setUp(self):
        self.foo_queryset = SchemaQuerySet(
            UnmanagedFoo,
            table_schemas=self.table_schemas,
        )
        self.foo_subclass_queryset = SchemaQuerySet(
            UnmanagedFooSubclass,
            table_schemas=self.table_schemas,
        )
        self.bar_queryset = SchemaQuerySet(
            UnmanagedBar,
            table_schemas=self.table_schemas,
        )

    def test_update(self):
        bar = self.bar_queryset.get()
        bar.save()
        foo_subclass = self.foo_subclass_queryset.get()
        foo_subclass.save()

    def test_delete(self):
        bar = self.bar_queryset.get()
        bar.delete()
        self.assertFalse(self.bar_queryset.exists())
        foo_subclass = self.foo_subclass_queryset.get()
        foo_subclass.delete()
        self.assertFalse(self.foo_subclass_queryset.exists())
        self.assertFalse(self.foo_queryset.exists())

    def test_refresh_from_db(self):
        bar = self.bar_queryset.get()
        bar.refresh_from_db()
        foo_subclass = self.foo_subclass_queryset.get()
        foo_subclass.refresh_from_db()
    if django.VERSION < (2, 1):
        # The refresh_from_db() function is broken on Django < 2.1 because it
        # doesn't pass along the origin instance as an hint do db_manager().
        test_refresh_from_db = expectedFailure(test_refresh_from_db)

    def test_foreign_key_access(self):
        bar = self.bar_queryset.get()
        self.assertEqual(bar.foo.pk, self.foo.pk)

    def test_reverse_foreign_key_access(self):
        foo = self.foo_queryset.get()
        self.assertEqual(foo.bars.get().pk, self.bar.pk)

    def test_one_to_one_access(self):
        foo_subclass = self.foo_subclass_queryset.get()
        self.assertEqual(foo_subclass.foo_ptr.pk, self.foo.pk)

    def test_reverse_one_to_one_access(self):
        foo = self.foo_queryset.get()
        self.assertEqual(foo.foosubclass.pk, self.foo.pk)

    def test_m2m_access(self):
        bar = self.bar_queryset.get()
        self.assertEqual(bar.foos.get().pk, self.foo.pk)

    def test_reverse_m2m_access(self):
        foo = self.foo_queryset.get()
        self.assertEqual(foo.m2m_bars.get().pk, self.bar.pk)
