import os
# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
from datetime import timedelta

import sentry_sdk
from dotenv import load_dotenv
from sentry_sdk.integrations.django import DjangoIntegration

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# initialise .env
load_dotenv()

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get("SECRET_KEY")

EMAIL_CONFIRMATION_PERIOD_DAYS = 7
SIMPLE_EMAIL_CONFIRMATION_PERIOD = timedelta(days=EMAIL_CONFIRMATION_PERIOD_DAYS)
SIMPLE_EMAIL_CONFIRMATION_KEY_LENGTH = 40
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST = os.environ.get("EMAIL_HOST")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD")
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER")
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

DEBUG = bool(os.environ.get("DEBUG", False))

ALLOWED_HOSTS = ["idmy.team", "127.0.0.1", "localhost"]

AUTH_USER_MODEL = "idmyteamserver.Team"

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",
    "idmyteam.apps.IdmyteamConfig",
    "idmyteamserver.apps.IdmyteamserverConfig",
    "captcha",
    "simple_email_confirmation",
    "channels",
    "ws"
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "idmyteamserver.middleware.SentryMiddleware",
]

ROOT_URLCONF = "web.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            os.path.join(BASE_DIR, "idmyteam/templates"),
            os.path.join(BASE_DIR, "idmyteamserver/templates"),
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "web.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DATABASE_NAME", "idmyteam"),
        "USER": os.environ.get("DATABASE_USER", "idmyteam"),
        "PASSWORD": os.environ.get("DATABASE_PASS", "idmyteam"),
        "HOST": os.environ.get("DATABASE_HOST", "127.0.0.1"),
        "PORT": os.environ.get("DATABASE_PORT", "5432"),
        "TEST": {
            "NAME": os.environ.get("DATABASE_NAME", "idmyteam") + "_test",
        },
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.Argon2PasswordHasher",
]

# Channels
REDIS_HOST = os.environ.get("REDIS_HOST", "127.0.0.1")
REDIS_PORT = os.environ.get("REDIS_PORT", 6379)
ASGI_APPLICATION = 'idmyteamserver.routing.application'
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [(REDIS_HOST, REDIS_PORT)],
        },
    },
}

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_L10N = True

USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "static")

# sentry
sentry_sdk.init(
    dsn=os.environ.get("SENTRY_DSN"),
    integrations=[DjangoIntegration()],
    # If you wish to associate users to errors (assuming you are using
    # django.contrib.auth) you may enable sending PII data.
    send_default_pii=True,
)

# project stuff
DEFAULT_NUM_TRAINING_IMGS_PER_HOUR = 60
DEFAULT_NUM_CLASSES = 5
DEFAULT_UPLOAD_RETRY_LIMIT = 0.5
PASS_RESET_TOKEN_LEN = 200
MAX_IMG_UPLOAD_SIZE_KB = 1000
CREDENTIAL_LEN = 150
MAX_UPLOAD_SIZE = 104857600
RECAPTCHA_PUBLIC_KEY = os.environ.get("RECAPTCHA_PUBLIC_KEY")
RECAPTCHA_PRIVATE_KEY = os.environ.get("RECAPTCHA_PRIVATE_KEY")
