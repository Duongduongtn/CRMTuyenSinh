"""Views app core:

- ``SiteSettingsPublicView`` — GET /api/site-settings (FE public).
- ``IntegrationListView`` — GET /api/admin/integrations/ (superuser, list theo schema).
- ``IntegrationProviderUpdateView`` — PUT /api/admin/integrations/{provider}/ (bulk update).
"""
from __future__ import annotations

import logging

from django.conf import settings as django_settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.files.storage import default_storage
from django.db import transaction
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .image_uploads import (
    IMAGE_FIELD_SPECS,
    safe_image_filename,
    to_audit_value,
    validate_uploaded_image,
)
from .integrations import INTEGRATION_SCHEMA, invalidate
from .mixins import apply_audited_patch_singleton
from .models import AuditLog, IntegrationCredential, SiteSettings
from .serializers import (
    SITE_SETTINGS_ADMIN_EDITABLE_FIELDS,
    IntegrationCredentialItemSerializer,
    IntegrationProviderUpdateSerializer,
    SiteSettingsAdminSerializer,
    SiteSettingsPublicSerializer,
)

logger = logging.getLogger("apps.core")


class IsSuperUser(IsAuthenticated):
    """Chỉ superuser (is_superuser=True) — nghiêm ngặt hơn IsAdminUser (chỉ kiểm is_staff)."""

    def has_permission(self, request, view) -> bool:
        return super().has_permission(request, view) and bool(
            request.user and request.user.is_superuser
        )


