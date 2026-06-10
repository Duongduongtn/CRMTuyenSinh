"""Dev settings — chạy local."""
from .base import *  # noqa

DEBUG = True
ALLOWED_HOSTS = ["*"]

# Debug Toolbar
INSTALLED_APPS += [  # noqa: F405
    "debug_toolbar",
    "django_extensions",
]

MIDDLEWARE = [  # noqa: F405
    "debug_toolbar.middleware.DebugToolbarMiddleware",
] + MIDDLEWARE  # type: ignore  # noqa: F405

INTERNAL_IPS = ["127.0.0.1", "localhost"]

# Email backend dev: in ra console
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Celery: chạy đồng bộ trong dev nếu không có Redis
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# CORS thoáng hơn ở dev — nhưng KHÔNG dùng CORS_ALLOW_ALL_ORIGINS=True vì
# kèm CORS_ALLOW_CREDENTIALS=True sẽ bị browser block. Whitelist localhost:5173 (Vite CRM).
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [  # noqa: F405
    "http://localhost:3000",   # FE public Nuxt
    "http://localhost:3001",   # FE student PWA
    "http://localhost:5173",   # FE CRM Vue + Vite default
    "http://localhost:5174",   # Vite fallback nếu 5173 bận
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "http://127.0.0.1:5173",
]
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:5173",
    "http://localhost:5174",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "http://127.0.0.1:5173",
]

# Session cookie cho SPA dev: SameSite=Lax đủ vì cùng site (localhost).
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = False  # để axios đọc csrftoken cookie
