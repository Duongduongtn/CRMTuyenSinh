"""Signal handlers cho app orders.

Trigger Zalo ZNS + Telegram alert KHI mới tạo enrollment, KHÔNG khi update.
Async qua Celery để không block API response. Lỗi gửi tin nhắn KHÔNG rollback đơn.
"""
import logging

from django.db.models.signals import post_save
from django.db.transaction import on_commit
from django.dispatch import receiver

from .models import Enrollment

logger = logging.getLogger("apps.orders")


@receiver(post_save, sender=Enrollment)
def notify_on_new_enrollment(sender, instance: Enrollment, created: bool, **kwargs):
    """Gửi ZNS + Telegram khi enrollment vừa được tạo.

    Dùng `on_commit` để task chỉ chạy sau khi transaction convert hoàn tất —
    tránh trường hợp task chạy quá sớm và đọc state cũ.
    """
    if not created:
        return

    enrollment_id = instance.pk

    def _trigger():
        try:
            from .tasks import send_deposit_zns_link, send_new_order_telegram

            send_deposit_zns_link.delay(enrollment_id)
            send_new_order_telegram.delay(enrollment_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Không trigger được task notify enrollment: %s", exc)

    on_commit(_trigger)
