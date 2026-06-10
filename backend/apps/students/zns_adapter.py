"""Zalo ZNS adapter — gửi OTP, link đặt cọc, thông báo cho HV.

ZNS (Zalo Notification Service) cần template duyệt trước. v1 chỉ dùng template
OTP và deposit-info. Khi token ZNS chưa cấu hình hoặc template ID rỗng, adapter
chuyển sang chế độ MOCK — log OTP ra console + lưu trong DB ``sent_via=mock_dev``.
HV dev/test xem code trong admin OTPRequest hoặc Django log.

API ZNS chính thức: https://developers.zalo.me/docs/api/official-account-api/api-tin-tuc/gui-tin-otp-zns

Sprint 2 yêu cầu chỉ cần gửi được (mock OK). Sprint 3 sẽ hoàn thiện refresh
token rotation + theo dõi delivery status.
"""
from __future__ import annotations

import logging
from typing import Any

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class ZNSError(Exception):
    """Lỗi gọi API ZNS."""


def _is_mock_mode() -> bool:
    return not (settings.ZNS_ACCESS_TOKEN and settings.ZNS_TEMPLATE_ID_OTP)


def send_otp(phone: str, code: str, *, template_id: str | None = None) -> dict[str, Any]:
    """Gửi mã OTP qua ZNS template.

    Return dict với ``sent_via`` và ``meta`` để caller lưu vào ``OTPRequest.sent_meta``.
    """
    template_id = template_id or settings.ZNS_TEMPLATE_ID_OTP
    if _is_mock_mode():
        logger.warning(
            "ZNS MOCK MODE — OTP cho %s: %s (template=%s)",
            phone,
            code,
            template_id or "<chưa cấu hình>",
        )
        return {"sent_via": "mock_dev", "meta": {"mock": True, "code_logged": True}}

    url = "https://business.openapi.zalo.me/message/template"
    payload = {
        "phone": phone,
        "template_id": template_id,
        "template_data": {"otp": code},
        "tracking_id": f"otp_{phone}_{code[:2]}",
    }
    headers = {
        "access_token": settings.ZNS_ACCESS_TOKEN,
        "Content-Type": "application/json",
    }
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        data = resp.json()
    except (requests.RequestException, ValueError) as exc:
        logger.error("ZNS gửi OTP thất bại cho %s: %s", phone, exc)
        return {"sent_via": "zalo_zns_error", "meta": {"error": str(exc)}}

    if data.get("error") not in (0, "0", None):
        logger.error("ZNS API trả lỗi cho %s: %s", phone, data)
        return {"sent_via": "zalo_zns_error", "meta": data}

    return {"sent_via": "zalo_zns", "meta": data}


def send_deposit_info(
    phone: str,
    *,
    order_code: str,
    amount: int,
    bank_account: str,
    template_id: str | None = None,
) -> dict[str, Any]:
    """Gửi thông tin đặt cọc qua ZNS (Sprint 3 dùng)."""
    template_id = template_id or settings.ZNS_TEMPLATE_ID_DEPOSIT
    if _is_mock_mode() or not template_id:
        logger.warning(
            "ZNS MOCK — Thông tin cọc cho %s: order=%s amount=%s bank=%s",
            phone, order_code, amount, bank_account,
        )
        return {"sent_via": "mock_dev", "meta": {"mock": True}}
    # Implement đầy đủ ở Sprint 3
    return {"sent_via": "zalo_zns_pending", "meta": {"note": "Sprint 3"}}
