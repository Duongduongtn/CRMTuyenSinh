"""Helper mask PII cho log/Telegram/Sentry tuân thủ NĐ 13/2023.

Reuse cho:
- Telegram task (apps/payments/tasks.py) — mask SĐT trong message.
- AuditLog (apps/core/views.py) — mask bank_account_number/bank_account_name.
- Sentry before_send hook (config/settings/prod.py) — scrub PII khỏi event.
- fix_orphan_accounts command (apps/students/management/commands/).

Mở rộng: thêm key vào SENSITIVE_KEYS khi có field mới chứa PII (CMND mới, GPLX
serial, biển số xe nếu cần). Mỗi field thêm thành extension point — KHÔNG
hard-code regex/policy ngoài file này.
"""
from __future__ import annotations

from typing import Any

# Field/key tên chứa PII cần strip toàn bộ value khi log/event.
# Khi thêm key mới, cập nhật memory `[[masking-keys-policy]]` để team biết.
# Phạm vi NĐ 13/2023 Điều 2: thông tin cá nhân cơ bản (định danh, liên lạc, địa
# chỉ, ngày sinh) + secret/credential. Tên cá nhân (full_name) giữ nguyên cho
# debug Sentry — KHÔNG phải secret + không cấm xử lý theo NĐ 13.
SENSITIVE_KEYS: frozenset[str] = frozenset({
    # Định danh cá nhân (NĐ 13/2023 Điều 2)
    "phone", "phone_number", "student_phone", "sdt", "mobile",
    "cccd", "cccd_number", "id_number", "id_card", "national_id",
    "cccd_front", "cccd_back",
    # Liên lạc cá nhân (NĐ 13/2023 Điều 2.5)
    "email", "student_email", "user_email", "lead_email",
    # Ngày sinh (NĐ 13/2023)
    "date_of_birth", "dob", "birthday",
    # Địa chỉ (NĐ 13/2023)
    "address", "permanent_address", "current_address", "address_line",
    # Thanh toán
    "bank_account_number", "bank_account_name",
    # Secret / credential
    "password", "secret", "token", "api_key", "webhook_secret",
    "access_token", "refresh_token", "app_secret",
    "fernet_secret", "fernet_secret_old", "student_jwt_secret",
    "django_secret_key",
})


def mask_phone(phone: str | None) -> str:
    """SĐT VN 10 số → giữ 3 đầu + 4 dấu sao + 3 cuối: `0903111222` → `090****222`."""
    if not phone or len(phone) < 7:
        return "***"
    return phone[:3] + "****" + phone[-3:]


def mask_cccd(cccd: str | None) -> str:
    """CCCD/CMND → giữ 4 cuối: `036123456789` → `********6789`."""
    if not cccd or len(cccd) < 5:
        return "***"
    return "*" * (len(cccd) - 4) + cccd[-4:]


def scrub_sentry_pii(event: dict[str, Any], _hint: dict[str, Any]) -> dict[str, Any] | None:
    """Sentry `before_send` hook strip PII khỏi event trước khi gửi server.

    Lý do tồn tại: `send_default_pii=False` của Sentry SDK chỉ loại `request.user.email`
    + IP. KHÔNG strip `request.data` / `request.json` / form body chứa phone, CCCD
    upload, bank info. NĐ 13/2023 quy định không lộ data nhạy cảm ra dịch vụ thứ 3
    (Sentry server hosted bên Mỹ/EU).

    Recursive scrub mọi dict/list trong event chứa key thuộc `SENSITIVE_KEYS` → "***".
    Trả về event đã scrub (Sentry SDK gửi tiếp). Trả None để DROP event hoàn toàn —
    không dùng ở đây (giữ stack trace + log message kỹ thuật).
    """
    if not event:
        return event
    return _scrub_dict(event)


def _scrub_dict(obj: Any) -> Any:
    """Đệ quy scrub mọi key thuộc SENSITIVE_KEYS trong nested dict/list."""
    if isinstance(obj, dict):
        return {
            key: ("***" if key.lower() in SENSITIVE_KEYS else _scrub_dict(value))
            for key, value in obj.items()
        }
    if isinstance(obj, list):
        return [_scrub_dict(item) for item in obj]
    return obj
