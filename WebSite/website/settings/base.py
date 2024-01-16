import os
import posixpath
import json
from decimal import Decimal

from django.core.exceptions import ImproperlyConfigured
from django.contrib.messages import constants as messages

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Read JSON secrets file
with open(os.path.join(BASE_DIR, 'secrets.json')) as f:
    secrets = json.loads(f.read())

def get_secret(setting):
    try:
        return secrets[setting]
    except KeyError:
        raise ImproperlyConfigured("Secret {0} not found".format(setting))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = get_secret("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# Internationalization
# https://docs.djangoproject.com/en/1.9/topics/i18n/
LANGUAGE_CODE = 'en-us'
#TIME_ZONE = 'UTC'
TIME_ZONE = 'Europe/London'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Application definition
INSTALLED_APPS = [
    'dal',
    'dal_select2',

    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'debug_toolbar',
    'crispy_forms',
    'crispy_bootstrap4',
    'widget_tweaks',
    'bootstrap_datepicker_plus',
    'django_select2',
    'django_htmx',

    #'sslserver',
    
    'core.apps.CoreConfig',
    'content.apps.ContentConfig',
    'festival.apps.FestivalConfig',
    'program.apps.ProgramConfig',
    'tickets.apps.TicketsConfig',
    'venue.apps.VenueConfig',
    'boxoffice.apps.BoxOfficeConfig',
    'reports.apps.ReportsConfig',
    'volunteers.apps.VolunteersConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.contrib.sites.middleware.CurrentSiteMiddleware',

    'debug_toolbar.middleware.DebugToolbarMiddleware',
    'django_requestlogging.middleware.LogSetupMiddleware',
    'django_htmx.middleware.HtmxMiddleware',

    'core.middleware.FestivalMiddleware',
]

AUTHENTICATION_BACKENDS = [
    'core.backends.AuthBackend',
]

ROOT_URLCONF = 'website.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR + '/templates/',
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'website.wsgi.application'

MESSAGE_TAGS = {
    messages.INFO: 'alert alert-info',
    messages.SUCCESS: 'alert alert-success',
    messages.WARNING: 'alert alert-warning',
    messages.ERROR: 'alert alert-danger',
}

# Default auot-field type (to avoid unwanted migrations in the future)
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

# User model
AUTH_USER_MODEL = "core.User"

# Logon and registration
LOGIN_URL = "/login"
ACCOUNT_ACTIVATION_DAYS = 7
REGISTRATION_AUTO_LOGIN = True
LOGIN_REDIRECT_URL = "/home"
LOGOUT_REDIRECT_URL = "/home"

# Crisp forms
CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap4'
CRISPY_TEMPLATE_PACK = 'bootstrap4'

# Sessions
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# Application settings
DEFAULT_FESTIVAL = 'TF2024'
VOLUNTEER_CANCEL_SHIFTS = False

# Suppress unwanted system checks
SILENCED_SYSTEM_CHECKS = ["auth.W004"]