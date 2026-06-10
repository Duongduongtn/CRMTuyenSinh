"""Admin cho app students (django-unfold).

Văn thư + sale có quyền xem/sửa StudentAccount + Person. Admin xem được OTP log
(không thấy code thật, chỉ thấy status + attempts).
"""
from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline

from .models import (
    AccountPersonLink,
    OTPRequest,
    Person,
    StudentAccount,
    StudentDeleteRequest,
)


class AccountPersonLinkInline(TabularInline):
    model = AccountPersonLink
    extra = 0
    fields = ("person", "relation", "is_primary", "created_at")
    readonly_fields = ("created_at",)
    autocomplete_fields = ("person",)


@admin.register(StudentAccount)
class StudentAccountAdmin(ModelAdmin):
    list_display = ("phone", "display_name", "is_active", "last_login_at", "created_at")
    list_filter = ("is_active",)
    search_fields = ("phone", "display_name")
    date_hierarchy = "created_at"
    inlines = [AccountPersonLinkInline]
    readonly_fields = ("last_login_at", "created_at", "updated_at")


@admin.register(Person)
class PersonAdmin(ModelAdmin):
    list_display = ("full_name", "id_number_mask", "gender", "date_of_birth", "created_at")
    list_filter = ("gender",)
    search_fields = ("full_name", "id_number")
    date_hierarchy = "created_at"
    readonly_fields = ("created_at", "updated_at")

    @admin.display(description="Số CCCD")
    def id_number_mask(self, obj: Person) -> str:
        """Mask CCCD chỉ hiện 4 số cuối trong list (chống lộ PII trên màn hình).

        Detail view vẫn xem được số đầy đủ. View detail cũng được audit qua
        AuditLog (Sprint 3).
        """
        if not obj.id_number:
            return "—"
        if len(obj.id_number) <= 4:
            return obj.id_number
        return "•" * (len(obj.id_number) - 4) + obj.id_number[-4:]


@admin.register(AccountPersonLink)
class AccountPersonLinkAdmin(ModelAdmin):
    list_display = ("account", "person", "relation", "is_primary", "created_at")
    list_filter = ("relation", "is_primary")
    search_fields = ("account__phone", "person__full_name")
    autocomplete_fields = ("account", "person")


@admin.register(OTPRequest)
class OTPRequestAdmin(ModelAdmin):
    """Admin OTP — KHÔNG hiển thị code_hash trong list/detail.

    Chỉ admin thấy được trạng thái + audit log gửi.
    """

    list_display = ("created_at", "phone", "purpose", "status_badge", "attempts", "sent_via")
    list_filter = ("status", "purpose", "sent_via")
    search_fields = ("phone",)
    date_hierarchy = "created_at"
    readonly_fields = (
        "phone",
        "purpose",
        "status",
        "attempts",
        "ip_address",
        "user_agent",
        "expires_at",
        "consumed_at",
        "sent_via",
        "sent_meta",
        "created_at",
    )

    def has_add_permission(self, request):
        return False  # OTP chỉ tạo qua API

    @admin.display(description="Trạng thái", ordering="status")
    def status_badge(self, obj: OTPRequest) -> str:
        colors = {
            OTPRequest.Status.PENDING: ("#F59E0B", "Chờ"),
            OTPRequest.Status.VERIFIED: ("#15803D", "Đã xác thực"),
            OTPRequest.Status.CONSUMED: ("#15803D", "Đã dùng"),
            OTPRequest.Status.EXPIRED: ("#94A3B8", "Hết hạn"),
        }
        color, label = colors.get(obj.status, ("#000", obj.status))
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;'
            'border-radius:4px;font-size:11px;font-weight:600;">{}</span>',
            color,
            label,
        )

    def get_fields(self, request, obj=None):
        # Loại bỏ code_hash khỏi UI hoàn toàn.
        return [f for f in self.readonly_fields if f != "code_hash"]


@admin.register(StudentDeleteRequest)
class StudentDeleteRequestAdmin(ModelAdmin):
    """Quản lý yêu cầu xóa dữ liệu HV (NĐ 13/2023).

    Văn thư + admin xử lý: đọc lý do, đối soát công nợ trong CRM, rồi quyết
    định ``approved`` (sẽ xóa thủ công) hoặc ``rejected`` (kèm lý do, gọi HV
    giải thích). KHÔNG có nút "xóa tự động" — thao tác xóa phải do người thực
    hiện để tránh mất dữ liệu nhầm.
    """

    list_display = ("created_at", "account", "status_badge", "handled_by", "telegram_sent_at")
    list_filter = ("status",)
    search_fields = ("account__phone", "reason")
    date_hierarchy = "created_at"
    autocomplete_fields = ("account", "handled_by")
    readonly_fields = (
        "account",
        "reason",
        "ip_address",
        "user_agent",
        "telegram_sent_at",
        "created_at",
        "updated_at",
    )
    fieldsets = (
        ("Yêu cầu của học viên", {"fields": ("account", "reason", "created_at")}),
        (
            "Xử lý",
            {
                "fields": (
                    "status",
                    "handler_note",
                    "handled_by",
                    "handled_at",
                )
            },
        ),
        (
            "Audit",
            {
                "classes": ("collapse",),
                "fields": (
                    "ip_address",
                    "user_agent",
                    "telegram_sent_at",
                    "updated_at",
                ),
            },
        ),
    )

    def has_add_permission(self, request) -> bool:
        return False  # Chỉ tạo qua API HV

    @admin.display(description="Trạng thái", ordering="status")
    def status_badge(self, obj: StudentDeleteRequest) -> str:
        colors = {
            StudentDeleteRequest.Status.RECEIVED: "#F59E0B",
            StudentDeleteRequest.Status.IN_REVIEW: "#0EA5E9",
            StudentDeleteRequest.Status.APPROVED: "#15803D",
            StudentDeleteRequest.Status.REJECTED: "#B91C1C",
            StudentDeleteRequest.Status.COMPLETED: "#7C3AED",
        }
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;'
            'border-radius:4px;font-size:11px;font-weight:600;">{}</span>',
            colors.get(obj.status, "#000"),
            obj.get_status_display(),
        )
