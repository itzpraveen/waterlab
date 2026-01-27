"""
Production settings for Water Lab LIMS.

This module is intended for real deployments and therefore must *not* ship
with insecure fallbacks. All critical secrets should be provided via env.
"""

import os
import sys
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
_BUILD_TIME_COMMANDS = {'collectstatic', 'check'}
_is_build_time = any(cmd in sys.argv for cmd in _BUILD_TIME_COMMANDS)

SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    if _is_build_time:
        # Allow Docker build steps (e.g., collectstatic) to run without secrets.
        SECRET_KEY = 'insecure-build-time-key'
    else:
        raise ImproperlyConfigured("SECRET_KEY must be set via environment variable in production.")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'

# Domain configuration: prefer explicit ALLOWED_HOSTS, else derive from DOMAIN_NAME/SERVER_IP.
allowed_hosts_env = os.environ.get('ALLOWED_HOSTS')
if allowed_hosts_env:
    ALLOWED_HOSTS = [h.strip() for h in allowed_hosts_env.split(',') if h.strip()]
else:
    ALLOWED_HOSTS = []
    for host in (
        os.environ.get('DOMAIN_NAME'),
        os.environ.get('SERVER_IP'),
        'localhost',
        '127.0.0.1',
    ):
        if host and host not in ALLOWED_HOSTS:
            ALLOWED_HOSTS.append(host)
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured("ALLOWED_HOSTS must be set for production.")

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core',
]

# Custom User Model
AUTH_USER_MODEL = 'core.CustomUser'

# Login/Logout URLs
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # For static files in production
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'waterlab.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.lab_profile',
            ],
        },
    },
]

WSGI_APPLICATION = 'waterlab.wsgi.application'

# Database - PostgreSQL Production Configuration
db_password = os.environ.get('DB_PASSWORD')
if not db_password:
    if _is_build_time:
        # Static collection during Docker build doesn't require DB access.
        db_password = ''
    else:
        raise ImproperlyConfigured("DB_PASSWORD must be set via environment variable in production.")

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'waterlab'),
        'USER': os.environ.get('DB_USER', 'waterlab'),
        'PASSWORD': db_password,
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
        'OPTIONS': {
            'connect_timeout': 20,
            'options': '-c default_transaction_isolation=serializable'
        },
        'CONN_MAX_AGE': 600,  # Connection pooling
    }
}

# Redis Cache (Optional - for production performance)
# CACHES = {
#     'default': {
#         'BACKEND': 'django_redis.cache.RedisCache',
#         'LOCATION': 'redis://127.0.0.1:6379/1',
#         'OPTIONS': {
#             'CLIENT_CLASS': 'django_redis.client.DefaultClient',
#         }
#     }
# }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'  # Indian Standard Time
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# Media files (User uploads)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / "media"

# WhiteNoise for static files in production
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Security Settings for Production
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_REDIRECT_EXEMPT = []
    SECURE_SSL_REDIRECT = False  # Set to True if using HTTPS
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    USE_TZ = True

# Accept common day-first and ISO datetime inputs across environments
DATETIME_INPUT_FORMATS = [
    '%d/%m/%Y %H:%M:%S', '%d/%m/%Y %H:%M', '%d/%m/%Y',
    '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d',
]

# Seed standard parameters automatically when the DB is empty
AUTO_SEED_PARAMETERS = True

# Session Security
SESSION_COOKIE_SECURE = False  # Set to True if using HTTPS
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = 3600  # 1 hour
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# CSRF Protection
CSRF_COOKIE_SECURE = False  # Set to True if using HTTPS
CSRF_COOKIE_HTTPONLY = True

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'waterlab.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'core': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}

# Email Configuration for Production
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = 'Water Lab LIMS <noreply@waterlab.com>'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Application-specific settings
WATERLAB_SETTINGS = {
    'LAB_NAME': 'Kerala Water Testing Laboratory',
    'LAB_ADDRESS': 'Thiruvananthapuram, Kerala, India',
    'LAB_PHONE': '+91-471-XXXXXXX',
    'LAB_EMAIL': 'info@keralawatertesting.com',
    'ACCREDITATION_NUMBER': 'NABL-123456',
    'REPORT_VALIDITY_DAYS': 30,
    'MAX_SAMPLES_PER_BATCH': 50,
    'BACKUP_RETENTION_DAYS': 365,
    'TEXT_RESULT_STATUS_OVERRIDES': {
        'global': {
            'BDL': 'WITHIN_LIMITS',
        },
    },
    'INVOICE_PRICING': {
        'CHEMICAL': 400,
        'MICROBIOLOGICAL': 500,
        'FULL': 900,
    },
    'INVOICE_DESCRIPTIONS': {
        'CHEMICAL': 'Chemical Test',
        'MICROBIOLOGICAL': 'Microbiological Test',
        'FULL': 'Water Quality Test Report',
        'FALLBACK': 'Water Quality Test Report',
    },
    'PAYMENT_OPTIONS': {
        'ACCOUNT_NAME': 'BIOFIX TECHNOLOGY LLP',
        'ACCOUNT_NUMBER': '25150200002107',
        'BANK_NAME': 'FEDERAL BANK',
        'IFSC': 'FDRL0002515',
        'PHONE': '7510510946',
    },
    'CURRENCY_SYMBOL': '₹',
}
