"""Admin blog (django-unfold)."""
from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin

from .models import BlogCategory, BlogPost, BlogPostStatus


@admin.register(BlogCategory)
class BlogCategoryAdmin(ModelAdmin):
    list_display = ("name", "slug", "is_active", "sort_order")
    list_filter = ("is_active",)
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "slug")


@admin.register(BlogPost)
class BlogPostAdmin(ModelAdmin):
    list_display = ("title", "category", "status_badge", "published_at", "view_count", "is_featured")
    list_filter = ("status", "category", "is_featured")
    search_fields = ("title", "slug", "excerpt")
    date_hierarchy = "published_at"
    autocomplete_fields = ("category", "author")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("view_count", "created_at", "updated_at")
    fieldsets = (
        ("Cơ bản", {
            "fields": ("title", "slug", "category", "excerpt", "content_md"),
        }),
        ("Ảnh", {
            "fields": ("cover_image", "cover_alt", "og_image"),
        }),
        ("SEO", {
            "fields": ("meta_title", "meta_description", "canonical_url"),
        }),
        ("Xuất bản", {
            "fields": ("status", "published_at", "author", "is_featured", "read_time_minutes"),
        }),
        ("Thống kê", {
            "fields": ("view_count", "created_at", "updated_at"),
        }),
    )

    @admin.display(description="Trạng thái", ordering="status")
    def status_badge(self, obj: BlogPost) -> str:
        colors = {
            BlogPostStatus.DRAFT: ("#94A3B8", "Nháp"),
            BlogPostStatus.PUBLISHED: ("#15803D", "Xuất bản"),
            BlogPostStatus.ARCHIVED: ("#7C3AED", "Lưu trữ"),
        }
        color, label = colors.get(obj.status, ("#000", obj.status))
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;'
            'border-radius:4px;font-size:11px;font-weight:600;">{}</span>',
            color, label,
        )

    def save_model(self, request, obj, form, change):
        if not obj.author_id:
            obj.author = request.user
        super().save_model(request, obj, form, change)
