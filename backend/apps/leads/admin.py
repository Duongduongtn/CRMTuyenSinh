"""Admin cho app leads. UI tạm thời dùng Django admin (django-unfold), Vue SPA sẽ build đẹp ở Sprint 2-3."""
from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline

from .models import Lead, LeadContact, LeadNote, LeadReason, LeadStatus


@admin.register(LeadReason)
class LeadReasonAdmin(ModelAdmin):
    list_display = ("name", "status_scope", "sort_order", "is_active")
    list_filter = ("status_scope", "is_active")
    list_editable = ("sort_order", "is_active")
    search_fields = ("name",)


class LeadContactInline(TabularInline):
    model = LeadContact
    extra = 0
    fields = (
        "created_at",
        "user",
        "contact_type",
        "status_before",
        "status_after",
        "priority_after",
        "reason",
        "note",
        "next_contact_date",
    )
    readonly_fields = ("created_at", "status_before", "status_after")
    ordering = ("-created_at",)
    can_delete = False
    show_change_link = True


class LeadNoteInline(TabularInline):
    model = LeadNote
    extra = 0
    fields = ("created_at", "user", "content")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)


@admin.register(Lead)
class LeadAdmin(ModelAdmin):
    list_display = (
        "name",
        "phone",
        "vehicle_class",
        "status_badge",
        "priority_badge",
        "assigned_to",
        "contact_count",
        "next_contact_date",
        "created_at",
    )
    list_filter = (
        "status",
        "priority",
        "vehicle_class",
        "source",
        "assigned_to",
        "converted_to_order",
    )
    search_fields = ("name", "phone", "email", "address")
    date_hierarchy = "created_at"
    autocomplete_fields = ("assigned_to", "reason")

    fieldsets = (
        (
            "Khách hàng",
            {"fields": (("name", "phone"), "email", ("district", "address"), "vehicle_class", "notes")},
        ),
        (
            "Trạng thái và phân công",
            {
                "fields": (
                    ("status", "priority"),
                    "assigned_to",
                    ("reason", "reason_text"),
                    "next_contact_date",
                )
            },
        ),
        (
            "Theo dõi liên hệ",
            {
                "fields": (
                    "contact_count",
                    "last_contact_at",
                    "last_contact_by",
                )
            },
        ),
        (
            "Nguồn lead",
            {
                "classes": ("collapse",),
                "fields": (
                    ("source", "source_page", "source_title"),
                    ("utm_source", "utm_medium", "utm_campaign"),
                    ("utm_content", "utm_term"),
                    ("device_type", "device_os", "device_browser", "screen_size"),
                    ("ip_address", "user_agent"),
                ),
            },
        ),
        (
            "Chuyển đổi",
            {
                "classes": ("collapse",),
                "fields": ("converted_to_order", "order_code", "converted_at"),
            },
        ),
    )
    readonly_fields = ("contact_count", "last_contact_at", "last_contact_by", "converted_at")
    inlines = [LeadContactInline, LeadNoteInline]

    @admin.display(description="Trạng thái", ordering="status")
    def status_badge(self, obj: Lead) -> str:
        colors = {
            LeadStatus.NEW: ("#94A3B8", "Chưa LH"),
            LeadStatus.FOLLOWING: ("#D97706", "Đang theo dõi"),
            LeadStatus.SUCCESS: ("#15803D", "Thành công"),
            LeadStatus.FAILED: ("#B91C1C", "Thất bại"),
        }
        color, label = colors.get(obj.status, ("#000", obj.status))
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;">{}</span>',
            color,
            label,
        )

    @admin.display(description="Độ nóng", ordering="priority")
    def priority_badge(self, obj: Lead) -> str:
        if not obj.priority:
            return "—"
        icons = {"hot": "🔥", "warm": "🌡️", "cold": "❄️"}
        labels = {"hot": "Nóng", "warm": "Ấm", "cold": "Lạnh"}
        return format_html("{} {}", icons.get(obj.priority, ""), labels.get(obj.priority, obj.priority))

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("assigned_to", "last_contact_by", "reason")


@admin.register(LeadContact)
class LeadContactAdmin(ModelAdmin):
    list_display = ("created_at", "lead", "user", "contact_type", "status_after", "priority_after")
    list_filter = ("contact_type", "status_after", "priority_after")
    search_fields = ("lead__name", "lead__phone", "note")
    date_hierarchy = "created_at"
    autocomplete_fields = ("lead", "user", "reason")


@admin.register(LeadNote)
class LeadNoteAdmin(ModelAdmin):
    list_display = ("created_at", "lead", "user")
    search_fields = ("lead__name", "content")
    autocomplete_fields = ("lead", "user")
