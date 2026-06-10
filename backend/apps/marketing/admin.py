"""Admin app marketing — view raw FB leadgen event để truy vết."""
from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin

from .models import FBLeadAdsEvent


@admin.register(FBLeadAdsEvent)
class FBLeadAdsEventAdmin(ModelAdmin):
    list_display = (
        "leadgen_id",
        "status_badge",
        "page_id",
        "campaign_id",
        "matched_lead_link",
        "received_at",
        "processed_at",
    )
    list_filter = ("status", "page_id")
    search_fields = ("leadgen_id", "form_id", "campaign_id", "page_id")
    readonly_fields = (
        "leadgen_id",
        "form_id",
        "page_id",
        "ad_id",
        "adgroup_id",
        "campaign_id",
        "created_time",
        "raw_payload",
        "field_data",
        "matched_lead",
        "received_at",
        "processed_at",
        "updated_at",
    )
    date_hierarchy = "received_at"

    @admin.display(description="Trạng thái", ordering="status")
    def status_badge(self, obj: FBLeadAdsEvent) -> str:
        colors = {
            FBLeadAdsEvent.Status.RECEIVED: "#94A3B8",
            FBLeadAdsEvent.Status.PROCESSED: "#15803D",
            FBLeadAdsEvent.Status.DUPLICATE: "#0EA5E9",
            FBLeadAdsEvent.Status.FAILED: "#B91C1C",
        }
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;'
            'border-radius:4px;font-size:11px;font-weight:600;">{}</span>',
            colors.get(obj.status, "#000"),
            obj.get_status_display(),
        )

    @admin.display(description="Lead CRM")
    def matched_lead_link(self, obj: FBLeadAdsEvent) -> str:
        if not obj.matched_lead_id:
            return "—"
        return format_html(
            '<a href="/admin/leads/lead/{}/change/">#{}</a>',
            obj.matched_lead_id,
            obj.matched_lead_id,
        )

    def has_add_permission(self, request) -> bool:
        return False
