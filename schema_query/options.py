from __future__ import unicode_literals


class SchemaOptions(object):
    def __init__(self, schema, opts):
        self.db_table = '"%s"."%s"' % (schema, opts.db_table)
        self.__opts = opts

    def __getattr__(self, name):
        return getattr(self.__opts, name)
