from .base import *

DEBUG = False

# WARNING: Set this to your actual production hosts
ALLOWED_HOSTS = [os.getenv('VULNOPS_PROD_HOST', '127.0.0.1')]

# CORS - Adjust to specific production frontend URL in env
CORS_ALLOWED_ORIGINS = [
    os.getenv('FRONTEND_URL_PROD', 'https://your-production-frontend.com'),
]
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# CSRF
CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS

CSRF_COOKIE_SECURE = True  # Enforce HTTPS
CSRF_COOKIE_HTTPONLY = False  # Allows JS to read token if needed
CSRF_COOKIE_SAMESITE = 'Lax'
