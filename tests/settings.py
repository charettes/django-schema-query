from __future__ import unicode_literals

SECRET_KEY = 'not-anymore'

TIME_ZONE = 'America/Chicago'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'schema_query',
    }
}

INSTALLED_APPS = [
    'schema_query',
    'tests',
]
