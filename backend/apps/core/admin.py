"""Admin cho app core. SiteSettings dùng SingletonModelAdmin để chỉ có 1 record."""
from django.contrib import admin
from solo.admin import SingletonModelAdmin
from unfold.admin import ModelAdmin

from .models import AuditLog, SiteSettings, SystemSetting


@admin.register(SiteSettings)
class SiteSettingsAdmin(SingletonModelAdmin, ModelAdmin):
    """Trang chỉnh thông tin trung tâm. Hiển thị 1 form duy nhất, không cho tạo mới/xóa."""

    fieldsets = (
        (
            "Tên và thương hiệu",
            {"fields": ("brand_name", "brand_short_name", "slogan", "description")},
        ),
        (
            "Hình ảnh",
            {"fields": ("logo", "favicon", "og_image")},
        ),
        (
            "Liên hệ",
            {"fields": ("hotline", "hotline_display", "email")},
        ),
        (
            "Địa chỉ",
            {
                "fields": (
                    "address_line",
                    "ward",
                    "district",
                    "city",
                    ("map_lat", "map_lng"),
                    "map_embed_url",
                )
            },
        ),
        (
            "Giờ làm việc và mạng xã hội",
            {
                "fields": (
                    "working_hours_text",
                    "facebook_url",
                    "zalo_oa_id",
                    "zalo_url",
                    "youtube_url",
                    "tiktok_url",
                )
            },
        ),
        (
            "Thông tin pháp lý",
            {"fields": ("license_info", "company_full_name", "tax_code")},
        ),
        (
            "SEO mặc định",
            {"fields": ("meta_title_default", "meta_description_default")},
        ),
        (
            "Số liệu hiển thị trên FE",
            {
                "fields": (
                    "stat_students_count",
                    "stat_pass_rate_percent",
                    "stat_years_experience",
                    "stat_practice_area_m2",
                ),
                "description": "Cập nhật thủ công định kỳ. FE pull qua API site-settings.",
            },
        ),
    )


@admin.register(SystemSetting)
class SystemSettingAdmin(ModelAdmin):
    list_display = ("key", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("key", "description")
    readonly_fields = ("created_at", "updated_at")


@admin.register(AuditLog)
class AuditLogAdmin(ModelAdmin):
    list_display = ("created_at", "user", "action", "target_model", "target_id")
    list_filter = ("action", "target_model")
    search_fields = ("target_id", "user__username", "user__phone")
    readonly_fields = (
        "user",
        "action",
        "target_model",
        "target_id",
        "changes",
        "ip_address",
        "user_agent",
        "created_at",
    )
    ordering = ("-created_at",)

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        # Cho admin xóa log cũ nếu cần (theo policy giữ 1 năm).
        return request.user.is_superuser
