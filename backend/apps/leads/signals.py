"""Signal handlers cho lead. Telegram alert async khi có lead mới."""
import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Lead

logger = logging.getLogger("apps.leads")


@receiver(post_save, sender=Lead)
def alert_telegram_on_new_lead(sender, instance: Lead, created: bool, **kwargs):
    """Khi tạo Lead mới, gửi tin nhắn Telegram cho nhóm sale.

    Async qua Celery để không block response của API.
    Nếu Telegram fail, KHÔNG rollback Lead — chỉ log warning.
    """
    if not created:
        return

    try:
        from .tasks import send_new_lead_telegram

        send_new_lead_telegram.delay(instance.id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Không gửi được Telegram task: %s", exc)
