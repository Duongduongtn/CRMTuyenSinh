"""
App `blog` — tin tức/blog SEO.

Mục tiêu: kéo traffic SEO trên các từ khóa "học lái xe", "đổi GPLX", "luật mới 2025".

- ``BlogCategory``: chuyên mục (tin trung tâm, hướng dẫn, luật mới).
- ``BlogPost``: bài viết. Markdown trong DB, render trên FE Nuxt.

KHÔNG có tag system phức tạp v1 — categories đủ cho 5-10 bài/tháng đầu.
"""
from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _


class BlogCategory(models.Model):
    name = models.CharField(_("Tên chuyên mục"), max_length=100)
    slug = models.SlugField(_("Slug"), max_length=120, unique=True)
    description = models.CharField(_("Mô tả"), max_length=255, blank=True, default="")
    sort_order = models.PositiveSmallIntegerField(_("Thứ tự"), default=100)
    is_active = models.BooleanField(_("Hiển thị"), default=True)
    meta_title = models.CharField(_("Meta title"), max_length=70, blank=True, default="")
    meta_description = models.CharField(_("Meta description"), max_length=170, blank=True, default="")

    class Meta:
        verbose_name = _("Chuyên mục blog")
        verbose_name_plural = _("Chuyên mục blog")
        ordering = ["sort_order", "name"]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:120]
        super().save(*args, **kwargs)


class BlogPostStatus(models.TextChoices):
    DRAFT = "draft", _("Bản nháp")
    PUBLISHED = "published", _("Đã xuất bản")
    ARCHIVED = "archived", _("Lưu trữ")


class BlogPost(models.Model):
    title = models.CharField(_("Tiêu đề"), max_length=200)
    slug = models.SlugField(_("Slug"), max_length=220, unique=True)
    category = models.ForeignKey(
        BlogCategory,
        on_delete=models.PROTECT,
        related_name="posts",
        verbose_name=_("Chuyên mục"),
    )
    excerpt = models.CharField(
        _("Tóm tắt"),
        max_length=300,
        blank=True,
        default="",
        help_text=_("2-3 câu hiển thị trên card và meta description nếu trống."),
    )
    content_md = models.TextField(
        _("Nội dung (Markdown)"),
        help_text=_("Hỗ trợ Markdown chuẩn — heading, list, code, link, image, blockquote."),
    )

    cover_image = models.ImageField(
        _("Ảnh đại diện"),
        upload_to="blog/%Y/%m/",
        blank=True,
        null=True,
    )
    cover_alt = models.CharField(
        _("Alt ảnh"),
        max_length=200,
        blank=True,
        default="",
        help_text=_("Mô tả ảnh cho SEO + screen reader."),
    )

    # SEO
    meta_title = models.CharField(_("Meta title"), max_length=70, blank=True, default="")
    meta_description = models.CharField(_("Meta description"), max_length=170, blank=True, default="")
    og_image = models.ImageField(_("OG image"), upload_to="blog/og/", blank=True, null=True)
    canonical_url = models.URLField(_("Canonical URL"), blank=True, default="")

    # Tác giả / xuất bản
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="blog_posts",
        verbose_name=_("Tác giả"),
    )
    status = models.CharField(
        _("Trạng thái"),
        max_length=20,
        choices=BlogPostStatus.choices,
        default=BlogPostStatus.DRAFT,
    )
    published_at = models.DateTimeField(_("Xuất bản lúc"), null=True, blank=True, db_index=True)
    is_featured = models.BooleanField(_("Nổi bật"), default=False)

    # Thống kê đơn giản
    view_count = models.PositiveIntegerField(_("Lượt xem"), default=0)
    read_time_minutes = models.PositiveSmallIntegerField(
        _("Thời gian đọc (phút)"),
        default=5,
        help_text=_("Hiển thị trên card. Cập nhật tay hoặc tính từ word count."),
    )

    created_at = models.DateTimeField(_("Tạo lúc"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Cập nhật"), auto_now=True)

    class Meta:
        verbose_name = _("Bài viết")
        verbose_name_plural = _("Bài viết")
        ordering = ["-published_at", "-created_at"]
        indexes = [
            models.Index(fields=["status", "-published_at"]),
            models.Index(fields=["category", "status", "-published_at"]),
            models.Index(fields=["is_featured", "-published_at"]),
        ]

    def __str__(self) -> str:
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)[:220]
        if self.status == BlogPostStatus.PUBLISHED and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)
