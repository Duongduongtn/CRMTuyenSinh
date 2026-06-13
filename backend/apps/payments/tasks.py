"""Celery tasks cho app payments.

Có 2 task chính:
- ``send_payment_telegram``: alert Telegram khi có thanh toán confirmed.
- ``reconcile_pending_payments``: fallback đối soát chạy 5 phút/lần — pull Casso API
  + re-match CassoTransaction local còn ``matched_enrollment=null`` (xử lý trường hợp
  webhook đến TRƯỚC khi đơn được tạo, hoặc webhook bị Casso miss).
"""
from __future__ import annotations

import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.utils import timezone

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

    # AF3 (2026-06-13): mask SĐT vishing defense. Telegram chat nội bộ nhưng
    # bot_token + chat_id leak ra ngoài (commit, log) sẽ lộ toàn bộ SĐT thanh
    # toán cho attacker scrape → social engineering "chúng tôi từ trung tâm,
    # bạn vừa chuyển X đồng...". Giữ 3 số đầu + 3 cuối đủ để kế toán/sale nhận
    # diện đơn; muốn xem full SĐT → click link CRM ở dòng cuối message.
    from apps.core.masking import mask_phone

    lines = [
        "✅ *Đã nhận thanh toán*",
        "",
        f"📋 `{enrollment.code}`",
        f"👤 {enrollment.student_name}",
        f"📞 `{mask_phone(enrollment.student_phone)}`",
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


@shared_task(name="apps.payments.reconcile_pending_payments")
def reconcile_pending_payments(lookback_hours: int = 24) -> dict:
    """Fallback đối soát Casso — chạy 5 phút/lần qua Celery beat.

    Mục đích: bắt 2 trường hợp webhook miss:

    1. **Late enrollment**: HV chuyển khoản TRƯỚC khi sale tạo đơn. Webhook
       đã insert ``CassoTransaction`` nhưng ``matched_enrollment=null`` vì lúc đó
       chưa có Enrollment khớp ``code``. Sau khi sale tạo đơn, task này tìm lại
       các CassoTransaction unmatched có ``matched_code`` đúng định dạng và link
       vào Enrollment mới.

    2. **Webhook miss**: Casso không gọi webhook (rate limit, network). Task
       gọi Casso API lấy giao dịch ``lookback_hours`` giờ gần nhất, đẩy vào
       cùng pipeline ``_process_one_transaction`` của webhook handler — idempotent
       qua unique key ``CassoTransaction.tid``.

    Args:
        lookback_hours: số giờ ngược về quá khứ. Mặc định 24h.

    Returns:
        Dict thống kê: ``{"rematched": int, "pulled": int, "matched_from_pull": int}``.
    """
    from .casso_client import iter_recent_transactions
    from .models import CassoTransaction
    from .webhooks import _process_one_transaction

    summary = {"rematched": 0, "pulled": 0, "matched_from_pull": 0}

    # === 1) Re-match local unmatched CassoTransaction ===
    # Filter:
    #  - amount > 0 (chỉ tiền vào)
    #  - matched_enrollment is null (chưa link)
    #  - matched_code != "" (có code regex hợp lệ trong description)
    #  - received_at trong lookback_hours (tránh quét vô tận)
    cutoff = timezone.now() - timedelta(hours=lookback_hours)
    unmatched = CassoTransaction.objects.filter(
        amount__gt=0,
        matched_enrollment__isnull=True,
        received_at__gte=cutoff,
    ).exclude(matched_code="")

    for ctx in unmatched.iterator(chunk_size=200):
        try:
            _rematch_one(ctx)
            summary["rematched"] += 1
        except Exception as exc:  # noqa: BLE001
            logger.exception("Re-match CassoTransaction %s lỗi: %s", ctx.tid, exc)

    # === 2) Pull Casso API nếu có API key ===
    since = timezone.now() - timedelta(hours=lookback_hours)
    for tx_raw in iter_recent_transactions(since=since):
        summary["pulled"] += 1
        try:
            result = _process_one_transaction(tx_raw)
            if result.get("status") == "matched":
                summary["matched_from_pull"] += 1
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "Process pulled tx %s lỗi: %s", tx_raw.get("tid"), exc
            )

    if summary["rematched"] or summary["matched_from_pull"]:
        logger.info(
            "Reconcile xong: re-match local=%d, pull=%d, match từ pull=%d",
            summary["rematched"],
            summary["pulled"],
            summary["matched_from_pull"],
        )
    return summary


def _rematch_one(casso_tx) -> None:
    """Link 1 CassoTransaction đã có ``matched_code`` vào Enrollment vừa được tạo.

    Tách riêng để dễ test. Atomic block lock cả Enrollment + CassoTransaction.
    Bỏ qua silently nếu Enrollment vẫn chưa tồn tại — lần chạy sau task sẽ thử lại.
    """
    from decimal import Decimal

    from apps.orders.models import Enrollment

    from .models import CassoTransaction, Payment, PaymentMethod, PaymentStatus

    code = casso_tx.matched_code
    if not code:
        return

    with transaction.atomic():
        # Re-fetch lock — tránh race với webhook đến cùng lúc cho cùng tid.
        ctx = CassoTransaction.objects.select_for_update().get(pk=casso_tx.pk)
        if ctx.matched_enrollment_id:
            return  # webhook khác đã match xong giữa lúc task chạy

        try:
            enrollment = Enrollment.objects.select_for_update().get(code=code)
        except Enrollment.DoesNotExist:
            return  # vẫn chưa có đơn — lần sau thử lại

        # Nếu CassoTransaction này đã được link Payment (bất thường nhưng có thể
        # do migrate cũ), không tạo Payment trùng — chỉ link matched_enrollment.
        if hasattr(ctx, "payment") and ctx.payment is not None:
            ctx.matched_enrollment = enrollment
            ctx.matched_at = timezone.now()
            ctx.save(update_fields=["matched_enrollment", "matched_at"])
            return

        now = timezone.now()
        payment = Payment.objects.create(
            enrollment=enrollment,
            amount=ctx.amount,
            method=PaymentMethod.CASSO,
            status=PaymentStatus.CONFIRMED,
            casso_transaction=ctx,
            bank_tx_id=ctx.tid,
            reference_code=code,
            confirmed_at=now,
        )

        enrollment.paid_amount = (
            enrollment.paid_amount or Decimal("0")
        ) + ctx.amount
        enrollment.recompute_status_from_paid()
        enrollment.save(
            update_fields=[
                "paid_amount",
                "status",
                "deposit_paid_at",
                "completed_at",
                "updated_at",
            ]
        )

        ctx.matched_enrollment = enrollment
        ctx.matched_at = now
        ctx.save(update_fields=["matched_enrollment", "matched_at"])

        # Telegram alert ngoài lock
        from django.db.transaction import on_commit

        def _alert():
            try:
                send_payment_telegram.delay(payment.id)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Không trigger Telegram alert payment: %s", exc)

        on_commit(_alert)
