"""Celery tasks cho app orders.

- `send_deposit_zns_link`: gửi Zalo ZNS link đặt cọc cho HV sau khi sale chốt đơn.
- `send_new_order_telegram`: alert Telegram cho group sale khi có đơn mới.

Cả 2 task đều idempotent — gọi lại 1 task cho 1 enrollment không gây tin nhắn trùng
do enrollment có flag riêng (sẽ thêm khi cần). Hiện tại không có flag, caller chỉ
trigger 1 lần từ signal `post_save created=True`.
"""
import logging

from celery import shared_task
from django.conf import settings

logger = logging.getLogger("apps.orders")


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_deposit_zns_link(self, enrollment_id: int):
    """Gửi Zalo ZNS chứa link đặt cọc cho học viên.

    Sprint 1: mock — chỉ log ra console nếu ZNS_ACCESS_TOKEN chưa cấu hình.
    Sprint 2: gọi Zalo Notification Service API thật khi template đã được duyệt.
    """
    from .models import Enrollment

    try:
        enrollment = Enrollment.objects.select_related("course").get(pk=enrollment_id)
    except Enrollment.DoesNotExist:
        logger.warning("Enrollment %s không tồn tại — bỏ qua ZNS.", enrollment_id)
        return {"skipped": True, "reason": "enrollment_not_found"}

    site_url = settings.SITE_PUBLIC_URL.rstrip("/")
    deposit_url = f"{site_url}/dh/{enrollment.code}"

    if not settings.ZNS_ACCESS_TOKEN or not settings.ZNS_TEMPLATE_ID_DEPOSIT:
        logger.info(
            "[MOCK ZNS] Gửi link đặt cọc cho %s (%s): %s",
            enrollment.student_name,
            enrollment.student_phone,
            deposit_url,
        )
        return {"mocked": True, "url": deposit_url}

    # Sprint 2: thay phần này bằng gọi Zalo ZNS API thật
    import requests

    payload = {
        "phone": enrollment.student_phone,
        "template_id": settings.ZNS_TEMPLATE_ID_DEPOSIT,
        "template_data": {
            "ho_ten": enrollment.student_name,
            "khoa": enrollment.course.title,
            "ma_don": enrollment.code,
            "so_tien_coc": f"{int(enrollment.deposit_amount):,}".replace(",", ".") + " đ",
            "link": deposit_url,
        },
    }
    headers = {"access_token": settings.ZNS_ACCESS_TOKEN}
    try:
        resp = requests.post(
            "https://business.openapi.zalo.me/message/template",
            headers=headers,
            json=payload,
            timeout=10,
        )
        if resp.status_code >= 400:
            logger.error("ZNS lỗi HTTP %s: %s", resp.status_code, resp.text)
            raise self.retry(exc=Exception(f"HTTP {resp.status_code}"))
        return {"ok": True, "data": resp.json()}
    except Exception as exc:
        logger.exception("Gửi ZNS lỗi: %s", exc)
        raise self.retry(exc=exc)


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
        "🧾 *Đơn mới*",
        "",
        f"📋 `{enrollment.code}`",
        f"👤 {enrollment.student_name}",
        f"📞 `{enrollment.student_phone}`",
        f"🚗 {enrollment.course.title} ({enrollment.vehicle_class})",
        f"💰 Cọc: {deposit_amount_fmt}",
        f"👨‍💼 Sale: {sale_name}",
        "",
        f"🕐 {enrollment.created_at.strftime('%H:%M %d/%m/%Y')}",
        f"🔗 CRM: {settings.SITE_CRM_URL}/admin/orders/enrollment/{enrollment.id}/change/",
    ]
    text = "\n".join(lines)

    import requests

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code >= 400:
            logger.error("Telegram API trả %s: %s", resp.status_code, resp.text)
            raise self.retry(exc=Exception(f"HTTP {resp.status_code}"))
        return {"ok": True}
    except Exception as exc:
        logger.exception("Gửi Telegram lỗi: %s", exc)
        raise self.retry(exc=exc)
