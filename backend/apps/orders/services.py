"""Service layer cho orders — tách logic convert lead → enrollment khỏi view.

Lý do tách: dùng được trong CLI/Celery/admin action mà không lệ thuộc DRF request.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.courses.models import Course
from apps.leads.models import Lead

from .models import Enrollment, EnrollmentStatus


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

        return ConvertResult(enrollment=enrollment, created=True)
