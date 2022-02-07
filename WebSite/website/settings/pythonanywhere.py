from .base import *

ALLOWED_HOSTS = [
    'pa.theatrefest.co.uk',
]

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'HOST': 'GrahamJC-139.postgres.eu.pythonanywhere-services.com',
        'PORT': '10139',
        'NAME': 'theatrefest',
        'USER': 'theatrefest',
        'PASSWORD': 'g25mwF7wE684',
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

# Application settings
VENUE_SHOW_ALL_PERFORMANCES = False
VOLUNTEER_CANCEL_SHIFTS = False
