"""Logic chuyển FB Lead Ads payload → ``leads.Lead`` trong CRM.

Tách riêng khỏi view để test dễ + có thể tái dùng cho task reconcile/import.
"""
from __future__ import annotations

import logging
from typing import Any

from django.db import transaction

from apps.leads.models import Lead, LeadSource, LeadStatus
from apps.students.models import normalize_phone

from .models import FBLeadAdsEvent

logger = logging.getLogger("apps.marketing")


# Map field name phổ biến trên FB Lead Ads (VN) → field Lead trong CRM.
# FB cho phép custom tên field → match nhiều biến thể.
PHONE_FIELDS = {"phone_number", "phone", "sdt", "so_dien_thoai", "so dien thoai"}
NAME_FIELDS = {"full_name", "name", "ho_va_ten", "ho va ten", "ten"}
EMAIL_FIELDS = {"email"}
CITY_FIELDS = {"city", "tinh", "tỉnh", "khu_vuc", "khu vuc"}
NOTE_FIELDS = {"message", "notes", "ghi_chu", "ghi chu"}


class FBLeadProcessError(Exception):
    """Lỗi nghiệp vụ khi xử lý FB lead (thiếu phone, raw payload invalid...)."""


def _extract_field_data(field_data_list: list[dict[str, Any]]) -> dict[str, str]:
    """Từ list ``[{name, values}]`` của FB → dict đơn giản ``{name: value}``."""
    result: dict[str, str] = {}
    for item in field_data_list or []:
        name = (item.get("name") or "").strip().lower()
        values = item.get("values") or []
        if name and values:
            result[name] = str(values[0]).strip()
    return result


def _match_first(fields: dict[str, str], candidates: set[str]) -> str:
    for key in candidates:
        if key in fields and fields[key]:
            return fields[key]
    return ""


def process_fb_leadgen(payload: dict[str, Any]) -> FBLeadAdsEvent:
    """Lưu event + tạo ``Lead`` trong CRM nếu chưa có.

    Idempotent: cùng ``leadgen_id`` → trả về event cũ, không tạo Lead trùng.
    """
    leadgen_id = str(payload.get("leadgen_id") or payload.get("id") or "").strip()
    if not leadgen_id:
        raise FBLeadProcessError("Payload không có leadgen_id.")

    field_list = payload.get("field_data") or payload.get("custom_disclaimer_responses") or []
    field_data = _extract_field_data(field_list)

    with transaction.atomic():
        event, created = FBLeadAdsEvent.objects.select_for_update().get_or_create(
            leadgen_id=leadgen_id,
            defaults={
                "form_id": str(payload.get("form_id") or "")[:64],
                "page_id": str(payload.get("page_id") or "")[:64],
                "ad_id": str(payload.get("ad_id") or "")[:64],
                "adgroup_id": str(payload.get("adgroup_id") or "")[:64],
                "campaign_id": str(payload.get("campaign_id") or "")[:64],
                "raw_payload": payload,
                "field_data": field_data,
            },
        )
        if not created:
            logger.info("FB leadgen %s đã xử lý trước đó.", leadgen_id)
            return event

        phone_raw = _match_first(field_data, PHONE_FIELDS)
        phone = normalize_phone(phone_raw) if phone_raw else ""
        name = _match_first(field_data, NAME_FIELDS) or "Khách FB Lead Ads"
        email = _match_first(field_data, EMAIL_FIELDS)
        city = _match_first(field_data, CITY_FIELDS)
        note = _match_first(field_data, NOTE_FIELDS)

        if not phone or len(phone) != 10:
            event.status = FBLeadAdsEvent.Status.FAILED
            event.error_message = "Thiếu hoặc sai định dạng số điện thoại từ FB."
            event.save(update_fields=["status", "error_message", "updated_at"])
            logger.warning(
                "FB lead %s không có SĐT hợp lệ (raw=%s)", leadgen_id, phone_raw
            )
            return event

        # Dedup theo phone trong 7 ngày gần nhất → tránh chạy nhiều campaign trùng.
        from django.utils import timezone

        cutoff = timezone.now() - timezone.timedelta(days=7)
        existing_lead = (
            Lead.objects
            .filter(phone=phone, created_at__gte=cutoff)
            .order_by("-created_at")
            .first()
        )
        if existing_lead:
            event.matched_lead = existing_lead
            event.status = FBLeadAdsEvent.Status.DUPLICATE
            event.processed_at = timezone.now()
            event.save(update_fields=["matched_lead", "status", "processed_at", "updated_at"])
            logger.info(
                "FB lead %s trùng Lead %s tạo trong 7 ngày — bỏ qua tạo mới.",
                leadgen_id, existing_lead.id,
            )
            return event

        lead = Lead.objects.create(
            name=name[:200],
            phone=phone,
            email=email[:254] if email else "",
            district=city[:100],
            notes=note[:2000] if note else "",
            status=LeadStatus.NEW,
            source=LeadSource.FB_ADS,
            source_page=f"facebook.com/{payload.get('page_id', '')}",
            utm_source="facebook",
            utm_medium="lead_ads",
            utm_campaign=str(payload.get("campaign_id") or "")[:100],
            utm_content=str(payload.get("ad_id") or "")[:100],
        )
        event.matched_lead = lead
        event.status = FBLeadAdsEvent.Status.PROCESSED
        from django.utils import timezone as tz

        event.processed_at = tz.now()
        event.save(update_fields=["matched_lead", "status", "processed_at", "updated_at"])

        # Trigger Telegram alert qua signal có sẵn của leads (post_save tự bắn).
        return event
