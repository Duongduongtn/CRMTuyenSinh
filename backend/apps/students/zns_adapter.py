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

from apps.core.integrations import get_credential

logger = logging.getLogger(__name__)


class ZNSError(Exception):
    """Lỗi gọi API ZNS."""


def _is_mock_mode() -> bool:
    """Mock khi access_token hoặc template OTP rỗng (DB + ENV đều thiếu)."""
    return not (
        get_credential("zns", "access_token")
        and get_credential("zns", "template_id_otp")
    )


def _mask_phone(phone: str) -> str:
    """Mask SĐT cho log: 0903456789 → 0903***789."""
    if not phone or len(phone) < 7:
        return "***"
    return phone[:4] + "***" + phone[-3:]


def send_otp(phone: str, code: str, *, template_id: str | None = None) -> dict[str, Any]:
    """Gửi mã OTP qua ZNS template.

    Return dict với ``sent_via`` và ``meta`` để caller lưu vào ``OTPRequest.sent_meta``.
    KHÔNG bao giờ log plain code ở prod — chỉ dev/test với DJANGO_DEBUG=True
    hoặc ZNS_ALLOW_MOCK=True mới in code thuần.
    """
    template_id = template_id or get_credential("zns", "template_id_otp")
    if _is_mock_mode():
        # Chặn cứng prod: nếu không DEBUG và không cho phép mock → raise ngay.
        allow_mock = getattr(settings, "ZNS_ALLOW_MOCK", False) or settings.DEBUG
        if not allow_mock:
            logger.error(
                "ZNS chưa cấu hình ở môi trường production (phone=%s).",
                _mask_phone(phone),
            )
            raise ZNSError(
                "Dịch vụ gửi mã OTP chưa được cấu hình. Vui lòng liên hệ tư vấn viên."
            )
        # Dev/test: log code thuần để debug, kèm cảnh báo rõ.
        logger.warning(
            "ZNS MOCK MODE (dev only) — OTP cho %s: %s",
            _mask_phone(phone),
            code,
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
        "access_token": get_credential("zns", "access_token"),
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
    template_id = template_id or get_credential("zns", "template_id_deposit")
    if _is_mock_mode() or not template_id:
        logger.warning(
            "ZNS MOCK — Thông tin cọc cho %s: order=%s amount=%s bank=%s",
            phone, order_code, amount, bank_account,
        )
        return {"sent_via": "mock_dev", "meta": {"mock": True}}
    # Implement đầy đủ ở Sprint 3
    return {"sent_via": "zalo_zns_pending", "meta": {"note": "Sprint 3"}}
