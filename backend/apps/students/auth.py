"""JWT token cho học viên — auth = SĐT + 6 số cuối CCCD (chốt 2026-06-11).

Dùng HMAC-SHA256 trên SECRET_KEY Django, payload nhỏ, không phụ thuộc lib bên ngoài
(PyJWT). Khi cần refresh token rotation phức tạp hơn có thể chuyển sang
``djangorestframework-simplejwt`` sau.

- ``access`` token: 15 phút.
- ``refresh`` token: 7 ngày (giảm từ 30 ngày để bù entropy 6 số cuối CCCD thấp
  hơn OTP 6 số, theo [[student-auth-flow]]).
- ``quick`` token: 24 giờ — văn thư CRM gen + copy link gửi tay cho HV (Zalo
  tay/SMS tay/gọi điện). Scope cứng 1 enrollment, read-only.

Payload:
```
{
  "sub": <student_account_id>,
  "phone": "0903...",
  "type": "access" | "refresh" | "quick",
  "enrollment": <id> | null,   # chỉ với quick token
  "exp": <unix_ts>,
  "iat": <unix_ts>,
  "jti": <random_hex>,         # rotation tracking (TODO Sprint 3)
}
```
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass
from typing import Any

from django.conf import settings


ACCESS_TTL_SECONDS = 15 * 60
REFRESH_TTL_SECONDS = 7 * 24 * 60 * 60
QUICK_TTL_SECONDS = 24 * 60 * 60


class TokenError(Exception):
    """Token không hợp lệ, hết hạn, hoặc sai signature."""


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    pad = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + pad)


def _sign(payload_b64: str) -> str:
    secret = settings.SECRET_KEY.encode("utf-8")
    sig = hmac.new(secret, payload_b64.encode("ascii"), hashlib.sha256).digest()
    return _b64url_encode(sig)


def _make_token(payload: dict[str, Any]) -> str:
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    sig = _sign(payload_b64)
    return f"{payload_b64}.{sig}"


def issue_access_token(account_id: int, phone: str) -> str:
    now = int(time.time())
    return _make_token({
        "sub": account_id,
        "phone": phone,
        "type": "access",
        "iat": now,
        "exp": now + ACCESS_TTL_SECONDS,
        "jti": secrets.token_hex(8),
    })


def issue_refresh_token(account_id: int, phone: str) -> str:
    now = int(time.time())
    return _make_token({
        "sub": account_id,
        "phone": phone,
        "type": "refresh",
        "iat": now,
        "exp": now + REFRESH_TTL_SECONDS,
        "jti": secrets.token_hex(8),
    })


def issue_quick_token(account_id: int, phone: str, enrollment_id: int) -> str:
    """Link xem nhanh 24h — văn thư CRM gen + copy gửi tay. Scope 1 enrollment."""
    now = int(time.time())
    return _make_token({
        "sub": account_id,
        "phone": phone,
        "type": "quick",
        "enrollment": enrollment_id,
        "iat": now,
        "exp": now + QUICK_TTL_SECONDS,
        "jti": secrets.token_hex(8),
    })


def decode_token(token: str, *, expected_type: str | None = None) -> dict[str, Any]:
    """Verify signature + exp; return payload dict. Raise ``TokenError`` nếu invalid."""
    if not token or "." not in token:
        raise TokenError("Token không đúng định dạng.")
    payload_b64, sig = token.split(".", 1)
    expected_sig = _sign(payload_b64)
    if not hmac.compare_digest(expected_sig, sig):
        raise TokenError("Chữ ký token sai.")
    try:
        payload = json.loads(_b64url_decode(payload_b64))
    except Exception as exc:
        raise TokenError(f"Payload không decode được: {exc}") from exc

    if int(payload.get("exp", 0)) < int(time.time()):
        raise TokenError("Token hết hạn.")
    if expected_type and payload.get("type") != expected_type:
        raise TokenError(f"Loại token không khớp (cần {expected_type}, có {payload.get('type')}).")
    return payload


@dataclass
class StudentAuthPayload:
    account_id: int
    phone: str
    token_type: str
    enrollment_id: int | None = None
