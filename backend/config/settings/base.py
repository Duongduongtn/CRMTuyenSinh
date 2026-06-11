"""Common settings — dev/prod kế thừa từ file này."""
from pathlib import Path

import environ
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
env_file = BASE_DIR / ".env"
if env_file.exists():
    env.read_env(str(env_file))

SECRET_KEY = env.str("DJANGO_SECRET_KEY", default="dev-insecure-change-me")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

# Custom config
BASE_DOMAIN = env.str("BASE_DOMAIN", default="tencongty.vn")
SITE_PUBLIC_URL = env.str("SITE_PUBLIC_URL", default="http://localhost:3000")
SITE_STUDENT_URL = env.str("SITE_STUDENT_URL", default="http://localhost:3001")
SITE_CRM_URL = env.str("SITE_CRM_URL", default="http://localhost:8000")

INSTALLED_APPS = [
    # django-unfold MUST come BEFORE django.contrib.admin
    "unfold",
    "unfold.contrib.filters",
    "unfold.contrib.forms",
    "unfold.contrib.import_export",
    # Django core
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "django_filters",
    "corsheaders",
    "solo",
    # Local apps
    "apps.core",
    "apps.users",
    "apps.courses",
    "apps.leads",
    "apps.orders",
    "apps.payments",
    "apps.students",
    "apps.documents",
    "apps.blog",
    "apps.marketing",
    "apps.reports",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Audit phải đặt SAU AuthenticationMiddleware để get_current_request().user đã có.
    "apps.core.middleware.AuditContextMiddleware",
    # CSP cuối chain để bao mọi response (kể cả admin + API).
    "apps.core.middleware.SimpleCSPMiddleware",
]

# CSP defaults (dev có thể override). Prod set strict trong settings/prod.py.
CSP_ENABLED = True
CSP_REPORT_ONLY = False
CSP_DIRECTIVES = {}

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.template.context_processors.debug",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# Database — mặc định SQLite cho dev nhanh, dùng env DATABASE_URL để switch sang Postgres
DATABASE_URL = env.str("DATABASE_URL", default="")
if DATABASE_URL:
    DATABASES = {"default": dj_database_url.parse(DATABASE_URL, conn_max_age=600)}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# Auth
AUTH_USER_MODEL = "users.User"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LOGIN_URL = "/admin/login/"
LOGIN_REDIRECT_URL = "/admin/"

# Locale (Vietnam)
LANGUAGE_CODE = "vi"
TIME_ZONE = "Asia/Ho_Chi_Minh"
USE_I18N = True
USE_TZ = True
LANGUAGES = [("vi", "Tiếng Việt"), ("en", "English")]

# Static + Media
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"] if (BASE_DIR / "static").exists() else []
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# CORS — SPA CRM cần credentials để gửi session cookie + CSRF
CORS_ALLOWED_ORIGINS = [
    SITE_PUBLIC_URL,
    SITE_STUDENT_URL,
    SITE_CRM_URL,
]
CORS_ALLOW_CREDENTIALS = True

# REST Framework
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
    "DATETIME_FORMAT": "%Y-%m-%dT%H:%M:%S%z",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/minute",
        "user": "300/minute",
        "lead_capture": "30/hour",   # chống spam form
        "deposit_link": "30/minute", # chống enum đơn qua public deposit endpoint
        # Login học viên (SĐT + 6 số cuối CCCD) — entropy 10^6 + lock cứng ở model.
        "student_login_phone_hour": "10/hour",  # 10 lần/giờ/SĐT
        "student_login_phone_day": "30/day",    # 30 lần/ngày/SĐT
        "student_login_ip": "60/hour",          # 60 lần/giờ/IP chống scan
        "delete_request": "5/hour",  # 5 yêu cầu xóa dữ liệu/giờ/account
        "report_export": "10/hour",  # 10 lần export Excel/giờ/user — chống DoS gen file
    },
}

# File upload limits
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024 + 256 * 1024  # 5MB + buffer headers
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
DATA_UPLOAD_MAX_NUMBER_FIELDS = 200  # chống DoS multipart spam field

# Chỉ honor X-Forwarded-For khi đứng sau proxy đáng tin (nginx ở prod).
# Dev thường truy cập trực tiếp, để mặc định False tránh client forge IP audit.
TRUST_X_FORWARDED_FOR = env.bool("TRUST_X_FORWARDED_FOR", default=False)

