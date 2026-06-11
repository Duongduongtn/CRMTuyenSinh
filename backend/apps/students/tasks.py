"""Celery tasks app students.

- ``send_delete_request_telegram``: thông báo admin có HV yêu cầu xóa dữ liệu.
  Phải xử lý thủ công theo NĐ 13/2023/NĐ-CP Điều 9 (đối chiếu công nợ, hồ sơ
  đã nộp Sở GTVT chưa).
"""
from __future__ import annotations

import logging

from celery import shared_task
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger("apps.students")


def _mask_display_name(name: str) -> str:
    """Mask tên cho Telegram: lấy 1 ký tự đầu mỗi từ — `Nguyễn Văn A` → `N. V. A`.

    Mục đích chống lộ PII lên Telegram cloud — tên đầy đủ vẫn xem trong CRM
    qua link admin đính kèm.
    """
    if not name:
        return "(chưa có)"
    parts = [p for p in name.strip().split() if p]
    if not parts:
        return "(chưa có)"
    return ". ".join(p[:1].upper() for p in parts) + "."


def _summarize_debt(phone: str) -> str:
    """Tổng kết công nợ theo SĐT cho Telegram alert.

    Trả "Công nợ: 1.234.567 đồng (N đơn)". Nếu lỗi truy vấn → trả empty string
    để không phá flow gửi Telegram.
    """
    try:
        from decimal import Decimal

        from apps.orders.models import Enrollment, EnrollmentStatus

        enrollments = Enrollment.objects.filter(student_phone=phone).exclude(
            status__in=[EnrollmentStatus.CANCELLED, EnrollmentStatus.REFUNDED]
        ).values("tuition_fee", "paid_amount")
        total_remaining = Decimal("0")
        count_open = 0
        for e in enrollments:
            remaining = max(Decimal("0"), e["tuition_fee"] - e["paid_amount"])
            total_remaining += remaining
            if remaining > 0:
                count_open += 1
        if not enrollments:
            return "Công nợ: không có đơn nào trong hệ thống."
        formatted = f"{int(total_remaining):,}".replace(",", ".")
        return f"Công nợ: {formatted} đồng ({count_open}/{len(enrollments)} đơn còn nợ)."
    except Exception:  # noqa: BLE001 — không break Telegram nếu query lỗi
        logger.exception("Lỗi tổng kết công nợ cho %s", phone[:3] + "****")
        return ""


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_delete_request_telegram(self, request_id: int):
    """Gửi Telegram alert khi HV yêu cầu xóa dữ liệu.

    KHÔNG gửi PII đầy đủ — chỉ SĐT (đã mask), lý do, link admin để mở chi tiết.
    """
    bot_token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CHAT_ID
    if not bot_token or not chat_id:
        logger.warning(
            "TELEGRAM_BOT_TOKEN/CHAT_ID chưa cấu hình — bỏ qua alert delete-request %s",
            request_id,
        )
        return {"skipped": True, "reason": "no_token"}

    from .models import StudentDeleteRequest

    try:
        req = StudentDeleteRequest.objects.select_related("account").get(pk=request_id)
    except StudentDeleteRequest.DoesNotExist:
        logger.warning("StudentDeleteRequest %s không tồn tại.", request_id)
        return {"skipped": True, "reason": "not_found"}

    phone = req.account.phone or ""
    # Mask 3 đầu + 3 cuối (chuẩn ngân hàng), giấu 4 chữ số giữa.
    masked_phone = phone[:3] + "****" + phone[-3:] if len(phone) >= 7 else "***"
    masked_name = _mask_display_name(req.account.display_name)
    reason_short = (req.reason or "(không nêu lý do)").strip()
    if len(reason_short) > 250:
        reason_short = reason_short[:247] + "..."

    # Đính kèm tóm tắt công nợ cho admin (xem payment-integration-reviewer P1.2).
    debt_line = _summarize_debt(req.account.phone)

    lines = [
        "Yêu cầu xóa dữ liệu (NĐ 13/2023)",
        "",
        f"SĐT: {masked_phone}",
        f"Tên: {masked_name}",
        f"Lý do: {reason_short}",
        f"Lúc: {req.created_at.strftime('%H:%M %d/%m/%Y')}",
        debt_line,
        "",
        "Cần xử lý thủ công: đối soát công nợ, hồ sơ đã nộp Sở GTVT.",
        f"Mở CRM: {settings.SITE_CRM_URL}/admin/students/studentdeleterequest/{req.id}/change/",
        "Liên hệ HV qua kênh đã đăng ký (Zalo tay/SMS tay/gọi điện) để xác minh.",
    ]
    text = "\n".join(line for line in lines if line is not None)

    import requests

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    # KHÔNG dùng parse_mode để tránh Markdown injection từ field `reason`/tên.
    payload = {"chat_id": chat_id, "text": text, "disable_web_page_preview": True}
    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code >= 400:
            logger.error(
                "Telegram (delete-request) trả %s: %s", resp.status_code, resp.text
            )
            raise self.retry(exc=Exception(f"HTTP {resp.status_code}"))
        req.telegram_sent_at = timezone.now()
        req.save(update_fields=["telegram_sent_at", "updated_at"])
        return {"ok": True, "request_id": req.id}
    except Exception as exc:
        logger.exception("Gửi Telegram delete-request lỗi: %s", exc)
        raise self.retry(exc=exc)
