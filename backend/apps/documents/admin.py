"""Admin văn thư duyệt hồ sơ.

Văn thư có:
- Xem list pending → click duyệt/từ chối hàng loạt
- Upload hộ HV (nếu HV trung niên không quen smartphone)
- Xem preview file (image inline, PDF link)
"""
from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from unfold.admin import ModelAdmin

from .models import DocumentStatus, DocumentType, EnrollmentDocument, PersonDocument


@admin.register(DocumentType)
class DocumentTypeAdmin(ModelAdmin):
    list_display = ("name", "code", "scope", "is_required", "is_active", "sort_order")
    list_filter = ("scope", "is_required", "is_active")
    search_fields = ("code", "name")


class DocReviewMixin:
    """Action duyệt/từ chối hàng loạt — dùng chung cho PersonDocument và EnrollmentDocument."""

    actions = ("approve_selected", "reject_selected")
    list_filter = ("status", "document_type")
    date_hierarchy = "created_at"
    readonly_fields = (
        "mime_type",
        "file_size",
        "uploaded_by_account",
        "uploaded_by_staff",
        "created_at",
        "updated_at",
        "preview",
    )

    @admin.display(description="Xem trước")
    def preview(self, obj):
        if not obj.file:
            return "—"
        url = obj.file.url
        if obj.mime_type.startswith("image/"):
            return mark_safe(
                f'<img src="{url}" style="max-width:320px;max-height:240px;border-radius:8px;" />'
            )
        return mark_safe(
            f'<a href="{url}" target="_blank" rel="noopener">Mở file</a> '
            f'<span style="color:#666;">({obj.mime_type or "không rõ"})</span>'
        )

    @admin.display(description="Trạng thái", ordering="status")
    def status_badge(self, obj):
        colors = {
            DocumentStatus.PENDING_REVIEW: ("#F59E0B", "Chờ duyệt"),
            DocumentStatus.APPROVED: ("#15803D", "Đã duyệt"),
            DocumentStatus.REJECTED: ("#B91C1C", "Từ chối"),
            DocumentStatus.EXPIRED: ("#94A3B8", "Hết hạn"),
            DocumentStatus.PURGED: ("#7C3AED", "Đã xóa"),
        }
        color, label = colors.get(obj.status, ("#000", obj.status))
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;'
            'border-radius:4px;font-size:11px;font-weight:600;">{}</span>',
            color, label,
        )

    @admin.action(description="Duyệt các tài liệu đã chọn")
    def approve_selected(self, request, queryset):
        now = timezone.now()
        updated = queryset.filter(status=DocumentStatus.PENDING_REVIEW).update(
            status=DocumentStatus.APPROVED,
            reviewed_by=request.user,
            reviewed_at=now,
        )
        self.message_user(request, f"Đã duyệt {updated} tài liệu.")

    @admin.action(description="Từ chối các tài liệu đã chọn")
    def reject_selected(self, request, queryset):
        now = timezone.now()
        updated = queryset.filter(status=DocumentStatus.PENDING_REVIEW).update(
            status=DocumentStatus.REJECTED,
            reviewed_by=request.user,
            reviewed_at=now,
        )
        self.message_user(request, f"Đã từ chối {updated} tài liệu.")


@admin.register(PersonDocument)
class PersonDocumentAdmin(DocReviewMixin, ModelAdmin):
    list_display = ("created_at", "person", "document_type", "status_badge", "reviewed_by")
    search_fields = ("person__full_name", "person__id_number")
    autocomplete_fields = ("person", "document_type")
    fields = (
        "person",
        "document_type",
        "file",
        "preview",
        "status",
        "review_note",
        "uploaded_by_account",
        "uploaded_by_staff",
        "reviewed_by",
        "reviewed_at",
        "expires_at",
        "mime_type",
        "file_size",
        "created_at",
        "updated_at",
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            "person", "document_type", "reviewed_by", "uploaded_by_account",
        )


@admin.register(EnrollmentDocument)
class EnrollmentDocumentAdmin(DocReviewMixin, ModelAdmin):
    list_display = ("created_at", "enrollment", "document_type", "status_badge", "reviewed_by")
    search_fields = ("enrollment__code", "enrollment__student_name")
    autocomplete_fields = ("enrollment", "document_type")
    fields = (
        "enrollment",
        "document_type",
        "file",
        "preview",
        "status",
        "review_note",
        "uploaded_by_account",
        "uploaded_by_staff",
        "reviewed_by",
        "reviewed_at",
        "expires_at",
        "mime_type",
        "file_size",
        "created_at",
        "updated_at",
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            "enrollment", "document_type", "reviewed_by", "uploaded_by_account",
        )
