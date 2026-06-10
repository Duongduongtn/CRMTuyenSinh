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

# CORS thoáng hơn ở dev
CORS_ALLOW_ALL_ORIGINS = True
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
]
