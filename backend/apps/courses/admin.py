"""Admin khóa học."""
from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Course


@admin.register(Course)
class CourseAdmin(ModelAdmin):
    list_display = (
        "title",
        "vehicle_class_display",
        "vehicle_group",
        "tuition_fee_display",
        "available_slots",
        "is_visible",
        "is_featured",
    )
    list_filter = ("vehicle_group", "is_visible", "is_featured")
    search_fields = ("title", "slug", "vehicle_class")
    list_editable = ("is_visible", "is_featured")
    prepopulated_fields = {"slug": ("title",)}

    fieldsets = (
        (
            "Thông tin cơ bản",
            {"fields": ("title", "slug", "vehicle_class", "vehicle_group", "short_description")},
        ),
        (
            "Mô tả chi tiết",
            {"fields": ("description_md",)},
        ),
        (
            "Học phí",
            {"fields": ("tuition_fee", "deposit_amount")},
        ),
        (
            "Thời lượng và slot",
            {"fields": (("duration_days", "duration_display"), ("total_slots", "available_slots"))},
        ),
        (
            "Ảnh và SEO",
            {"fields": ("cover_image", "meta_title", "meta_description", "og_image")},
        ),
        (
            "Hiển thị FE public",
            {"fields": ("is_visible", "is_featured", "sort_order")},
        ),
    )

    @admin.display(description="Hạng", ordering="vehicle_class")
    def vehicle_class_display(self, obj: Course) -> str:
        return obj.vehicle_class

    @admin.display(description="Học phí", ordering="tuition_fee")
    def tuition_fee_display(self, obj: Course) -> str:
        # Format số kiểu VN: 17.500.000đ
        return f"{int(obj.tuition_fee):,}đ".replace(",", ".")
