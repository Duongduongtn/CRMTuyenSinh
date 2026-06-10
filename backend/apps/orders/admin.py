"""Admin cho app orders (django-unfold)."""
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from unfold.admin import ModelAdmin

from .models import Enrollment, EnrollmentStatus


@admin.register(Enrollment)
class EnrollmentAdmin(ModelAdmin):
    list_display = (
        "code",
        "student_name",
        "student_phone",
        "course",
        "vehicle_class",
        "status_badge",
        "deposit_progress",
        "print_pdf_link",
        "created_by",
        "created_at",
    )
    list_filter = ("status", "vehicle_class", "course", "created_by")
    search_fields = ("code", "student_name", "student_phone", "student_email")
    date_hierarchy = "created_at"
    autocomplete_fields = ("lead", "course", "created_by")
    readonly_fields = (
        "code",
        "deposit_link_token",
        "paid_amount",
        "created_at",
        "updated_at",
        "deposit_paid_at",
        "completed_at",
    )

    fieldsets = (
        (
            "Đơn",
            {
                "fields": (
                    "code",
                    ("lead", "course"),
                    ("status", "vehicle_class"),
                )
            },
        ),
        (
            "Học viên",
            {
                "fields": (
                    ("student_name", "student_phone"),
                    "student_email",
                )
            },
        ),
        (
            "Tài chính",
            {
                "fields": (
                    ("tuition_fee", "deposit_amount"),
                    "paid_amount",
                )
            },
        ),
        ("Ghi chú", {"fields": ("notes",)}),
        (
            "Thời gian + nội bộ",
            {
                "classes": ("collapse",),
                "fields": (
                    "created_by",
                    "deposit_link_token",
                    ("deposit_paid_at", "completed_at"),
                    ("created_at", "updated_at"),
                ),
            },
        ),
    )

    @admin.display(description="Trạng thái", ordering="status")
    def status_badge(self, obj: Enrollment) -> str:
        colors = {
            EnrollmentStatus.PENDING: ("#94A3B8", "Chờ cọc"),
            EnrollmentStatus.DEPOSITED: ("#0EA5E9", "Đã cọc"),
            EnrollmentStatus.PARTIAL: ("#F59E0B", "Đóng một phần"),
            EnrollmentStatus.COMPLETED: ("#15803D", "Đã đóng đủ"),
            EnrollmentStatus.CANCELLED: ("#B91C1C", "Đã hủy"),
            EnrollmentStatus.REFUNDED: ("#7C3AED", "Đã hoàn"),
        }
        color, label = colors.get(obj.status, ("#000", obj.status))
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;'
            'border-radius:4px;font-size:11px;font-weight:600;">{}</span>',
            color,
            label,
        )

    @admin.display(description="Đã đóng / Tổng")
    def deposit_progress(self, obj: Enrollment) -> str:
        paid = f"{int(obj.paid_amount):,}".replace(",", ".")
        total = f"{int(obj.tuition_fee):,}".replace(",", ".")
        return format_html("{} / {} đ", paid, total)

    @admin.display(description="Đơn PDF")
    def print_pdf_link(self, obj: Enrollment) -> str:
        url = reverse("enrollment-pdf", args=[obj.pk])
        return format_html(
            '<a href="{}" target="_blank" rel="noopener" '
            'style="display:inline-flex;align-items:center;gap:4px;'
            'padding:2px 10px;border-radius:6px;background:#ecfdf5;'
            'color:#047857;font-size:11px;font-weight:600;'
            'border:1px solid #a7f3d0;">In PDF</a>',
            url,
        )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("course", "created_by", "lead")
