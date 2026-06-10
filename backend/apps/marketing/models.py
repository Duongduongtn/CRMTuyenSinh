"""
App `marketing` — tích hợp nguồn lead bên ngoài (Sprint 3 Tuần 6).

Hiện tại chỉ có FB Lead Ads webhook (Facebook Page → khi user submit Lead Ad
form, Facebook bắn webhook về backend). Tương lai có thể thêm TikTok Lead Ads,
Zalo Click-to-Lead, Google Ads conversion.

Lưu raw payload để truy vết khi Facebook đổi schema hoặc xử lý lỗi cần audit.
"""
from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _


class FBLeadAdsEvent(models.Model):
    """Raw event Facebook gửi qua webhook.

    Mỗi Lead trên Facebook = 1 record. Lưu để truy vết khi Facebook đổi field
    + hỗ trợ idempotent (lead_id duy nhất). Sau khi xử lý xong sẽ link sang
    ``leads.Lead`` đã tạo trong CRM.
    """

    class Status(models.TextChoices):
        RECEIVED = "received", _("Đã nhận")
        PROCESSED = "processed", _("Đã chuyển vào CRM")
        DUPLICATE = "duplicate", _("Trùng lead đã có")
        FAILED = "failed", _("Lỗi xử lý")

    leadgen_id = models.CharField(
        _("Lead ID (Facebook)"),
        max_length=64,
        unique=True,
        db_index=True,
        help_text=_("Idempotent key. FB có thể bắn webhook nhiều lần cùng 1 lead."),
    )
    form_id = models.CharField(_("Form ID"), max_length=64, blank=True, default="")
    page_id = models.CharField(_("Page ID"), max_length=64, blank=True, default="")
    ad_id = models.CharField(_("Ad ID"), max_length=64, blank=True, default="")
    adgroup_id = models.CharField(_("AdGroup ID"), max_length=64, blank=True, default="")
    campaign_id = models.CharField(_("Campaign ID"), max_length=64, blank=True, default="")
    created_time = models.DateTimeField(_("FB tạo lúc"), null=True, blank=True)

    raw_payload = models.JSONField(_("Raw payload"), blank=True, null=True)
    field_data = models.JSONField(
        _("Câu trả lời form"),
        blank=True,
        null=True,
        help_text=_("Dict {field_name: value} sau khi parse từ Graph API."),
    )

    status = models.CharField(
        _("Trạng thái"),
        max_length=20,
        choices=Status.choices,
        default=Status.RECEIVED,
    )
    error_message = models.CharField(
        _("Lỗi"),
        max_length=500,
        blank=True,
        default="",
    )
    matched_lead = models.ForeignKey(
        "leads.Lead",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="fb_lead_ads_events",
        verbose_name=_("Lead trong CRM"),
    )
    processed_at = models.DateTimeField(_("Xử lý lúc"), null=True, blank=True)

    received_at = models.DateTimeField(_("Webhook nhận lúc"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Cập nhật"), auto_now=True)

    class Meta:
        verbose_name = _("Lead FB Ads")
        verbose_name_plural = _("Lead FB Ads")
        ordering = ["-received_at"]
        indexes = [
            models.Index(fields=["status", "-received_at"]),
            models.Index(fields=["page_id", "-received_at"]),
        ]

    def __str__(self) -> str:
        return f"FB Lead {self.leadgen_id} · {self.get_status_display()}"