class HealthzView(APIView):
    """GET /healthz/ — health check nhẹ cho CI deploy + monitoring sau này.

    KHÔNG query DB, KHÔNG render template — chỉ confirm Django WSGI/ASGI lên,
    middleware chain pass. Verify pre-condition cho mọi endpoint khác sẵn sàng
    nhận traffic. Dùng cho `docker compose healthcheck` + workflow deploy.yml
    `curl http://127.0.0.1:8003/healthz/`.

    Public (AllowAny), không auth. Trả 200 + JSON ``{"ok": true}``.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, _request):
        return Response({"ok": True})


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


class SiteSettingsAdminView(APIView):
    """GET + PATCH `/api/admin/site-settings/` — quản lý SiteSettings singleton.

    GET: trả toàn bộ field text/number + URL ảnh (read-only).
    PATCH: partial update field trong `SITE_SETTINGS_ADMIN_EDITABLE_FIELDS`.
      - select_for_update lock row → race-safe khi 2 superuser PATCH đồng thời.
      - Ghi AuditLog với cả old + new value (NĐ 13/2023). Sensitive field (số
        TK ngân hàng) mask 4 số cuối, KHÔNG plaintext.
      - Bỏ qua key lạ (không raise) để FE gửi extra field không vỡ.
    """

    permission_classes = [IsSuperUser]

    def get(self, request):
        site = SiteSettings.get_solo()
        return Response(
            SiteSettingsAdminSerializer(site, context={"request": request}).data
        )

    def patch(self, request):
        try:
            instance, _changed = apply_audited_patch_singleton(
                model=SiteSettings,
                serializer_cls=SiteSettingsAdminSerializer,
                request=request,
                editable_fields=SITE_SETTINGS_ADMIN_EDITABLE_FIELDS,
                audit_target_model="SiteSettings",
                sensitive_masks={
                    "bank_account_number": _mask_bank_account,
                    # NĐ 13/2023: MST DN/CN là dữ liệu định danh gián tiếp (kết
                    # hợp với STK có thể cross-reference GDT) — chỉ mask 4 cuối.
                    "tax_code": _mask_bank_account,
                },
                ip_resolver=_get_client_ip,
            )
        except ValueError:
            return Response(
                {"detail": "Không có field nào hợp lệ để cập nhật."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            SiteSettingsAdminSerializer(instance, context={"request": request}).data
        )


class SiteSettingsBrandImageView(APIView):
    """POST + DELETE `/api/admin/site-settings/upload-image/`.

    POST multipart: upload 1 ảnh (logo / favicon / og_image) đè file cũ.
    DELETE JSON {"field": "logo"}: xóa ảnh hiện tại + reset field.

    Validation server-side:
    - field nằm trong enum (logo / favicon / og_image).
    - size <= spec.max_bytes (logo 2MB, favicon 512KB, og_image 5MB).
    - PIL verify true image (chống upload php/sh giả ext .png).
    - format nằm trong allowed_mime per-field.
    - dimension trong bound (logo 256-4096, favicon 16-512, og_image 600x315-4096).

    File cũ xóa SAU commit (`transaction.on_commit`) để tránh orphan khi DB
    rollback nhưng file đã delete. Tên file mới sinh UUID v4 unpredictable.

    Audit log: 1 entry UPDATE/DELETE với fields_changed + old/new là tên file
    tương đối (vd ``brand/logo_abc123.png``), không sensitive.
    """

    permission_classes = [IsSuperUser]
    # MultiPart + Form cho POST upload; JSON cho DELETE (cũng accept query param).
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        field = request.data.get("field", "")
        if field not in IMAGE_FIELD_SPECS:
            return Response(
                {
                    "detail": (
                        f"Field ảnh không hợp lệ. Chỉ chấp nhận: "
                        f"{', '.join(sorted(IMAGE_FIELD_SPECS))}."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        upload = request.FILES.get("image")
        if upload is None:
            return Response(
                {"detail": "Thiếu file ảnh trong body multipart (key 'image')."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            detected_format = validate_uploaded_image(field, upload)
        except DjangoValidationError as exc:
            return Response(
                {"detail": "; ".join(exc.messages)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        new_name = safe_image_filename(field, detected_format)

        with transaction.atomic():
            site = SiteSettings.objects.select_for_update().get_or_create(
                pk=getattr(SiteSettings, "singleton_instance_id", 1)
            )[0]
            old_file = getattr(site, field)
            old_value = to_audit_value(old_file)

            # ImageField.save() lưu file qua default_storage + set field value
            # + save model. Tên file truyền vào sẽ qua get_available_name của
            # storage (default đảm bảo unique trong directory).
            getattr(site, field).save(new_name, upload, save=True)
            new_value = to_audit_value(getattr(site, field))

            AuditLog.objects.create(
                user=request.user if request.user.is_authenticated else None,
                action=AuditLog.Action.UPDATE,
                target_model="SiteSettings",
                target_id=str(site.pk),
                changes={
                    "fields_changed": [field],
                    "old": {field: old_value},
                    "new": {field: new_value},
                },
                ip_address=_get_client_ip(request),
                user_agent=request.META.get(
                    "HTTP_USER_AGENT", ""
                )[: AuditLog._meta.get_field("user_agent").max_length],
            )

            # Xóa file cũ SAU khi commit để tránh DB rollback nhưng file đã
            # delete (orphan ngược). Storage.delete() no-op nếu file không tồn
            # tại (default_storage local + S3 đều safe).
            if old_value and old_value != new_value:
                transaction.on_commit(
                    lambda old=old_value: default_storage.delete(old)
                )

        return Response(
            SiteSettingsAdminSerializer(site, context={"request": request}).data
        )

    def delete(self, request):
        # DELETE accept body JSON `{"field": "logo"}` only (KHÔNG query param).
        # Lý do consistency với PATCH/POST + tránh field tên ảnh xuất hiện trên
        # access log/browser history/referer.
        field = request.data.get("field", "") if isinstance(request.data, dict) else ""
        if field not in IMAGE_FIELD_SPECS:
            return Response(
                {
                    "detail": (
                        f"Field ảnh không hợp lệ. Chỉ chấp nhận: "
                        f"{', '.join(sorted(IMAGE_FIELD_SPECS))}."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            site = SiteSettings.objects.select_for_update().get_or_create(
                pk=getattr(SiteSettings, "singleton_instance_id", 1)
            )[0]
            old_file = getattr(site, field)
            old_value = to_audit_value(old_file)

            if not old_value:
                # Idempotent: xóa khi đã rỗng → 200 với data hiện tại, không
                # ghi audit (không có thay đổi).
                return Response(
                    SiteSettingsAdminSerializer(
                        site, context={"request": request}
                    ).data
                )

            # ImageField.delete(save=True) xóa file qua storage + set field
            # về null + save model.
            getattr(site, field).delete(save=True)

            AuditLog.objects.create(
                user=request.user if request.user.is_authenticated else None,
                action=AuditLog.Action.DELETE,
                target_model="SiteSettings",
                target_id=str(site.pk),
                changes={
                    "fields_changed": [field],
                    "old": {field: old_value},
                    "new": {field: ""},
                },
                ip_address=_get_client_ip(request),
                user_agent=request.META.get(
                    "HTTP_USER_AGENT", ""
                )[: AuditLog._meta.get_field("user_agent").max_length],
            )

        return Response(
            SiteSettingsAdminSerializer(site, context={"request": request}).data
        )


def _mask_bank_account(number: str) -> str:
    """Mask số TK chỉ giữ 4 số cuối: `123456789` → `*****6789`."""
    if not number:
        return ""
    if len(number) <= 4:
        return "****"
    return "*" * (len(number) - 4) + number[-4:]


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
