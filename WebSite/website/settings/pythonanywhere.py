from .base import *

ALLOWED_HOSTS = [
    'www.theatrefest.co.uk',
]

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'HOST': 'GrahamJC-139.postgres.eu.pythonanywhere-services.com',
        'PORT': '10139',
        'NAME': 'theatrefest',
        'USER': get_secret("POSTGRES_USERNAME"),
        'PASSWORD': get_secret("POSTGRES_PASSWORD"),
    },
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Registration
REGISTRATION_TWOSTEP = False

# E-mail
EMAIL_HOST = "smtp.mailgun.org"
EMAIL_PORT = 587
EMAIL_HOST_USER = "postmaster@mg.theatrefest.co.uk"
EMAIL_HOST_PASSWORD = get_secret("MAILGUN_EMAIL_HOST_PASSWORD")
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = 'postmaster@theatrefest.co.uk'

# Stripe
STRIPE_PUBLIC_KEY = get_secret("STRIPE_PUBLIC_KEY")
STRIPE_PRIVATE_KEY = get_secret("STRIPE_PRIVATE_KEY")
STRIPE_WEBHOOK_SECRET = get_secret("STRIPE_WEBHOOK_SECRET")
STRIPE_FEE_FIXED = Decimal(0.2)
STRIPE_FEE_PERCENT = Decimal(0.015)

# Square
SQUARE_APPLICATION_ID = get_secret("SQUARE_APPLICATION_ID")
SQUARE_API_VERSION = 'v2.0'
SQUARE_CURRENCY_CODE = 'GBP'

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
        "theatrefest": {
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": r"/home/GrahamJC/TheatrefestV2/log/theatrefest.log",
            "when": "midnight",
            "interval": 1,
            "backupCount": 10,
            "filters": ['request'],
            "formatter": "request",
        },
        "django": {
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": r"/home/GrahamJC/TheatrefestV2/log/django.log",
            "when": "midnight",
            "interval": 1,
            "backupCount": 10,
            "formatter": "basic",
       }
    },
    "loggers": {
        "django": {
            "level": "INFO",
            "handlers": ["django"],
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
        "handlers": ["theatrefest"],
    },
}

# Application settings
