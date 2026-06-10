"""Celery tasks cho app leads."""
import logging

from celery import shared_task
from django.conf import settings

logger = logging.getLogger("apps.leads")


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_new_lead_telegram(self, lead_id: int):
    """Gửi tin nhắn Telegram khi có lead mới.

    Format: tên + SĐT trong code block + hạng quan tâm + source + link CRM.
    """
    bot_token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CHAT_ID
    if not bot_token or not chat_id:
        logger.info("TELEGRAM_BOT_TOKEN hoặc TELEGRAM_CHAT_ID chưa cấu hình — bỏ qua alert.")
        return {"skipped": True, "reason": "no_token"}

    from .models import Lead

    try:
        lead = Lead.objects.get(pk=lead_id)
    except Lead.DoesNotExist:
        logger.warning("Lead %s không tồn tại — bỏ qua alert.", lead_id)
        return {"skipped": True, "reason": "lead_not_found"}

    # Build message tiếng Việt (Markdown)
    vehicle_label = dict(lead._meta.get_field("vehicle_class").choices).get(
        lead.vehicle_class, lead.vehicle_class or "(chưa chọn)"
    )
    source_label = dict(lead._meta.get_field("source").choices).get(lead.source, lead.source)

    lines = [
        "🔔 *Lead mới*",
        "",
        f"👤 {lead.name}",
        f"📞 `{lead.phone}`",
        f"🚗 Hạng quan tâm: {vehicle_label}",
        f"📍 Khu vực: {lead.district or '(chưa rõ)'}",
        f"🌐 Nguồn: {source_label}",
    ]
    if lead.source_page:
        lines.append(f"📄 Trang: {lead.source_page}")
    if lead.utm_campaign:
        lines.append(f"🎯 Campaign: {lead.utm_campaign}")
    if lead.notes:
        # Giới hạn 200 ký tự để tránh tin quá dài
        note_short = lead.notes[:200] + ("..." if len(lead.notes) > 200 else "")
        lines.append(f"📝 {note_short}")
    lines += [
        "",
        f"🕐 {lead.created_at.strftime('%H:%M %d/%m/%Y')}",
        f"🔗 Mở CRM: {settings.SITE_CRM_URL}/admin/leads/lead/{lead.id}/change/",
    ]
    text = "\n".join(lines)

    # Gọi API Telegram qua requests
    import requests

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code >= 400:
            logger.error("Telegram API trả %s: %s", resp.status_code, resp.text)
            raise self.retry(exc=Exception(f"HTTP {resp.status_code}"))
        return {"ok": True, "message_id": resp.json().get("result", {}).get("message_id")}
    except Exception as exc:
        logger.exception("Gửi Telegram lỗi: %s", exc)
        raise self.retry(exc=exc)
