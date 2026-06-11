"""Production settings — hardened SSL/HSTS/cookie + bắt buộc cấu hình secret.

Áp dụng cho mọi môi trường non-dev (staging cũng dùng).
"""
from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa
from .base import SECRET_KEY, env

DEBUG = False

# Bắt buộc SECRET_KEY thật — KHÔNG để default insecure ở prod.
if SECRET_KEY == "dev-insecure-change-me" or len(SECRET_KEY) < 32:
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY chưa được đặt hoặc quá ngắn (cần >= 32 ký tự ngẫu nhiên). "
        "Sinh bằng: python -c \"import secrets; print(secrets.token_urlsafe(64))\""
    )

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured(
        "DJANGO_ALLOWED_HOSTS phải được set ở prod (vd: crm.tencongty.vn)."
    )

# === SSL / HSTS ===
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_SECONDS = env.int("DJANGO_HSTS_SECONDS", default=60 * 60 * 24 * 30)  # 30 ngày
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = False  # bật khi đã chắc chắn không rollback HTTPS

# CSP strict prod — chỉ self + đối tác QR ngân hàng. Khi có CDN, thêm whitelist ở đây.
CSP_ENABLED = True
CSP_REPORT_ONLY = env.bool("DJANGO_CSP_REPORT_ONLY", default=False)
CSP_DIRECTIVES = {
    # Hình QR có thể nhúng từ api.vietqr.io khi đặt cọc.
    "img-src": "'self' data: blob: https://api.vietqr.io https:",
    # Cho phép FE public + PWA học viên + CRM gọi API cross-subdomain.
    "connect-src": " ".join([
        "'self'",
        env.str("SITE_PUBLIC_URL", default=""),
        env.str("SITE_STUDENT_URL", default=""),
        env.str("SITE_CRM_URL", default=""),
    ]).strip(),
    # Strict script-src: bỏ 'unsafe-inline' khỏi prod. Django admin sẽ được
    # SimpleCSPMiddleware nới riêng qua relaxed policy cho path /admin/.
    "script-src": "'self'",
}

# Path prefix vẫn cần 'unsafe-inline' (Django admin inline script).
# SimpleCSPMiddleware sẽ swap qua CSP_DIRECTIVES_RELAXED khi match.
CSP_RELAXED_PATH_PREFIXES = ("/admin/",)
CSP_DIRECTIVES_RELAXED = {
    **CSP_DIRECTIVES,
    "script-src": "'self' 'unsafe-inline'",
}

# === Cookie ===
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = False  # để JS đọc csrftoken cho XHR
CSRF_COOKIE_SAMESITE = "Lax"

# === Header bảo mật khác ===
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
X_FRAME_OPTIONS = "DENY"

# === CORS prod: whitelist subdomain ===
CORS_ALLOWED_ORIGINS = env.list(
    "DJANGO_CORS_ORIGINS",
    default=[
        env.str("SITE_PUBLIC_URL", default=""),
        env.str("SITE_STUDENT_URL", default=""),
        env.str("SITE_CRM_URL", default=""),
    ],
)
CORS_ALLOWED_ORIGINS = [u for u in CORS_ALLOWED_ORIGINS if u]
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = False  # tuyệt đối không bật ở prod

CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=CORS_ALLOWED_ORIGINS)

# === Fernet encryption: prod BẮT BUỘC có key thật, KHÔNG dùng dev default ===
if not FERNET_SECRET or FERNET_SECRET.startswith("dev-"):  # noqa: F405
    raise ImproperlyConfigured(
        "FERNET_SECRET chưa được set ở prod hoặc đang dùng dev default. "
        "Sinh key 1 lần: python -c \"from cryptography.fernet import Fernet; "
        "print(Fernet.generate_key().decode())\" rồi paste vào .env.prod. "
        "Mất key = mất toàn bộ IntegrationCredential — phải backup riêng. "
        "Xem docs/08-integration-credentials.md."
    )

# === ZNS phải cấu hình ===
ZNS_ALLOW_MOCK = False  # chặn cứng mock log OTP ra console

# === Upload limits ===
DATA_UPLOAD_MAX_NUMBER_FIELDS = 200  # chống DoS multipart spam field

# === Cache Redis (mặc định memcached/redis tùy env) ===
_REDIS_URL = env.str("REDIS_URL", default="")
if _REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": _REDIS_URL,
        }
    }

# === Email backend SMTP (override qua env) ===
EMAIL_BACKEND = env.str(
    "DJANGO_EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend"
)
EMAIL_HOST = env.str("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_HOST_USER = env.str("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env.str("EMAIL_HOST_PASSWORD", default="")

# === Logging tăng level WARN cho prod ===
LOGGING["root"]["level"] = "WARNING"  # noqa: F405
LOGGING["loggers"]["apps"]["level"] = "INFO"  # noqa: F405
LOGGING["loggers"]["django"]["level"] = "WARNING"  # noqa: F405

# === Sentry (observability, optional) ===
# Init chỉ khi SENTRY_DSN có giá trị. DSN trống → SDK no-op, không phá deploy
# khi tài khoản Sentry chưa sẵn sàng.
#
# Ràng buộc PII: send_default_pii=False bắt buộc — CCCD/SĐT/email là dữ liệu
# nhạy cảm; KHÔNG đẩy lên Sentry server. Nếu cần stack-trace có thêm context,
# dùng sentry_sdk.set_context() ở chỗ raise, lọc tay field cho phép.
SENTRY_DSN = env.str("SENTRY_DSN", default="")
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration(), CeleryIntegration()],
        traces_sample_rate=env.float("SENTRY_TRACES_SAMPLE_RATE", default=0.1),
        send_default_pii=False,
        environment=env.str("SENTRY_ENVIRONMENT", default="production"),
        release=env.str("SENTRY_RELEASE", default=""),
    )
