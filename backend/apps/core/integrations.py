"""Loader credential cho 4 nhóm tích hợp (Casso/ZNS/FB/SMTP).

Thay flow `settings.CASSO_WEBHOOK_SECRET` bằng `get_credential("casso", "webhook_secret")`
để hỗ trợ paste key qua UI CRM SPA `/admin/integrations` (DB encrypted Fernet)
thay vì SSH `nano .env.prod`.

Priority đọc: cache (60s) → DB IntegrationCredential → settings ENV → default.

Schema provider + key được khai báo cứng ở `INTEGRATION_SCHEMA` — UI dựng form
từ schema này, không tự do paste key lạ.
"""
from __future__ import annotations

import logging
from typing import Iterable

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

CACHE_KEY_TPL = "integration_credential:{provider}:{key}"
CACHE_TTL_SECONDS = 60


# Schema: {provider: {key: (env_setting_name, label, sensitive, help_text)}}
# - env_setting_name: tên setting trong base.py để fallback nếu DB chưa có.
# - label: UI label tiếng Việt.
# - sensitive: True → API GET trả masked, False → trả nguyên (tên template, host).
# - help_text: hint cho UI.
INTEGRATION_SCHEMA: dict[str, dict[str, tuple[str, str, bool, str]]] = {
    "casso": {
        "webhook_secret": (
            "CASSO_WEBHOOK_SECRET",
            "Webhook Secret",
            True,
            "Lấy từ my.casso.vn → Tích hợp → Webhook. Dùng để verify HMAC.",
        ),
        "api_key": (
            "CASSO_API_KEY",
            "API Key",
            True,
            "Lấy từ my.casso.vn → API Token. Dùng để gọi API check giao dịch.",
        ),
    },
    "zns": {
        "access_token": (
            "ZNS_ACCESS_TOKEN",
            "Access Token",
            True,
            "Token gửi tin ZNS. TTL 7 ngày, refresh tự động dùng refresh_token.",
        ),
        "refresh_token": (
            "ZNS_REFRESH_TOKEN",
            "Refresh Token",
            True,
            "Token dùng để xin access token mới khi hết hạn.",
        ),
        "template_id_otp": (
            "ZNS_TEMPLATE_ID_OTP",
            "Template ID OTP",
            False,
            "ID template gửi mã OTP 6 chữ số (Zalo duyệt 1-3 ngày).",
        ),
        "template_id_deposit": (
            "ZNS_TEMPLATE_ID_DEPOSIT",
            "Template ID đặt cọc",
            False,
            "ID template thông báo đặt cọc thành công.",
        ),
    },
    "fb": {
        "app_secret": (
            "FB_APP_SECRET",
            "App Secret",
            True,
            "Lấy từ Meta Business App → Cài đặt → Cơ bản. Dùng verify HMAC webhook.",
        ),
        "lead_verify_token": (
            "FB_LEAD_VERIFY_TOKEN",
            "Verify Token",
            True,
            "Chuỗi random 32 ký tự tự đặt. Paste vào Meta UI để Meta GET verify.",
        ),
    },
    "smtp": {
        "host": (
            "EMAIL_HOST",
            "SMTP Host",
            False,
            "VD: smtp-relay.brevo.com",
        ),
        "port": (
            "EMAIL_PORT",
            "SMTP Port",
            False,
            "Mặc định 587 (TLS).",
        ),
        "host_user": (
            "EMAIL_HOST_USER",
            "SMTP User",
            False,
            "ID người gửi do SMTP cấp.",
        ),
        "host_password": (
            "EMAIL_HOST_PASSWORD",
            "SMTP Password",
            True,
            "Key SMTP do nhà cung cấp cấp (Brevo/Sendgrid/Mailgun).",
        ),
    },
}


def _cache_key(provider: str, key: str) -> str:
    return CACHE_KEY_TPL.format(provider=provider, key=key)


def get_credential(provider: str, key: str, default: str = "") -> str:
    """Đọc credential theo priority: cache → DB → settings ENV → default.

    Schema phải đăng ký trong `INTEGRATION_SCHEMA`. Provider+key lạ → ValueError
    ở dev để bắt typo, prod silent fallback default để không phá runtime.
    """
    schema = INTEGRATION_SCHEMA.get(provider)
    if schema is None or key not in schema:
        if settings.DEBUG:
            raise ValueError(
                f"Provider+key chưa khai báo trong INTEGRATION_SCHEMA: {provider}.{key}"
            )
        logger.warning("get_credential gọi với provider+key lạ: %s.%s", provider, key)
        return default

    ck = _cache_key(provider, key)
    cached = cache.get(ck)
    if cached is not None:
        # Empty string vẫn cache để tránh hammer DB khi credential rỗng.
        return cached or default

    # Đọc DB - bắt mọi exception (DB chưa migrate, connection lỗi) để fallback ENV.
    db_value = ""
    try:
        from .models import IntegrationCredential

        cred = IntegrationCredential.objects.filter(
            provider=provider, key=key
        ).only("value_encrypted").first()
        if cred is not None:
            db_value = cred.get_value()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Đọc IntegrationCredential thất bại (fallback ENV): %s", exc)

    if db_value:
        cache.set(ck, db_value, CACHE_TTL_SECONDS)
        return db_value

    # Fallback ENV - lấy theo schema mapping.
    env_setting_name = schema[key][0]
    env_value = getattr(settings, env_setting_name, "") or ""
    cache.set(ck, env_value, CACHE_TTL_SECONDS)
    return env_value or default


def invalidate(provider: str, key: str | None = None) -> None:
    """Xóa cache 1 key cụ thể, hoặc toàn bộ key của 1 provider."""
    schema = INTEGRATION_SCHEMA.get(provider, {})
    if key is None:
        for k in schema.keys():
            cache.delete(_cache_key(provider, k))
    else:
        cache.delete(_cache_key(provider, key))


def list_providers() -> Iterable[str]:
    return INTEGRATION_SCHEMA.keys()


def schema_for(provider: str) -> dict[str, tuple[str, str, bool, str]]:
    return INTEGRATION_SCHEMA.get(provider, {})
