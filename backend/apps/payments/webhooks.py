"""Webhook handler cho Casso — POST /webhook/casso.

Quy trình bảo mật:
1. Đọc raw body (KHÔNG parse json trước).
2. Lấy chữ ký từ header ``Secure-Token`` (Casso V2 dùng tên này).
3. Verify HMAC-SHA256 hex digest body với ``CASSO_WEBHOOK_SECRET`` —
   constant_time_compare để chống timing attack.
4. Parse json, iterate ``data`` list.
5. Với mỗi tx: ``select_for_update`` ``CassoTransaction`` theo ``tid``.
   - Nếu đã tồn tại → idempotent skip.
   - Nếu mới → tạo CassoTransaction, regex extract ORD-XXXXXX, match Enrollment.
6. Match thành công → tạo Payment + cập nhật ``Enrollment.paid_amount`` +
   recompute status — tất cả trong 1 atomic block, ``select_for_update`` Enrollment.

KHÔNG dùng csrf_exempt một cách bất cẩn — endpoint chỉ chấp nhận POST + verify HMAC.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import re
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils import timezone
from django.utils.crypto import constant_time_compare
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.core.views import _get_client_ip
from apps.orders.models import Enrollment

from .models import CassoTransaction, Payment, PaymentMethod, PaymentStatus

logger = logging.getLogger("apps.payments")

ORDER_CODE_RE = re.compile(r"\bORD-[A-F0-9]{6}\b", re.IGNORECASE)


def verify_casso_signature(raw_body: bytes, header_token: str, secret: str) -> bool:
    """HMAC-SHA256 verify với constant_time_compare.

    Trả False nếu secret/token rỗng — caller xử lý 401.
    """
    if not secret or not header_token:
        return False
    expected = hmac.new(
        secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    return constant_time_compare(expected, header_token.strip())


def _parse_when(when_str: str | None):
    """Parse Casso datetime (ISO8601 với offset) sang aware datetime."""
    if not when_str:
        return None
    try:
        from datetime import datetime

        # Casso gửi format "2026-06-10T14:25:00+0700" hoặc "2026-06-10 14:25:00"
        for fmt in (
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
        ):
            try:
                dt = datetime.strptime(when_str, fmt)
                if dt.tzinfo is None:
                    dt = timezone.make_aware(dt)
                return dt
            except ValueError:
                continue
    except Exception:  # noqa: BLE001
        logger.warning("Không parse được Casso when=%s", when_str)
    return None


def _process_one_transaction(tx: dict) -> dict:
    """Xử lý 1 record trong ``data[]`` của payload Casso.

    Trả dict ``{"tid": str, "status": "skipped|matched|unmatched|invalid"}``.
    Idempotent qua unique key ``CassoTransaction.tid``.
    """
    tid = str(tx.get("tid") or "").strip()
    if not tid:
        return {"tid": "", "status": "invalid", "reason": "no_tid"}

    raw_amount = tx.get("amount")
    try:
        amount = Decimal(str(raw_amount))
    except Exception:  # noqa: BLE001
        return {"tid": tid, "status": "invalid", "reason": "bad_amount"}

    description = str(tx.get("description") or "")
    casso_id = str(tx.get("id") or "")
    bank_brand = str(tx.get("bankBrandName") or tx.get("bank_brand_name") or "")
    bank_sub_acc = str(tx.get("subAccId") or tx.get("bank_sub_acc_id") or "")
    when_dt = _parse_when(tx.get("when"))

    # Regex tìm tất cả mã ORD-XXXXXX trong description.
    # Nếu có >1 mã (ví dụ "chuyen ORD-AAA111 sang ORD-BBB222") — KHÔNG auto-match,
    # để kế toán xử lý tay để tránh nhầm đơn.
    raw_codes = ORDER_CODE_RE.findall(description)
    unique_codes = {c.upper() for c in raw_codes}
    matched_code = next(iter(unique_codes)) if len(unique_codes) == 1 else ""
    ambiguous = len(unique_codes) > 1

    with transaction.atomic():
        # 1. Idempotent — wrap create + bắt IntegrityError race-safe (2 webhook cùng tid).
        defaults = {
            "casso_id": casso_id,
            "description": description,
            "amount": amount,
            "bank_brand_name": bank_brand,
            "bank_sub_acc_id": bank_sub_acc,
            "when": when_dt,
            "matched_code": matched_code,
            "payload": tx,
        }
        try:
            with transaction.atomic():
                casso_tx = CassoTransaction.objects.create(tid=tid, **defaults)
            created = True
        except IntegrityError:
            # 2 webhook cùng tid đến gần đồng thời — fetch row đã tạo.
            casso_tx = CassoTransaction.objects.get(tid=tid)
            created = False
        if not created:
            return {"tid": tid, "status": "skipped", "reason": "duplicate"}

        # 2. Chỉ xử lý tiền vào (amount > 0). Tiền ra (refund/manual outgoing) lưu nhưng không tạo Payment.
        if amount <= 0:
            return {"tid": tid, "status": "ignored", "reason": "non_positive_amount"}

        # 3. Match với Enrollment nếu có code
        if not matched_code:
            if ambiguous:
                logger.warning(
                    "Casso tx %s có nhiều mã ORD-XXXXXX (%s) — không auto-match, "
                    "kế toán xử lý tay. Description: %s",
                    tid,
                    sorted(unique_codes),
                    description[:200],
                )
                return {"tid": tid, "status": "unmatched", "reason": "multiple_order_codes"}
            logger.warning(
                "Casso tx %s không tìm thấy mã ORD-XXXXXX trong description: %s",
                tid,
                description[:200],
            )
            return {"tid": tid, "status": "unmatched", "reason": "no_order_code"}

        try:
            enrollment = Enrollment.objects.select_for_update().get(code=matched_code)
        except Enrollment.DoesNotExist:
            logger.warning(
                "Casso tx %s match mã %s nhưng không có Enrollment.", tid, matched_code
            )
            return {
                "tid": tid,
                "status": "unmatched",
                "reason": "enrollment_not_found",
                "code": matched_code,
            }

        # 4. Tạo Payment (idempotent qua OneToOne casso_transaction)
        now = timezone.now()
        payment = Payment.objects.create(
            enrollment=enrollment,
            amount=amount,
            method=PaymentMethod.CASSO,
            status=PaymentStatus.CONFIRMED,
            casso_transaction=casso_tx,
            bank_tx_id=tid,
            reference_code=matched_code,
            confirmed_at=now,
        )

        # 5. Cộng dồn paid_amount và recompute status
        enrollment.paid_amount = (enrollment.paid_amount or Decimal("0")) + amount
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

        # 6. Mark casso tx đã match
        casso_tx.matched_enrollment = enrollment
        casso_tx.matched_at = now
        casso_tx.save(update_fields=["matched_enrollment", "matched_at"])

        # 7. Trigger Telegram alert async
        from django.db.transaction import on_commit

        def _alert():
            try:
                from .tasks import send_payment_telegram

                send_payment_telegram.delay(payment.id)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Không trigger Telegram alert payment: %s", exc)

        on_commit(_alert)

    return {
        "tid": tid,
        "status": "matched",
        "code": matched_code,
        "amount": str(amount),
        "enrollment_id": enrollment.id,
        "payment_id": payment.id,
    }


@csrf_exempt
@require_POST
def casso_webhook(request: HttpRequest) -> HttpResponse:
    """POST /webhook/casso — endpoint Casso gọi khi có giao dịch mới.

    Header bắt buộc: ``Secure-Token`` (hex HMAC-SHA256 của body với ``CASSO_WEBHOOK_SECRET``).
    Body: JSON theo Casso V2 spec (``{"error": 0, "data": [...]}``).
    """
    raw_body = request.body
    # Đọc secret qua loader: ưu tiên DB IntegrationCredential (UI paste), fallback ENV.
    from apps.core.integrations import get_credential

    secret = get_credential("casso", "webhook_secret") or ""
    if not secret:
        logger.error("CASSO_WEBHOOK_SECRET chưa cấu hình — từ chối webhook.")
        return JsonResponse(
            {"detail": "Webhook chưa cấu hình."},
            status=503,
        )

    header_token = request.headers.get("Secure-Token", "") or request.headers.get(
        "X-Casso-Signature", ""
    )
    if not verify_casso_signature(raw_body, header_token, secret):
        # AF3 (2026-06-13): dùng _get_client_ip tôn trọng TRUST_X_FORWARDED_FOR.
        # Trước fix: REMOTE_ADDR luôn là 127.0.0.1 vì nginx proxy → mất IP attacker
        # thật trong log signature mismatch (cản trở forensic + IP whitelist sau).
        logger.warning(
            "Casso webhook signature không hợp lệ. IP=%s", _get_client_ip(request)
        )
        return JsonResponse({"detail": "Sai chữ ký."}, status=401)

    try:
        payload = json.loads(raw_body.decode("utf-8") or "{}")
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        logger.exception("Casso webhook body không phải JSON hợp lệ: %s", exc)
        return JsonResponse({"detail": "Body không hợp lệ."}, status=400)

    tx_list = payload.get("data") or []
    if not isinstance(tx_list, list):
        return JsonResponse(
            {"detail": "`data` phải là list."},
            status=400,
        )

    results = []
    for tx in tx_list:
        if not isinstance(tx, dict):
            continue
        try:
            results.append(_process_one_transaction(tx))
        except Exception as exc:  # noqa: BLE001
            logger.exception("Xử lý Casso tx lỗi: %s", exc)
            results.append({"tid": tx.get("tid", ""), "status": "error", "reason": str(exc)})

    # Casso yêu cầu response 200 cho tx đã nhận. Lỗi từng tx được nêu trong body.
    return JsonResponse({"error": 0, "processed": len(results), "results": results})
