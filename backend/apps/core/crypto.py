"""Fernet symmetric encryption wrapper cho IntegrationCredential.

Fernet = AES-128-CBC + HMAC-SHA256 + timestamp + base64. Spec:
https://cryptography.io/en/latest/fernet/

Key seed qua `settings.FERNET_SECRET` (URL-safe base64, 32 bytes). Mất key này
== mất toàn bộ credential trong DB → phải backup riêng.

Rotation: khi đổi key, đọc DB bằng MultiFernet([new, old]) → re-encrypt sang new
→ remove old. Doc: docs/08-integration-credentials.md.
"""
from __future__ import annotations

import logging

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)

_CIPHER = None


def _build_cipher():
    """Lazy build Fernet cipher từ settings.FERNET_SECRET.

    Raise ImproperlyConfigured nếu key thiếu hoặc sai format. Caller chịu trách
    nhiệm catch nếu muốn fallback graceful (vd loader fallback ENV).
    """
    from cryptography.fernet import Fernet, MultiFernet

    primary = getattr(settings, "FERNET_SECRET", "") or ""
    if not primary:
        raise ImproperlyConfigured(
            "FERNET_SECRET chưa được cấu hình. Sinh key 1 lần:\n"
            "  python -c \"from cryptography.fernet import Fernet; "
            "print(Fernet.generate_key().decode())\"\n"
            "rồi paste vào .env.prod (hoặc .env dev)."
        )

    # MultiFernet hỗ trợ rotation - đọc thêm FERNET_SECRET_OLD (csv) nếu có.
    extra = getattr(settings, "FERNET_SECRET_OLD", "") or ""
    keys = [primary]
    if extra:
        keys.extend(k.strip() for k in extra.split(",") if k.strip())

    try:
        ciphers = [Fernet(k.encode() if isinstance(k, str) else k) for k in keys]
    except Exception as exc:  # noqa: BLE001
        raise ImproperlyConfigured(
            f"FERNET_SECRET không hợp lệ (cần URL-safe base64, 32 bytes): {exc}"
        ) from exc

    if len(ciphers) == 1:
        return ciphers[0]
    return MultiFernet(ciphers)


def get_cipher():
    """Trả về Fernet instance singleton (cache process-level)."""
    global _CIPHER
    if _CIPHER is None:
        _CIPHER = _build_cipher()
    return _CIPHER


def reset_cipher_cache() -> None:
    """Reset singleton — dùng trong test để swap FERNET_SECRET."""
    global _CIPHER
    _CIPHER = None


def encrypt_str(plaintext: str) -> bytes:
    """Encrypt UTF-8 string. Empty string → empty bytes (không encrypt)."""
    if not plaintext:
        return b""
    return get_cipher().encrypt(plaintext.encode("utf-8"))


def decrypt_to_str(ciphertext: bytes) -> str:
    """Decrypt bytes → UTF-8 string. Empty bytes → empty string."""
    if not ciphertext:
        return ""
    try:
        return get_cipher().decrypt(bytes(ciphertext)).decode("utf-8")
    except Exception as exc:  # noqa: BLE001
        # InvalidToken khi key đổi mà chưa rotate, hoặc data hỏng.
        logger.error("Decrypt credential thất bại: %s", exc)
        return ""
