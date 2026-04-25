import os
import environ
from pathlib import Path

# 1. Initialize environment variables
env = environ.Env(
    DEBUG=(bool, False),
    DATABASE_URL=(str, None),
    SECURE_SSL_REDIRECT=(bool, False),
    SESSION_COOKIE_SECURE=(bool, False),
    CSRF_COOKIE_SECURE=(bool, False),
    SECURE_HSTS_SECONDS=(int, 0),
    SECURE_HSTS_INCLUDE_SUBDOMAINS=(bool, False),
    SECURE_HSTS_PRELOAD=(bool, False),
)

# 2. Build paths inside the project
# BASE_DIR is the 'backend' folder
BASE_DIR = Path(__file__).resolve().parent.parent

# 3. Read the .env file from the backend directory
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

# 4. Security settings loaded from .env
SECRET_KEY = env('SECRET_KEY')
DEBUG = env.bool('DEBUG', default=False)
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS')

# 5. Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third-party apps
    'rest_framework',
    'django_filters',
    'corsheaders',
    'cloudinary',
    'cloudinary_storage',

    # Project apps
    'api',
    'accounts',
    'patients',
    'appointments',
    'prescriptions',
    'billing',
    'publications',
    'audit',
]

# 6. Middleware configuration (Order matters for Auth/Admin)
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',    # ← serves static files in production
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'audit.middleware.AuditUserMiddleware',          # ← captures request.user for signals
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

# 7. Templates configuration (linked to frontend/templates)
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR.parent / 'frontend' / 'templates'], # Points to ProClinic/frontend/templates
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

# 8. Database configuration
# If DATABASE_URL is set (e.g. in Docker), use PostgreSQL; otherwise use SQLite.
_database_url = env('DATABASE_URL', default=None)
if _database_url:
    DATABASES = {
        'default': env.db_url('DATABASE_URL')
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# 9. Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# 10. Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

# 11. Static files configuration (linked to frontend/static)
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR.parent / 'frontend' / 'static',  # Points to ProClinic/frontend/static
]
# Django 4.2+ / 6.x: use STORAGES dict instead of the removed STATICFILES_STORAGE setting.
# WhiteNoise CompressedManifestStaticFilesStorage gzips + fingerprint-hashes every asset.
# Default file storage: Cloudinary when credentials are present, local filesystem otherwise.
_CLOUDINARY_CONFIGURED = bool(
    os.environ.get('CLOUDINARY_CLOUD_NAME') and
    os.environ.get('CLOUDINARY_API_KEY') and
    os.environ.get('CLOUDINARY_API_SECRET')
)
STORAGES = {
    'default': {
        'BACKEND': (
            'cloudinary_storage.storage.MediaCloudinaryStorage'
            if _CLOUDINARY_CONFIGURED
            else 'django.core.files.storage.FileSystemStorage'
        ),
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# new models
AUTH_USER_MODEL = 'accounts.CustomUser'

# Media files (Uploaded PDFs, images, etc.)
# On Render free tier (no persistent disk), media is stored in Cloudinary.
# Locally, files are stored inside the project tree when Cloudinary creds are absent.
IS_RENDER = os.environ.get('RENDER', '') == 'true'
MEDIA_URL = '/media/'  # Still used by templates / local dev; Cloudinary ignores it for URLs.

# Cloudinary configuration — injected via environment variables.
# If any var is missing the STORAGES 'default' backend falls back to FileSystemStorage.
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': os.environ.get('CLOUDINARY_CLOUD_NAME', ''),
    'API_KEY':    os.environ.get('CLOUDINARY_API_KEY', ''),
    'API_SECRET': os.environ.get('CLOUDINARY_API_SECRET', ''),
}

# Local MEDIA_ROOT: only used when Cloudinary is NOT configured.
MEDIA_ROOT = BASE_DIR / 'media'
try:
    MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
except Exception:
    pass  # Non-fatal; Cloudinary storage does not use MEDIA_ROOT.

# 12. Password Hashing (Argon2 as per PRD)
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
]

# 13. Django REST Framework Settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    # ── Filtering / Search / Ordering ─────────────────────────────────────
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    # ── Pagination ────────────────────────────────────────────────────────
    'DEFAULT_PAGINATION_CLASS': 'api.pagination.StandardResultsSetPagination',
    'PAGE_SIZE': 20,
}

# 14. SimpleJWT Settings
from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# 15. Authentication redirects for session-based login
LOGIN_URL = '/accounts/choose-login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/accounts/choose-login/'

# 16. Financial / Clinic Configs
CONSULTATION_FEE = env('CONSULTATION_FEE', default='500.00')
GST_RATE = env('GST_RATE', default='0.18')

# 17. CORS Config
CORS_ALLOW_ALL_ORIGINS = True

# 18. Static root (collectstatic writes here; WhiteNoise serves from here)
STATIC_ROOT = BASE_DIR / 'staticfiles'

# 19. Production security settings
# All values are injected by Render env vars; defaults are safe for local dev.
CSRF_TRUSTED_ORIGINS           = env.list('CSRF_TRUSTED_ORIGINS',           default=[])
if not any('onrender.com' in origin for origin in CSRF_TRUSTED_ORIGINS):
    CSRF_TRUSTED_ORIGINS.append('https://*.onrender.com')

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT            = env.bool('SECURE_SSL_REDIRECT',            default=False)
SESSION_COOKIE_SECURE          = env.bool('SESSION_COOKIE_SECURE',          default=False)
CSRF_COOKIE_SECURE             = env.bool('CSRF_COOKIE_SECURE',             default=False)
SECURE_HSTS_SECONDS            = env.int( 'SECURE_HSTS_SECONDS',            default=0)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool('SECURE_HSTS_INCLUDE_SUBDOMAINS', default=False)
SECURE_HSTS_PRELOAD            = env.bool('SECURE_HSTS_PRELOAD',            default=False)

# 20. Logging — streams to stdout so Render's log viewer captures everything
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
        'accounts': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}
