import os
import posixpath

from .base import *

ALLOWED_HOSTS = [
    'localhost',
]
INTERNAL_IPS = [
        '127.0.0.1',
        'localhost',
]

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'theatrefestV2',
        'USER': 'theatrefest',
        'PASSWORD': 'barnum',
        'HOST': 'localhost',
        'PORT': '5432',
    },
}

# Static files (CSS, JavaScript, Images)
STATICFILES_DIRS = [
	os.path.join(BASE_DIR, "static"),
]
STATIC_ROOT = os.path.join(BASE_DIR, "django_static")
STATIC_URL = '/static/'
MEDIA_ROOT = os.path.join(BASE_DIR, "media")
MEDIA_URL = "/media/"

# E-mail
EMAIL_HOST = "smtp.mailgun.org"
EMAIL_PORT = 587
EMAIL_HOST_USER = "postmaster@mg.theatrefest.co.uk"
EMAIL_HOST_PASSWORD = get_secret("MAILGUN_EMAIL_HOST_PASSWORD")
EMAIL_USE_TLS = True

# Logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        'request': {
            '()': 'django_requestlogging.logging_filters.RequestFilter',
        }
    },
    "formatters": {
        "basic": {
            "format": "%(asctime)s %(levelname)-8s %(name)-32s %(message)s",
        },
        "request": {
            "format": "%(asctime)s %(levelname)-8s %(username)-32s %(name)-32s %(message)s",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "basic",
        },
        "theatrefest": {
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": r"C:\Temp\Theatrefest\theatrefest.log",
            "when": "midnight",
            "interval": 1,
            "backupCount": 10,
            "filters": ['request'],
            "formatter": "request",
        },
        "django": {
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": r"C:\Temp\Theatrefest\django.log",
            "when": "midnight",
            "interval": 1,
            "backupCount": 10,
            "formatter": "basic",
        },
    },
    "loggers": {
        "django": {
            "level": "INFO",
            "handlers": ["console", "django"],
            "propagate": False,
        },
        "django.server": {
            "level": "WARNING",
            "handlers": ["django"],
            "propagate": False,
        },
    },
    "root": {
        "level": "INFO",
        "handlers": ["console", "theatrefest"],
    },
}
