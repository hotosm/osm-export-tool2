# noqa
# -*- coding: utf-8 -*-
from __future__ import absolute_import

import os

import dj_database_url
import dramatiq
from dramatiq.brokers.redis import RedisBroker

from .base import *
from .contrib import *
from .utils import ABS_PATH
from hdx.hdx_configuration import Configuration

# Project apps
INSTALLED_APPS += (
    'jobs',
    'tasks',
    'api',
    'ui',
    'utils',
)

dramatiq.set_broker(RedisBroker(host="localhost", port=6379))

DATABASES = {}

DATABASES['default'] = dj_database_url.config(default='postgis:///exports', conn_max_age=500)

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': ['api/templates/', 'ui/templates', 'ui/static/ui/js'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.contrib.messages.context_processors.messages',
                'social_django.context_processors.backends',
                'social_django.context_processors.login_redirect',
            ],
            'debug': DEBUG
        },
    },
]

LOGIN_URL = '/login/'

# where exports are staged for processing
EXPORT_STAGING_ROOT = os.getenv('EXPORT_STAGING_ROOT',ABS_PATH('../export_staging/'))

# where exports are stored for public download
EXPORT_DOWNLOAD_ROOT = os.getenv('EXPORT_DOWNLOAD_ROOT',ABS_PATH('../export_downloads/'))

# the root url for export downloads
EXPORT_MEDIA_ROOT = '/downloads/'

OSMAND_MAP_CREATOR_DIR = os.getenv('OSMAND_MAP_CREATOR_DIR', '/usr/local/OsmAndMapCreator')
GARMIN_SPLITTER = os.getenv('GARMIN_SPLITTER', '/usr/local/splitter/splitter.jar')
GARMIN_MKGMAP = os.getenv('GARMIN_MKGMAP', '/usr/local/mkgmap/mkgmap.jar')

# url to overpass api endpoint
OVERPASS_API_URL = os.getenv('OVERPASS_API_URL', 'http://overpass-api.de/api/')
GENERATE_MWM = os.getenv('GENERATE_MWM','/usr/local/bin/generate_mwm.sh')
GENERATOR_TOOL = os.getenv('GENERATOR_TOOL','/usr/local/bin/generator_tool')
PLANET_FILE = os.getenv('PLANET_FILE','')

"""
Maximum extent of a Job
max of (latmax-latmin) * (lonmax-lonmin)
"""
JOB_MAX_EXTENT = 2500000  # default export max extent in sq km

HOSTNAME = os.getenv('HOSTNAME', 'localhost')

# Comment if you are not running behind proxy
USE_X_FORWARDED_HOST = bool(os.getenv('USE_X_FORWARDED_HOST'))
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Hosts/domain names that are valid for this site
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = ['exports-prod.hotosm.org', 'export.hotosm.org', HOSTNAME, '127.0.0.1']

"""
Overpass Element limit

Sets the max ram allowed for overpass query

http://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_QL#Element_limit_.28maxsize.29
"""

OVERPASS_MAX_SIZE = 2147483648  # 2GB

"""
Overpass timeout setting

Sets request timeout for overpass queries.

http://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_QL#timeout
"""

OVERPASS_TIMEOUT = 1600  # query timeout in seconds

if os.getenv('DJANGO_ENV') == 'development':
    INSTALLED_APPS += (
        'django_extensions',
    )

    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

    LOGGING_OUTPUT_ENABLED = DEBUG
    LOGGING_LOG_SQL = DEBUG

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s",
            'datefmt': "%d/%b/%Y %H:%M:%S"
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
            'level': os.getenv('LOG_LEVEL', 'DEBUG'),
        }
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'propagate': True,
            'level': os.getenv('DJANGO_LOG_LEVEL', 'ERROR'),
        },
        'api': {
            'handlers': ['console'],
            'propagate': True,
            'level': 'DEBUG',
        },
        'api.tests': {
            'handlers': ['console'],
            'propagate': True,
            'level': 'DEBUG',
        },
        'tasks.tests': {
            'handlers': ['console'],
            'propagate': True,
            'level': 'DEBUG',
        },
        'tasks': {
            'handlers': ['console'],
            'propagate': True,
            'level': 'DEBUG',
        },
        'jobs': {
            'handlers': ['console'],
            'propagate': True,
            'level': 'DEBUG',
        },
        'jobs.tests': {
            'handlers': ['console'],
            'propagate': True,
            'level': 'DEBUG',
        },
        'utils': {
            'handlers': ['console'],
            'propagate': True,
            'level': 'DEBUG',
        },
        'utils.tests': {
            'handlers': ['console'],
            'propagate': True,
            'level': 'DEBUG',
        },
        'hot_exports': {
            'handlers': ['console'],
            'propagate': True,
            'level': 'DEBUG',
        },
        'hdx_exports': {
            'handlers': ['console'],
            'propagate': True,
            'level': 'DEBUG',
        },
    }
}

EMAIL_HOST = os.getenv('EMAIL_HOST')
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
EMAIL_PORT = os.getenv('EMAIL_PORT',587)
EMAIL_USE_TLS = bool(os.getenv('EMAIL_USE_TLS',True))
REPLY_TO_EMAIL = os.getenv('REPLY_TO_EMAIL')

SPATIALITE_LIBRARY_PATH = 'mod_spatialite'

SYNC_TO_HDX = bool(os.getenv('SYNC_TO_HDX'))
HDX_API_KEY = os.getenv('HDX_API_KEY')
HDX_NOTIFICATION_EMAIL = os.getenv('HDX_NOTIFICATION_EMAIL')
HDX_SITE = os.getenv('HDX_SITE', 'demo')

GEONAMES_API_URL = os.getenv('GEONAMES_API_URL', 'http://api.geonames.org/searchJSON')

HDX_URL_PREFIX = Configuration.create(
    hdx_site=os.getenv('HDX_SITE', 'demo'),
    hdx_key=os.getenv('HDX_API_KEY'),
    user_agent="HOT Export Tool"
)
