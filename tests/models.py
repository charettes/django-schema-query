from __future__ import unicode_literals

from django.db import models

from schema_query.models import SchemaModel


class Foo(models.Model):
    class Meta:
        db_table = '"schema"."foo"'


class FooSubclass(Foo):
    foo_ptr = models.OneToOneField(
                    auto_created=True, on_delete=models.CASCADE,
                    parent_link=True, primary_key=True, serialize=False, to='tests.Foo', db_constraint=False)

    class Meta:
        db_table = '"schema"."foosubclass"'


class Bar(models.Model):
    foo = models.ForeignKey(Foo, models.SET_NULL, null=True, related_name='bars', db_constraint=False)
    foos = models.ManyToManyField(Foo, db_table='"schema"."bar_foos"', related_name='m2m_bars', db_constraint=False)

    class Meta:
        db_table = '"schema"."bar"'


class UnmanagedFoo(SchemaModel):
    class Meta:
        managed = False
        db_table = 'foo'


class UnmanagedFooSubclass(UnmanagedFoo):
    foo_ptr = models.OneToOneField(
                    auto_created=True, on_delete=models.CASCADE,
                    parent_link=True, primary_key=True, serialize=False, to='tests.UnmanagedFoo',
                    db_constraint=False, related_name='foosubclass')

    class Meta:
        managed = False
        db_table = 'foosubclass'


class UnamanagedBarFoos(SchemaModel):
    foo = models.ForeignKey(UnmanagedFoo, models.CASCADE, related_name='+')
    bar = models.ForeignKey('UnmanagedBar', models.CASCADE, related_name='+')

    class Meta:
        managed = False
        db_table = 'bar_foos'


class UnmanagedBar(SchemaModel):
    foo = models.ForeignKey(UnmanagedFoo, models.SET_NULL, null=True, related_name='bars')
    foos = models.ManyToManyField(UnmanagedFoo, through=UnamanagedBarFoos, related_name='m2m_bars')

    class Meta:
        managed = False
        db_table = 'bar'
