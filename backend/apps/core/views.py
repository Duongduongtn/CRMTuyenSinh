"""Views app core:

- ``SiteSettingsPublicView`` — GET /api/site-settings (FE public).
- ``IntegrationListView`` — GET /api/admin/integrations/ (superuser, list theo schema).
- ``IntegrationProviderUpdateView`` — PUT /api/admin/integrations/{provider}/ (bulk update).
"""
from __future__ import annotations

import logging

from django.conf import settings as django_settings
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .integrations import INTEGRATION_SCHEMA, invalidate
from .models import AuditLog, IntegrationCredential, SiteSettings
from .serializers import (
    IntegrationCredentialItemSerializer,
    IntegrationProviderUpdateSerializer,
    SiteSettingsPublicSerializer,
)

logger = logging.getLogger("apps.core")


class IsSuperUser(IsAuthenticated):
    """Chỉ superuser (is_superuser=True) — nghiêm ngặt hơn IsAdminUser (chỉ kiểm is_staff)."""

    def has_permission(self, request, view) -> bool:
        return super().has_permission(request, view) and bool(
            request.user and request.user.is_superuser
        )


class SiteSettingsPublicView(APIView):
    """GET /api/site-settings — brand, contact, SEO mặc định cho FE Nuxt.

    Public, không cần auth. FE Nuxt SSG gọi vào lúc build time + 1 lần khi hydrate.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        site = SiteSettings.get_solo()
        return Response(
            SiteSettingsPublicSerializer(site, context={"request": request}).data
        )


def _build_items_for_provider(provider: str) -> list[dict]:
    """Tổ hợp schema + DB record + ENV fallback → list item cho UI."""
    schema = INTEGRATION_SCHEMA[provider]
    records = {
        rec.key: rec
        for rec in IntegrationCredential.objects.filter(provider=provider).select_related(
            "updated_by"
        )
    }
    items: list[dict] = []
    for key, (env_name, label, sensitive, help_text) in schema.items():
        rec = records.get(key)
        db_value = rec.get_value() if rec else ""
        env_value = getattr(django_settings, env_name, "") or ""
        active_value = db_value or env_value
        if db_value:
            source = "db"
        elif env_value:
            source = "env"
        else:
            source = "empty"
        items.append(
            {
                "key": key,
                "label": label,
                "sensitive": sensitive,
                "help_text": help_text,
                "masked": _mask(active_value) if sensitive else active_value,
                "has_value": bool(active_value),
                "source": source,
                "updated_at": rec.updated_at if rec else None,
                "updated_by_username": (
                    rec.updated_by.username if rec and rec.updated_by else ""
                ),
            }
        )
    return items


def _mask(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 4:
        return "****"
    return "****" + value[-4:]


class IntegrationListView(APIView):
    """GET /api/admin/integrations/ — list 4 nhóm credential theo schema.

    Response: {provider: [item, item, ...]}.
    """

    permission_classes = [IsSuperUser]

    def get(self, request):
        data: dict[str, list[dict]] = {}
        for provider in INTEGRATION_SCHEMA.keys():
            items = _build_items_for_provider(provider)
            data[provider] = IntegrationCredentialItemSerializer(items, many=True).data
        return Response(data)


class IntegrationProviderUpdateView(APIView):
    """PUT /api/admin/integrations/{provider}/ — bulk update credential 1 nhóm.

    Body: {key: plaintext_value, ...} chỉ chứa key thuộc schema. Empty = clear.
    Audit log: 1 AuditLog cho mỗi provider PUT (changes liệt kê key đã đổi, KHÔNG log plaintext).
    """

    permission_classes = [IsSuperUser]

    def put(self, request, provider: str):
        if provider not in INTEGRATION_SCHEMA:
            return Response(
                {"detail": f"Provider không hợp lệ: {provider}"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Bảo đảm Fernet cipher build được trước khi encrypt. Khi FERNET_SECRET
        # chưa cấu hình hoặc đang dùng dev default, raise ImproperlyConfigured
        # → trả 503 với hướng dẫn thay vì 500 crash.
        from django.core.exceptions import ImproperlyConfigured

        from .crypto import get_cipher, reset_cipher_cache

        try:
            reset_cipher_cache()
            get_cipher()
        except ImproperlyConfigured as exc:
            return Response(
                {
                    "detail": (
                        "FERNET_SECRET chưa cấu hình ở prod. Cấp key qua docs/08 §2 "
                        "rồi restart backend."
                    ),
                    "hint": str(exc),
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        serializer = IntegrationProviderUpdateSerializer(
            data=request.data, provider=provider
        )
        serializer.is_valid(raise_exception=True)
        cleaned: dict[str, str] = serializer.validated_data["_cleaned"]

        # Cache hiện trạng để biết key nào đổi (audit log).
        existing = {
            rec.key: rec
            for rec in IntegrationCredential.objects.filter(provider=provider)
        }

        keys_changed: list[str] = []
        keys_cleared: list[str] = []
        for key, new_plaintext in cleaned.items():
            old_value = existing[key].get_value() if key in existing else ""

            # Bỏ qua khi không đổi (giảm noise audit log + tránh re-encrypt redundant).
            if new_plaintext == old_value:
                continue

            rec = existing.get(key) or IntegrationCredential(provider=provider, key=key)
            rec.set_value(new_plaintext)
            rec.updated_by = request.user if request.user.is_authenticated else None
            rec.save()
            invalidate(provider, key)

            if new_plaintext:
                keys_changed.append(key)
            else:
                keys_cleared.append(key)

        # Audit log: chỉ ghi khi có thay đổi.
        if keys_changed or keys_cleared:
            AuditLog.objects.create(
                user=request.user if request.user.is_authenticated else None,
                action=AuditLog.Action.UPDATE,
                target_model="IntegrationCredential",
                target_id=provider,
                changes={
                    "keys_changed": keys_changed,
                    "keys_cleared": keys_cleared,
                },
                ip_address=_get_client_ip(request),
                user_agent=request.META.get("HTTP_USER_AGENT", "")[:255],
            )

        # Trả lại state sau update.
        items = _build_items_for_provider(provider)
        return Response(
            {
                "provider": provider,
                "keys_changed": keys_changed,
                "keys_cleared": keys_cleared,
                "items": IntegrationCredentialItemSerializer(items, many=True).data,
            }
        )


def _get_client_ip(request) -> str | None:
    """X-Forwarded-For (chỉ tin nếu TRUST_X_FORWARDED_FOR) hoặc REMOTE_ADDR."""
    if getattr(django_settings, "TRUST_X_FORWARDED_FOR", False):
        xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if xff:
            return xff.split(",")[0].strip() or None
    return request.META.get("REMOTE_ADDR") or None
