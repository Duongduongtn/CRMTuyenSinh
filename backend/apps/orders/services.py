"""Service layer cho orders — tách logic convert lead → enrollment khỏi view.

Lý do tách: dùng được trong CLI/Celery/admin action mà không lệ thuộc DRF request.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.courses.models import Course
from apps.leads.models import Lead

from .models import Enrollment, EnrollmentStatus

logger = logging.getLogger("apps.orders")


class ConvertError(Exception):
    """Lỗi nghiệp vụ khi convert lead → enrollment. Kèm `code` để map sang HTTP."""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


@dataclass(frozen=True)
class ConvertResult:
    enrollment: Enrollment
    created: bool  # True nếu vừa tạo, False nếu đã tồn tại (idempotent hit)


def convert_lead_to_enrollment(
    *,
    lead_id: int,
    course_id: int,
    user,
    student_name: str = "",
    student_phone: str = "",
    student_email: str = "",
    notes: str = "",
    max_code_retries: int = 5,
) -> ConvertResult:
    """Atomic + idempotent + race-safe.

    Quy trình:
    1. ``select_for_update`` Lead → check đã convert chưa, nếu có trả về enrollment cũ.
    2. ``select_for_update`` Course → check available_slots > 0.
    3. Tạo Enrollment với code unique (retry tối đa 5 lần nếu collision).
    4. Cập nhật Course.available_slots -= 1.
    5. Cập nhật Lead.converted_to_order=True, order_code, status=success, converted_at.
    6. (Caller) trigger task Celery gửi Zalo ZNS deposit link async.

    Raises:
        ConvertError: nếu course không còn slot hoặc lỗi business khác.
    """
    with transaction.atomic():
        # 1. Lock lead — chống race convert đồng thời
        try:
            lead = Lead.objects.select_for_update().get(pk=lead_id)
        except Lead.DoesNotExist as exc:
            raise ConvertError("lead_not_found", "Lead không tồn tại.") from exc

        # Idempotent: nếu đã có enrollment gắn lead này, trả về luôn (không tạo mới, không trừ slot)
        existing = Enrollment.objects.filter(lead=lead).first()
        if existing is not None:
            return ConvertResult(enrollment=existing, created=False)

        # 2. Lock course — chống race 2 convert cùng course cuối cùng
        try:
            course = Course.objects.select_for_update().get(pk=course_id)
        except Course.DoesNotExist as exc:
            raise ConvertError("course_not_found", "Khóa học không tồn tại.") from exc

        if not course.is_visible:
            raise ConvertError("course_unavailable", "Khóa học đang ngừng tuyển sinh.")
        if course.available_slots <= 0:
            raise ConvertError(
                "course_full",
                f"Khóa '{course.title}' đã hết suất. Vui lòng chọn khóa khác.",
            )

        # 3. Build enrollment data (snapshot price + student info)
        final_name = (student_name or lead.name or "").strip()
        final_phone = (student_phone or lead.phone or "").strip()
        if not final_name or not final_phone:
            raise ConvertError(
                "missing_student_info",
                "Học viên thiếu họ tên hoặc số điện thoại.",
            )
        final_email = student_email or lead.email or ""

        # Retry sinh code nếu collision (xác suất rất thấp với 16^6)
        last_error: Optional[Exception] = None
        for _ in range(max_code_retries):
            code = Enrollment.generate_code()
            try:
                with transaction.atomic():
                    enrollment = Enrollment.objects.create(
                        code=code,
                        lead=lead,
                        course=course,
                        student_name=final_name,
                        student_phone=final_phone,
                        student_email=final_email,
                        vehicle_class=course.vehicle_class,
                        tuition_fee=course.tuition_fee,
                        deposit_amount=course.deposit_amount,
                        status=EnrollmentStatus.PENDING,
                        notes=notes,
                        created_by=user if user and user.is_authenticated else None,
                    )
                break
            except IntegrityError as exc:
                last_error = exc
                continue
        else:
            # Hết retry mà vẫn collision
            raise ConvertError(
                "code_collision",
                "Không sinh được mã đơn duy nhất. Vui lòng thử lại.",
            ) from last_error

        # 4. Trừ slot
        course.available_slots = max(0, course.available_slots - 1)
        course.save(update_fields=["available_slots", "updated_at"])

        # 5. Đánh dấu lead đã convert
        now = timezone.now()
        from apps.leads.models import LeadStatus  # tránh circular import

        lead.converted_to_order = True
        lead.order_code = code
        lead.converted_at = now
        lead.status = LeadStatus.SUCCESS
        lead.save(
            update_fields=[
                "converted_to_order",
                "order_code",
                "converted_at",
                "status",
                "updated_at",
            ]
        )

        # 6. Auto-provision tài khoản học viên (SĐT) + Person (CCCD rỗng, chờ
        #    văn thư nhập tay) + AccountPersonLink. Xem [[student-auth-flow]] +
        #    [[person-enrollment-model]]: HV chỉ login PWA được khi có đủ 3 bản
        #    ghi này + văn thư nhập CCCD vào Person.id_number.
        _provision_student_account(
            phone=final_phone,
            display_name=final_name,
            user=user if user and user.is_authenticated else None,
            lead_id=lead.id,
        )

        return ConvertResult(enrollment=enrollment, created=True)


def _mask_phone(phone: str) -> str:
    """Mask SĐT để log/audit không lộ PII đầy đủ (NĐ 13/2023).

    `0901234567` -> `090****567`. Cùng pattern với ``apps.students.views._audit_login``.
    """
    if not phone or len(phone) < 7:
        return "***"
    return phone[:3] + "****" + phone[-3:]


def _provision_student_account(
    *,
    phone: str,
    display_name: str,
    user=None,
    lead_id: int | None = None,
) -> None:
    """Tạo (hoặc reuse) StudentAccount + Person + AccountPersonLink primary.

    Idempotent qua các nhánh:
    - SĐT đã có account + có Person primary (id_number rỗng hay đầy đủ) → reuse,
      KHÔNG tạo Person mới (tránh duplicate khi 1 HV đăng ký nhiều khóa).
    - SĐT đã có account NHƯNG Person primary đã có ``id_number != ""`` →
      **KHÔNG tạo Link rỗng mới** (chống hijack: kẻ xấu submit lead với SĐT của
      HV thật để được sale chốt đơn → tạo Person rỗng dưới account đã có CCCD).
      Ghi AuditLog phone collision để admin/CRM review.
    - Account chưa có primary Link → tạo Person mới (CCCD rỗng) + Link.

    Bọc trong ``transaction.atomic(savepoint=True)`` riêng để khi raise (vd
    IntegrityError race tạo 2 primary cùng SĐT), savepoint rollback CHỈ phần
    provision — transaction outer (Enrollment + Lead update) vẫn commit. Đây mới
    đúng intent "thà có Enrollment không có Account".

    Reviewer Z (2026-06-12):
    - BE.P1.1 savepoint nested.
    - BE.P1.2 + Migration 0005 UniqueConstraint partial ``is_primary=True``.
    - SEC.P1.1 chống hijack qua phone collision.
    - SEC.P1.2 AuditLog cho Link.
    - BE/SEC.P2 mask phone trong log.
    """
    from django.db import DatabaseError, IntegrityError

    from apps.core.models import AuditLog
    from apps.students.models import (
        AccountPersonLink,
        Person,
        StudentAccount,
        normalize_phone,
    )

    normalized = normalize_phone(phone)
    if not normalized:
        logger.warning("Auto-provision bỏ qua: SĐT rỗng sau normalize.")
        return

    masked = _mask_phone(normalized)

    def _record_audit(action: str, target_model: str, target_id: str, extra: dict) -> None:
        try:
            AuditLog.objects.create(
                user=user,
                action=action,
                target_model=target_model,
                target_id=target_id,
                changes={
                    "phone_masked": masked,
                    "via": "auto_provision",
                    "lead_id": lead_id,
                    **extra,
                },
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Ghi AuditLog auto-provision lỗi: %s", exc)

    try:
        with transaction.atomic():  # savepoint
            account, account_created = StudentAccount.objects.get_or_create(
                phone=normalized,
                defaults={
                    "display_name": display_name or "",
                    "is_active": True,
                },
            )
            # Cập nhật display_name nếu account cũ chưa có tên (auto-provision
            # lần đầu từ lead có thông tin) — KHÔNG ghi đè khi đã có tên.
            if not account_created and not account.display_name and display_name:
                account.display_name = display_name
                account.save(update_fields=["display_name", "updated_at"])

            primary_link = (
                AccountPersonLink.objects
                .filter(account=account, is_primary=True)
                .select_related("person")
                .first()
            )
            if primary_link is not None:
                if (primary_link.person.id_number or "").strip():
                    # SEC.P1.1 chống hijack: account đã có Person CCCD thật.
                    # Có thể là HV cũ và lead này là chính HV (OK) HOẶC là kẻ
                    # xấu submit lead với SĐT người khác. Không thể phân biệt
                    # ở backend → KHÔNG tự tạo Person rỗng nữa, ghi AuditLog
                    # để admin review.
                    logger.warning(
                        "Auto-provision phone collision: account %s đã có "
                        "Person có CCCD. Bỏ qua tạo Link mới cho lead_id=%s.",
                        masked,
                        lead_id,
                    )
                    _record_audit(
                        AuditLog.Action.UPDATE,
                        "students.AccountPersonLink",
                        str(primary_link.pk),
                        {"event": "phone_collision_skip", "account_id": account.pk},
                    )
                # Đã có primary Link (CCCD đầy đủ hoặc rỗng) → reuse.
                return

            # Account chưa có primary Person — tạo Person mới + Link.
            person = Person.objects.create(full_name=display_name or "")
            link = AccountPersonLink.objects.create(
                account=account,
                person=person,
                relation=AccountPersonLink.Relation.SELF,
                is_primary=True,
            )
            _record_audit(
                AuditLog.Action.CREATE,
                "students.AccountPersonLink",
                str(link.pk),
                {"account_id": account.pk, "person_id": person.pk},
            )
    except IntegrityError:
        # Race: 2 convert song song cùng SĐT đã tạo primary trước → retry get
        # silent. Savepoint đã rollback phần partial. KHÔNG raise — convert
        # outer vẫn commit (Enrollment + Lead).
        logger.warning(
            "Auto-provision race condition cho phone=%s — primary Link đã tồn "
            "tại từ convert song song. Bỏ qua.",
            masked,
        )
    except DatabaseError as exc:
        # Lỗi DB nghiêm trọng (OperationalError = connection drop / deadlock,
        # ProgrammingError = SQL syntax bug, DataError = value out of range).
        # KHÁC IntegrityError ở chỗ KHÔNG phải race lành tính — DB có thể đang
        # unhealthy. Log ERROR (cao hơn warning) để monitoring/Sentry alert
        # ops. KHÔNG raise vì intent "thà có Enrollment không Account": vỡ
        # outer convert làm sale phải retry toàn flow.
        logger.exception(
            "Auto-provision DatabaseError cho phone=%s (%s): %s. DB có thể "
            "đang unhealthy, cần kiểm tra ngay.",
            masked,
            type(exc).__name__,
            exc,
        )
    except Exception as exc:  # noqa: BLE001
        # Lỗi business logic / không phải DB. Auto-provision không được làm
        # vỡ convert. Log + savepoint rollback.
        logger.exception(
            "Auto-provision StudentAccount lỗi cho phone=%s: %s", masked, exc
        )
