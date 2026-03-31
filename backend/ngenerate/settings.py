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

ENVIRONMENT = env("ENVIRONMENT", default="local")

# -------------------------------------------------
# SECURITY
# -------------------------------------------------

SECRET_KEY = env("SECRET_KEY", default="unsafe-secret-key")
DEBUG = env.bool("DEBUG", default=True)

ALLOWED_HOSTS = [
    "biometrically-towerless-yadiel.ngrok-free.dev",
    "127.0.0.1", 
    "localhost",
    "backend",
]

# -------------------------------------------------
# COSR Config
# -------------------------------------------------
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
CORS_ALLOW_CREDENTIALS = True
# CORS_ALLOW_ALL_ORIGINS = True

CORS_URLS_REGEX = r"^(?!/payments/webhook/).*$"

CORS_ALLOW_HEADERS = [
    "accept",
    "authorization",
    "content-type",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]

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
    "admin_console",
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

# DATABASES = {
#     "default": dj_database_url.config(
#         default=env("DATABASE_URL"),
#         conn_max_age=0,
#         ssl_require=True,
#     )
# }

# -------------------------------------------------
# DATABASE (PostgreSQL Docker Local)
# -------------------------------------------------

DATABASES = {
    "default": dj_database_url.config(
        default=env("DATABASE_URL"),
        conn_max_age=600,
        ssl_require=ENVIRONMENT == "production",
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
        "users.authentication.CustomJWTAuthentication",
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
# EMAIL (ส่ง OTP)
# ใช้ Gmail SMTP — ต้องเปิด App Password ใน Google Account
# https://myaccount.google.com/apppasswords
# -------------------------------------------------
 
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")      # your@gmail.com
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="") # App Password (16 ตัว)
DEFAULT_FROM_EMAIL = env("EMAIL_HOST_USER", default="noreply@ngenerate.com")
 
# -------------------------------------------------
# OTP CONFIG
# -------------------------------------------------
OTP_EXPIRE_MINUTES = env.int("OTP_EXPIRE_MINUTES", default=10)  # OTP หมดอายุใน 10 นาที
OTP_LENGTH = env.int("OTP_LENGTH", default=6)                    # OTP 6 หลัก

# -------------------------------------------------
# PAYMENTS SETTINGS
# -------------------------------------------------

PROMPTPAY_ID = env("PROMPTPAY_ID", default=None)
PAYMENTS_EXPIRE_MINUTES = env.int('PAYMENTS_EXPIRE_MINUTES', default=15)

STRIPE_PUBLIC_KEY = env("STRIPE_PUBLIC_KEY", default=None)
STRIPE_SECRET_KEY = env("STRIPE_SECRET_KEY", default=None)
STRIPE_WEBHOOK_SECRET = env("STRIPE_WEBHOOK_SECRET", default=None)

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

CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="redis://localhost:6379/0")
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'

POPPLER_PATH = env("POPPLER_PATH", default=None)

# -------------------------------------------------
# STORAGE CONFIG
# -------------------------------------------------

RUNPOD_STORAGE_ROOT = env("RUNPOD_STORAGE_ROOT", default="/workspace/ngenerate")
LOCAL_STORAGE_ROOT = env("LOCAL_STORAGE_ROOT", default=str(BASE_DIR / "storage"))

if ENVIRONMENT == "production":
    STORAGE_ROOT = RUNPOD_STORAGE_ROOT

elif ENVIRONMENT == "docker":
    STORAGE_ROOT = RUNPOD_STORAGE_ROOT

else:
    STORAGE_ROOT = LOCAL_STORAGE_ROOT


# -------------------------------------------------
# CORE STORAGE PATHS
# -------------------------------------------------

ASSET_ROOT = os.path.join(STORAGE_ROOT, env("ASSET_ROOT", default="assets"))
USER_DATA_ROOT = os.path.join(STORAGE_ROOT, env("USER_DATA_ROOT", default="user_data"))
MODEL_ROOT = os.path.join(STORAGE_ROOT, env("MODEL_ROOT", default="models"))

MASTER_VOICE_ROOT = os.path.join(ASSET_ROOT, env("MASTER_VOICE_DIR", default="master_voice"))
DEFAULT_ASSET_ROOT = os.path.join(ASSET_ROOT, env("DEFAULT_ASSET_DIR", default="defaults"))

TMP_ROOT = os.path.join(STORAGE_ROOT, "tmp")

DEFAULT_NOVEL_COVER = os.path.join(DEFAULT_ASSET_ROOT, "default_cover.jpg")
DEFAULT_AVATAR = os.path.join(DEFAULT_ASSET_ROOT, "default_avatar.jpg")

if ENVIRONMENT == "local":
    os.makedirs(STORAGE_ROOT, exist_ok=True)
    os.makedirs(ASSET_ROOT, exist_ok=True)
    os.makedirs(USER_DATA_ROOT, exist_ok=True)
    os.makedirs(MODEL_ROOT, exist_ok=True)

os.makedirs(TMP_ROOT, exist_ok=True)

# -------------------------------------------------
# MODEL PATH
# -------------------------------------------------

AI_API_URL = env("AI_API_URL", default="http://localhost:8000")
AI_TIMEOUT = env.int("TIMEOUT", default=3600)

BASE_FILE_URL=f"{AI_API_URL}/files"

SITE_URL = env("SITE_URL", default="http://localhost:8000")


# -------------------------------------------------
# MEDIA (Django)
# -------------------------------------------------

MEDIA_URL = "/media/"
MEDIA_ROOT = USER_DATA_ROOT


# -------------------------------------------------
# THREAD CONFIG
# -------------------------------------------------

GENERATION_MAX_IMAGE_WORKERS = int(os.environ.get("GENERATION_MAX_IMAGE_WORKERS", 2))
GENERATION_MAX_VOICE_WORKERS = int(os.environ.get("GENERATION_MAX_VOICE_WORKERS", 3))