# Celery
CELERY_BROKER_URL = env.str("CELERY_BROKER_URL", default="") or env.str("REDIS_URL", default="memory://")
CELERY_RESULT_BACKEND = env.str("REDIS_URL", default="cache+memory://")
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=False)
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True

# Celery beat schedule — đăng ký task chạy theo cron.
# Override interval qua env nếu cần (vd test cho chạy 30s).
CELERY_BEAT_SCHEDULE = {
    "reconcile-pending-payments": {
        "task": "apps.payments.reconcile_pending_payments",
        # Mặc định 5 phút/lần (300s). Override qua CELERY_RECONCILE_INTERVAL_SECONDS.
        "schedule": env.int("CELERY_RECONCILE_INTERVAL_SECONDS", default=300),
        "kwargs": {"lookback_hours": env.int("CELERY_RECONCILE_LOOKBACK_HOURS", default=24)},
        "options": {"expires": 240},  # hết hạn trước lần kế (tránh task chồng nhau)
    },
    "purge-expired-documents": {
        # Quét xóa CCCD/sức khỏe quá 90 ngày theo NĐ 13/2023.
        # Mặc định 6h/lần (đủ để purge kịp, không nặng DB).
        "task": "apps.documents.purge_expired_documents",
        "schedule": env.int("CELERY_PURGE_DOCS_INTERVAL_SECONDS", default=6 * 60 * 60),
        "options": {"expires": 5 * 60 * 60},
    },
}

# Cache (default in-memory, override prod sang Redis)
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "crm-default",
    }
}

# Logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name} | {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "apps": {"handlers": ["console"], "level": "DEBUG", "propagate": False},
    },
}

# django-unfold theme
UNFOLD = {
    "SITE_TITLE": "CRM Tuyển Sinh",
    "SITE_HEADER": "CRM Tuyển Sinh Học Lái Xe",
    "SITE_SUBHEADER": "Quản lý lead, đơn hàng, hồ sơ học viên",
    "SITE_SYMBOL": "school",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,
    "COLORS": {
        "primary": {
            "50": "240 253 244",
            "100": "220 252 231",
            "200": "187 247 208",
            "300": "134 239 172",
            "400": "74 222 128",
            "500": "34 197 94",
            "600": "22 163 74",
            "700": "21 128 61",
            "800": "22 101 52",
            "900": "20 83 45",
            "950": "5 46 22",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": True,
    },
}

# Fernet encryption cho IntegrationCredential (key paste qua UI CRM SPA, lưu
# vào DB mã hóa thay cho SSH paste .env.prod). Sinh key 1 lần:
#   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Dev default key cố định để test/migrate chạy không cần ENV. Prod BẮT BUỘC override.
FERNET_SECRET = env.str(
    "FERNET_SECRET",
    default="dev-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA0=",  # noqa: S105 - dev only, prod override
)
# Cho phép rotation: list base64 keys cũ (csv) để MultiFernet thử decrypt fallback.
FERNET_SECRET_OLD = env.str("FERNET_SECRET_OLD", default="")

# External integrations
TELEGRAM_BOT_TOKEN = env.str("TELEGRAM_BOT_TOKEN", default="")
TELEGRAM_CHAT_ID = env.str("TELEGRAM_CHAT_ID", default="")
CASSO_WEBHOOK_SECRET = env.str("CASSO_WEBHOOK_SECRET", default="")
CASSO_API_KEY = env.str("CASSO_API_KEY", default="")
# ZNS_* + SMTP đã bị loại khỏi MVP ở Sprint 3 Tuần 7 (2026-06-11 gói A + 2026-06-12
# gói B). Auth học viên chuyển sang SĐT + 6 số cuối CCCD. Không cấu hình lại.

# Facebook Lead Ads webhook
FB_APP_SECRET = env.str("FB_APP_SECRET", default="")
FB_LEAD_VERIFY_TOKEN = env.str("FB_LEAD_VERIFY_TOKEN", default="")
# Dev-only: bỏ qua signature verify khi chưa có FB_APP_SECRET. KHÔNG bật ở prod.
FB_ALLOW_INSECURE_DEV = env.bool("FB_ALLOW_INSECURE_DEV", default=False)
