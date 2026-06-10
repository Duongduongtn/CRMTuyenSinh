"""Celery tasks cho app payments."""
import logging

from celery import shared_task
from django.conf import settings

logger = logging.getLogger("apps.payments")


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_payment_telegram(self, payment_id: int):
    """Alert Telegram group sale + kế toán khi có payment confirmed (Casso webhook)."""
    bot_token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CHAT_ID
    if not bot_token or not chat_id:
        logger.info("Telegram chưa cấu hình — bỏ qua alert payment.")
        return {"skipped": True, "reason": "no_token"}

    from .models import Payment

    try:
        payment = Payment.objects.select_related("enrollment", "enrollment__course").get(
            pk=payment_id
        )
    except Payment.DoesNotExist:
        logger.warning("Payment %s không tồn tại.", payment_id)
        return {"skipped": True, "reason": "payment_not_found"}

    enrollment = payment.enrollment
    amount_fmt = f"{int(payment.amount):,}".replace(",", ".") + " đ"
    paid_fmt = f"{int(enrollment.paid_amount):,}".replace(",", ".") + " đ"
    total_fmt = f"{int(enrollment.tuition_fee):,}".replace(",", ".") + " đ"
    method_label = dict(Payment._meta.get_field("method").choices).get(
        payment.method, payment.method
    )

    lines = [
        "✅ *Đã nhận thanh toán*",
        "",
        f"📋 `{enrollment.code}`",
        f"👤 {enrollment.student_name}",
        f"📞 `{enrollment.student_phone}`",
        f"🚗 {enrollment.course.title}",
        "",
        f"💰 Lần này: {amount_fmt} ({method_label})",
        f"📊 Tổng đã đóng: {paid_fmt} / {total_fmt}",
        f"📈 Trạng thái: {enrollment.get_status_display()}",
    ]
    if payment.bank_tx_id:
        lines.append(f"🏦 GD ngân hàng: `{payment.bank_tx_id}`")
    lines += [
        "",
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
