"""Celery tasks cho app orders.

- ``send_new_order_telegram``: alert Telegram cho group sale khi có đơn mới.

Task idempotent — gọi lại 1 task cho 1 enrollment không gây tin nhắn trùng do
caller chỉ trigger 1 lần từ signal ``post_save created=True``.

Sprint 3 Tuần 7 (2026-06-12): bỏ ``send_deposit_zns_link`` (ZNS Zalo đã bị gỡ
khỏi MVP). Văn thư CRM tự gen "link xem nhanh" qua endpoint staff (xem
[[student-auth-flow]]) và gửi tay cho HV qua Zalo/SMS/gọi điện.
"""
import logging

from celery import shared_task
from django.conf import settings

logger = logging.getLogger("apps.orders")


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_new_order_telegram(self, enrollment_id: int):
    """Alert Telegram group sale khi có đơn mới."""
    bot_token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CHAT_ID
    if not bot_token or not chat_id:
        logger.info("Telegram chưa cấu hình — bỏ qua alert đơn mới.")
        return {"skipped": True, "reason": "no_token"}

    from .models import Enrollment

    try:
        enrollment = Enrollment.objects.select_related("course", "created_by").get(
            pk=enrollment_id
        )
    except Enrollment.DoesNotExist:
        logger.warning("Enrollment %s không tồn tại.", enrollment_id)
        return {"skipped": True, "reason": "enrollment_not_found"}

    deposit_amount_fmt = (
        f"{int(enrollment.deposit_amount):,}".replace(",", ".") + " đ"
    )
    sale_name = (
        enrollment.created_by.get_display_name() if enrollment.created_by else "(không rõ)"
    )
    lines = [
        "Đơn mới",
        "",
        f"Mã đơn: {enrollment.code}",
        f"Học viên: {enrollment.student_name}",
        f"SĐT: {enrollment.student_phone}",
        f"Khóa: {enrollment.course.title} ({enrollment.vehicle_class})",
        f"Cọc: {deposit_amount_fmt}",
        f"Sale: {sale_name}",
        "",
        f"Lúc: {enrollment.created_at.strftime('%H:%M %d/%m/%Y')}",
        f"Mở CRM: {settings.SITE_CRM_URL}/admin/orders/enrollment/{enrollment.id}/change/",
    ]
    text = "\n".join(lines)

    import requests

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    # KHÔNG dùng parse_mode để tránh Markdown injection từ student_name (input user).
    payload = {"chat_id": chat_id, "text": text, "disable_web_page_preview": True}
    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code >= 400:
            logger.error("Telegram API trả %s: %s", resp.status_code, resp.text)
            raise self.retry(exc=Exception(f"HTTP {resp.status_code}"))
        return {"ok": True}
    except Exception as exc:
        logger.exception("Gửi Telegram lỗi: %s", exc)
        raise self.retry(exc=exc)
