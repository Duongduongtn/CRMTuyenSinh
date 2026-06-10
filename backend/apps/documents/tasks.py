"""Celery tasks cho documents.

Task chính: auto-purge CCCD sau 90 ngày kể từ ngày hoàn thành khóa
(theo NĐ 13/2023 — Bảo vệ dữ liệu cá nhân).

Loại tài liệu cần purge (mặc định): cccd_front, cccd_back, health_cert.
Có thể cấu hình thêm qua admin DocumentType (thêm flag is_sensitive sau).
"""
from __future__ import annotations

import logging
from datetime import timedelta

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from apps.orders.models import Enrollment, EnrollmentStatus

from .models import DocumentStatus, PersonDocument

logger = logging.getLogger(__name__)


SENSITIVE_DOC_CODES = {"cccd_front", "cccd_back", "health_cert"}
PURGE_DELAY_DAYS = 90


@shared_task(name="apps.documents.purge_expired_documents")
def purge_expired_documents() -> dict:
    """Xóa file vật lý + đánh dấu trạng thái PURGED cho tài liệu CCCD/sức khỏe.

    Điều kiện: tài liệu gắn với Person mà mọi Enrollment của Person đó đã
    ``completed`` hoặc ``cancelled``/``refunded`` từ 90 ngày trở lên.
    """
    cutoff = timezone.now() - timedelta(days=PURGE_DELAY_DAYS)

    # Person có Enrollment hoàn thành/hủy cách đây >= 90 ngày, và KHÔNG có
    # Enrollment đang active.
    active_statuses = [
        EnrollmentStatus.PENDING,
        EnrollmentStatus.DEPOSITED,
        EnrollmentStatus.PARTIAL,
    ]
    # Sprint 2: Enrollment chưa link Person trực tiếp (denormalize bằng phone).
    # Khi Sprint 3 link Person, dùng filter join thực sự. Ở đây dùng pattern
    # bảo thủ — chỉ purge khi không còn enrollment active phù hợp SĐT của
    # AccountPersonLink.

    purged = 0
    qs = (
        PersonDocument.objects
        .filter(
            status__in=[DocumentStatus.APPROVED, DocumentStatus.EXPIRED],
            document_type__code__in=SENSITIVE_DOC_CODES,
            updated_at__lt=cutoff,
        )
        .select_related("person")
    )
    for doc in qs.iterator():
        person = doc.person
        # Tìm SĐT account link với person này
        phones = list(
            person.account_links.values_list("account__phone", flat=True).distinct()
        )
        if not phones:
            # Person mồ côi → vẫn purge nếu đã quá 90 ngày
            _purge_doc(doc)
            purged += 1
            continue
        has_active = Enrollment.objects.filter(
            student_phone__in=phones,
            status__in=active_statuses,
        ).exists()
        if has_active:
            continue
        # Check enrollment gần nhất đã hoàn thành/hủy cách đây >= 90 ngày
        latest_done = (
            Enrollment.objects.filter(student_phone__in=phones)
            .order_by("-completed_at", "-updated_at")
            .first()
        )
        last_event_at = (latest_done.completed_at or latest_done.updated_at) if latest_done else None
        if last_event_at and last_event_at >= cutoff:
            continue
        _purge_doc(doc)
        purged += 1

    logger.info("Auto-purge CCCD: %s tài liệu đã xóa.", purged)
    return {"purged": purged, "cutoff_iso": cutoff.isoformat()}


def _purge_doc(doc: PersonDocument) -> None:
    """Xóa file vật lý + đánh PURGED, giữ metadata để audit."""
    with transaction.atomic():
        try:
            doc.file.delete(save=False)
        except Exception as exc:
            logger.warning("Lỗi xóa file %s: %s", doc.file.name, exc)
        doc.status = DocumentStatus.PURGED
        doc.review_note = (doc.review_note + " | Auto-purge NĐ 13/2023").strip()[:500]
        doc.save(update_fields=["status", "review_note", "updated_at"])
