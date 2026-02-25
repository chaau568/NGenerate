from pathlib import Path
from datetime import timedelta
import environ
import dj_database_url

# -------------------------------------------------
# BASE
# -------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

# -------------------------------------------------
# SECURITY
# -------------------------------------------------

SECRET_KEY = env("SECRET_KEY", default="unsafe-secret-key")
DEBUG = env.bool("DEBUG", default=True)

ALLOWED_HOSTS = []

# -------------------------------------------------
# APPLICATIONS
# -------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    
    "corsheaders",

    # Third party
    "rest_framework",
    "drf_spectacular",

    # Local apps
    "users.apps.UsersConfig",
    "payments",
    "novels.apps.NovelsConfig",
    "ngenerate_sessions",
    "asset",
    "notifications",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "ngenerate.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# -------------------------------------------------
# DATABASE (Neon PostgreSQL)
# -------------------------------------------------

DATABASES = {
    "default": dj_database_url.config(
        default=env("DATABASE_URL"),
        conn_max_age=600,
        ssl_require=True,
    )
}

# -------------------------------------------------
# AUTH
# -------------------------------------------------

AUTH_USER_MODEL = "users.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

# -------------------------------------------------
# DRF + JWT
# -------------------------------------------------

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'Ngenerate API Project',
    'DESCRIPTION': 'NGenerate Web Application',
    'VERSION': '1.0',
    'SERVE_INCLUDE_SCHEMA': False,
    
    'COMPONENT_SPLIT_PATCH': True,
    'SECURITY': [{
        'jwtAuth': [],
    }],
    'APPEND_COMPONENTS': {
        "securitySchemes": {
            "jwtAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
            }
        }
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# -------------------------------------------------
# GOOGLE OAUTH
# -------------------------------------------------

GOOGLE_CLIENT_ID = env("GOOGLE_CLIENT_ID", default=None)
GOOGLE_CLIENT_SECRET = env("GOOGLE_CLIENT_SECRET", default=None)

# -------------------------------------------------
# PAYMENTS SETTINGS
# -------------------------------------------------

PROMPTPAY_ID = env("PROMPTPAY_ID", default=None)
PAYMENTS_EXPIRE_MINUTES = env.int('PAYMENTS_EXPIRE_MINUTES', default=15)

# -------------------------------------------------
# INTERNATIONALIZATION
# -------------------------------------------------

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# -------------------------------------------------
# STATIC
# -------------------------------------------------

STATIC_URL = "static/"

# -------------------------------------------------
# Pricing Config
# -------------------------------------------------
CREDIT_CHAPTER_PER_UNIT = int(env("CREDIT_CHAPTER_PER_UNIT", default=5))
CREDIT_SENTENCE_PER_UNIT = int(env("CREDIT_SENTENCE_PER_UNIT", default=10))
CREDIT_CHARACTER_IMAGE = int(env("CREDIT_CHARACTER_IMAGE", default=5))
CREDIT_SCENE_IMAGE = int(env("CREDIT_SCENE_IMAGE", default=10))

# -------------------------------------------------
# SYSTEM EMAIL DOMAIN Config
# -------------------------------------------------
SYSTEM_EMAIL_DOMAIN = env("SYSTEM_EMAIL_DOMAIN", default="no-email.ngenerate.local")

# -------------------------------------------------
# BACKGROUND TASK Config
# -------------------------------------------------
import os

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# CELERY_BROKER_URL = 'redis://:password@vps-ip-address:6379/0'
# CELERY_RESULT_BACKEND = 'redis://:password@vps-ip-address:6379/0'
# CELERY_ACCEPT_CONTENT = ['json']
# CELERY_TASK_SERIALIZER = 'json'

# -------------------------------------------------
# MODEL Config
# -------------------------------------------------
OLLAMA_URL=env("OLLAMA_URL")
LLAMA_MODEL=env("LLAMA_MODEL")
TIMEOUT=int(env("TIMEOUT", default=900))

POPPLER_PATH = env("POPPLER_PATH", default='/usr/bin/poppler')

TTS_SERVICE_URL = env("TTS_SERVICE_URL", default='https://runpod-xxxxx.proxy.runpod.net')

# -------------------------------------------------
# COSR Config
# -------------------------------------------------
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_HEADERS = [
    "accept",
    "authorization",
    "content-type",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]