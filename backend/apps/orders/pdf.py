"""Render đơn đăng ký học lái xe sang PDF.

Mẫu placeholder dựa trên format Sở GTVT Bình Phước (sẽ thay khi có mẫu chính
thức). Sinh từ HTML template + WeasyPrint để dễ chỉnh khi Sở thay form.

Strategy:
- Template ``orders/enrollment_form.html`` chứa toàn bộ nội dung + CSS print.
- Context lấy từ ``Enrollment`` + ``Person`` (nếu link qua AccountPersonLink) +
  ``SiteSettings`` (brand info, KHÔNG hard-code).
- WeasyPrint render HTML→PDF. Trên Windows cần GTK runtime; nếu chưa cài thì
  ``HTML().write_pdf()`` raise OSError — view sẽ fallback trả HTML preview để
  admin vẫn xem được nội dung.

Font tiếng Việt: dựa trên web font Be Vietnam Pro embed qua URL (Cloudflare hoặc
self-host static). WeasyPrint sẽ fetch khi render — đảm bảo dấu tiếng Việt
hiển thị đúng. Fallback DejaVu Sans nếu không tải được font.
"""
from __future__ import annotations

import logging
from io import BytesIO
from typing import Any

from django.template.loader import render_to_string
from django.utils import timezone

from apps.core.models import SiteSettings
from apps.students.models import AccountPersonLink, Person

from .models import Enrollment

logger = logging.getLogger(__name__)


class PDFRenderError(Exception):
    """Lỗi sinh PDF — caller render HTML preview thay thế."""


def _format_money_vn(amount) -> str:
    """123456789 → ``123.456.789`` (phân cách hàng nghìn dấu chấm VN)."""
    try:
        n = int(amount or 0)
    except (TypeError, ValueError):
        return "0"
    return f"{n:,}".replace(",", ".")


def _format_phone_vn(phone: str) -> str:
    """0903456789 → ``0903.456.789`` (3-3-3)."""
    if not phone or len(phone) != 10:
        return phone or ""
    return f"{phone[:4]}.{phone[4:7]}.{phone[7:]}"


def _format_date_vn(value) -> str:
    if not value:
        return ""
    return value.strftime("%d/%m/%Y")


def _resolve_person(enrollment: Enrollment) -> Person | None:
    """Tìm Person link với SĐT của đơn (nếu HV đã đăng nhập + link).

    Sprint 2 enrollment chưa có FK trực tiếp, tạm dùng AccountPersonLink qua
    SĐT. Khi Sprint 3 thêm FK enrollment.person, đổi sang truy cập trực tiếp.

    Ưu tiên link `is_primary=True` (chính chủ); fallback link đầu tiên — tránh
    case 1 SĐT có nhiều Person (mẹ-con) bị in nhầm CCCD con thay vì mẹ.
    """
    if not enrollment.student_phone:
        return None
    qs = (
        AccountPersonLink.objects
        .select_related("person")
        .filter(account__phone=enrollment.student_phone)
        .order_by("-is_primary", "created_at")
    )
    link = qs.first()
    return link.person if link else None


def _mask_id_number(raw: str) -> str:
    """Mask CCCD trên PDF: 3 đầu + 4 cuối, ở giữa che bằng ``•``.

    `001234567890` → `001•••••7890`. Theo NĐ 13/2023 Điều 21, chỉ hiện full khi
    cần và phải audit chi tiết. v1 mặc định mask trên PDF; admin xem chi tiết
    vẫn ở UI Person admin với audit log riêng.
    """
    if not raw:
        return ""
    digits = "".join(ch for ch in raw if ch.isdigit())
    if len(digits) < 7:
        return raw
    return digits[:3] + "•" * (len(digits) - 7) + digits[-4:]


def build_context(enrollment: Enrollment) -> dict[str, Any]:
    """Gom context cho template PDF — KHÔNG hard-code brand."""
    site = SiteSettings.get_solo()
    person = _resolve_person(enrollment)
    course = enrollment.course
    return {
        "site": site,
        "enrollment": enrollment,
        "person": person,
        "course": course,
        "today": _format_date_vn(timezone.localdate()),
        "formatted": {
            "tuition_fee": _format_money_vn(enrollment.tuition_fee),
            "deposit_amount": _format_money_vn(enrollment.deposit_amount),
            "paid_amount": _format_money_vn(enrollment.paid_amount),
            "remaining_amount": _format_money_vn(enrollment.remaining_amount),
            "student_phone": _format_phone_vn(enrollment.student_phone),
            "person_dob": _format_date_vn(person.date_of_birth) if person else "",
            "id_number": _mask_id_number(person.id_number) if person else "",
            "created_at": enrollment.created_at.strftime("%d/%m/%Y %H:%M"),
            "snapshot_at": timezone.localtime().strftime("%H:%M %d/%m/%Y"),
        },
    }


def render_enrollment_html(enrollment: Enrollment) -> str:
    """Render HTML template để preview hoặc làm input cho WeasyPrint."""
    return render_to_string(
        "orders/enrollment_form.html",
        build_context(enrollment),
    )


def render_enrollment_pdf(enrollment: Enrollment) -> bytes:
    """Sinh PDF bytes. Raise ``PDFRenderError`` nếu WeasyPrint không khả dụng."""
    html_str = render_enrollment_html(enrollment)
    try:
        # Import lazy để app vẫn boot khi WeasyPrint chưa cài (dev Windows).
        from weasyprint import HTML  # type: ignore
    except ImportError as exc:
        raise PDFRenderError(
            "WeasyPrint chưa cài đặt. Chạy `pip install weasyprint` hoặc dùng "
            "endpoint HTML preview."
        ) from exc

    try:
        buf = BytesIO()
        HTML(string=html_str, base_url="/").write_pdf(target=buf)
        return buf.getvalue()
    except OSError as exc:
        logger.exception("WeasyPrint render lỗi (thiếu GTK?): %s", exc)
        raise PDFRenderError(
            "Không sinh được PDF (thiếu GTK runtime trên Windows). "
            "Cài GTK3 hoặc render bản HTML preview."
        ) from exc
