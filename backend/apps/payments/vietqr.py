"""VietQR generator — sinh URL ảnh QR code chuẩn NAPAS.

Dùng dịch vụ free của vietqr.io: trả về URL ảnh, FE chỉ cần <img src=...>.
Format URL: https://img.vietqr.io/image/{BANK}-{ACC}-{TEMPLATE}.png?amount=&addInfo=&accountName=

Brand info (bank_code, account_number, account_name) đọc từ
``apps.core.models.SiteSettings`` — KHÔNG hard-code.
"""
from __future__ import annotations

from decimal import Decimal
from urllib.parse import quote, urlencode

from apps.core.models import SiteSettings


VIETQR_BASE_URL = "https://img.vietqr.io/image"
DEFAULT_TEMPLATE = "compact2"  # template QR có sẵn label và số tiền hiển thị


def build_vietqr_url(
    *,
    amount: Decimal | int,
    add_info: str,
    bank_code: str | None = None,
    account_number: str | None = None,
    account_name: str | None = None,
    template: str = DEFAULT_TEMPLATE,
) -> str:
    """Sinh URL VietQR.

    Nếu thiếu bank_code/account_number/account_name, đọc từ SiteSettings.
    Raise ValueError nếu SiteSettings cũng trống — admin chưa cấu hình ngân hàng.
    """
    site = SiteSettings.get_solo()
    bank_code = (bank_code or site.bank_code or "").strip().upper()
    account_number = (account_number or site.bank_account_number or "").strip()
    account_name = (account_name or site.bank_account_name or "").strip()

    if not bank_code or not account_number:
        raise ValueError(
            "Chưa cấu hình tài khoản ngân hàng nhận đặt cọc. "
            "Vào CRM admin → Thông tin trung tâm để cập nhật bank_code và bank_account_number."
        )

    amount_int = int(Decimal(amount))
    path = f"{VIETQR_BASE_URL}/{bank_code}-{quote(account_number)}-{template}.png"
    query = {
        "amount": amount_int,
        "addInfo": add_info,
    }
    if account_name:
        query["accountName"] = account_name
    return f"{path}?{urlencode(query, quote_via=quote)}"


def build_deposit_qr_for_enrollment(enrollment) -> dict:
    """Sinh data block đầy đủ cho FE trang đặt cọc.

    Trả về dict chứa: ``qr_url``, ``bank``, ``account_number``, ``account_name``,
    ``amount``, ``add_info``. FE render ảnh QR + bảng thông tin TK để HV nhập tay
    nếu app banking không quét được QR.
    """
    site = SiteSettings.get_solo()
    add_info = enrollment.code  # ORD-XXXXXX
    qr_url = build_vietqr_url(
        amount=enrollment.deposit_amount,
        add_info=add_info,
    )
    return {
        "qr_url": qr_url,
        "bank_code": site.bank_code,
        "account_number": site.bank_account_number,
        "account_name": site.bank_account_name,
        "amount": int(enrollment.deposit_amount),
        "add_info": add_info,
    }
