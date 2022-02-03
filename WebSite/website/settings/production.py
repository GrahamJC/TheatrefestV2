from .base import *

ALLOWED_HOSTS = [
    'www.theatrefest.co.uk',
]
INTERNAL_IPS = [
    # '81.143.205.105',
]

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'theatrefest',
        'USER': 'theatrefest',
        'PASSWORD': 'barnum',
        'HOST': 'localhost',
        'PORT': '5432',
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
MEDIA_ROOT = os.path.join(BASE_DIR, "media")
MEDIA_URL = "/media/"

# Registration
REGISTRATION_TWOSTEP = True

# E-mail
EMAIL_HOST = "smtp.mailgun.org"
EMAIL_PORT = 587
EMAIL_HOST_USER = "postmaster@mg.theatrefest.co.uk"
EMAIL_HOST_PASSWORD = get_secret("MAILGUN_EMAIL_HOST_PASSWORD")
EMAIL_USE_TLS = True

# Stripe
STRIPE_PUBLIC_KEY = get_secret("STRIPE_PUBLIC_KEY")
STRIPE_PRIVATE_KEY = get_secret("STRIPE_PRIVATE_KEY")
STRIPE_WEBHOOK_SECRET = get_secret("STRIPE_WEBHOOK_SECRET")
STRIPE_FEE_FIXED = Decimal(0.2)
STRIPE_FEE_PERCENT = Decimal(0.014)

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
            "filename": r"/var/log/theatrefest/theatrefest.log",
            "when": "midnight",
            "interval": 1,
            "backupCount": 10,
            "filters": ['request'],
            "formatter": "request",
        },
        "django": {
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": r"/var/log/theatrefest/django.log",
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

# Application settings
VENUE_SHOW_ALL_PERFORMANCES = False
VOLUNTEER_CANCEL_SHIFTS = False
