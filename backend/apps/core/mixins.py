"""Helper tái sử dụng cho admin PATCH endpoint singleton an toàn ghi audit log.

Đóng gói 4 việc lặp lại ở mọi admin endpoint sửa Settings:

1. ``select_for_update`` trong ``transaction.atomic`` để chống last-write-wins khi
   2 superuser PATCH đồng thời (race condition).
2. Snapshot giá trị TRƯỚC khi save để diff đúng kể cả khi serializer mutate
   (DRF có thể normalize value).
3. Build ``changes`` dict gồm cả ``old`` + ``new`` (NĐ 13/2023 yêu cầu truy được
   "đổi từ X sang Y", chỉ tên field là không đủ điều tra).
4. Mask sensitive field qua callable map (vd số TK ngân hàng → ``*****1234``).

Tách helper riêng vì:

- Sprint sau sẽ có thêm admin endpoint khác (upload UI ảnh logo, email config,
  webhook outbound…) đều cần cùng pattern.
- Tránh copy-paste audit logic 3-4 chỗ → mỗi chỗ sai 1 kiểu, không nhất quán.

Chọn helper function thay vì class mixin: APIView của DRF không sẵn instance state
phù hợp; helper thuần dễ test, không buộc inheritance.
"""
from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from django.db import transaction
from django.db.models import Model
from rest_framework import serializers as drf_serializers
from rest_framework.request import Request

from .models import AuditLog


class EmptyPayloadError(Exception):
    """Raise khi payload sau filter whitelist rỗng (caller nên return 400).

    Clean exception class hơn raw ``ValueError("payload_empty")``: consumer
    Sprint 4+ có thể phân biệt với ValueError business logic khác (vd
    validation), và có thể catch riêng để log/handle khác nhau.
    """


# Mask callable: nhận giá trị raw (str/None/int) → trả str an toàn hiển thị log.
SensitiveMaskMap = dict[str, Callable[[Any], str]]

# Bound forensic SUSPICIOUS_FIELD log để chống DoS bloat AuditLog table:
# - Attacker (compromised superuser) gửi 10k key lạ → 1 row JSONB phình → PG
#   TOAST page cost + query forensic chậm. Giữ tối đa 20 key đầu (sorted) +
#   marker __truncated__ + count thật. Volume admin endpoint cực thấp nên 20
#   key đủ truy vết pattern attack.
# - Single key tên 50k char → JSONB > 2KB → đẩy ra TOAST. Truncate 64 đủ phân
#   biệt field name hợp lệ (max field name VN hiện ~ 30 char `working_hours_text`).
MAX_REJECTED_FIELDS_LOGGED = 20
MAX_REJECTED_KEY_LENGTH = 64


def apply_audited_patch_singleton(
    *,
    model: type[Model],
    serializer_cls: type[drf_serializers.ModelSerializer],
    request: Request,
    editable_fields: Iterable[str],
    audit_target_model: str,
    sensitive_masks: SensitiveMaskMap | None = None,
    extra_serializer_context: dict[str, Any] | None = None,
    audit_action: str = AuditLog.Action.UPDATE,
    ip_resolver: Callable[[Request], str | None] | None = None,
) -> tuple[Model, list[str]]:
    """Thực thi PATCH singleton kèm audit log.

    Args:
        model: Class SingletonModel (django-solo) — sẽ gọi ``get_solo()`` rồi
            ``select_for_update`` để lock row trong transaction.
        serializer_cls: ModelSerializer dùng để validate + save.
        request: DRF Request đang xử lý PATCH.
        editable_fields: Whitelist field cho phép PATCH. Body lạ bị filter trước
            khi vào serializer (defense-in-depth chống mass assignment).
        audit_target_model: Tên model ghi vào AuditLog.target_model (vd
            ``"SiteSettings"``).
        sensitive_masks: Map ``{field_name: mask_callable}``. Field có trong map
            khi audit sẽ chỉ lưu giá trị đã mask (NĐ 13/2023). Field KHÔNG có
            trong map → lưu raw value.
        extra_serializer_context: Thêm key vào serializer context (vd ``{"request":
            request}`` để absolute URL hoạt động).
        audit_action: AuditLog.Action enum, default UPDATE.
        ip_resolver: Callable lấy IP client từ request. Nếu None → đọc từ
            ``REMOTE_ADDR`` (KHÔNG tin X-Forwarded-For).

    Returns:
        Tuple (updated instance, list field tên đã đổi). Empty list = không đổi
        gì → caller có thể skip audit hoặc return 304 tuỳ ngữ cảnh.

    Raises:
        rest_framework.exceptions.ValidationError: Serializer invalid.
        EmptyPayloadError: Payload sau khi filter rỗng (caller nên return 400).

    Behavior:
        - Mở 1 ``transaction.atomic`` block bao trọn fetch → validate → save → audit.
        - select_for_update lock row tới hết transaction → PATCH đồng thời sẽ
          serialize (PostgreSQL row-level lock).
        - Filter raw body theo whitelist TRƯỚC khi truyền serializer (nếu sau này
          thêm field nhạy cảm ``is_superuser`` vào model, mass assignment vẫn an toàn).
        - Key client gửi NHƯNG nằm ngoài whitelist (vd ``is_superuser``,
          ``created_at``) sẽ emit AuditLog ``SUSPICIOUS_FIELD`` riêng (NGOÀI
          atomic block) — luôn ghi kể cả khi payload sau filter rỗng → raise
          ValueError. Forensic: chỉ log tên key, KHÔNG log value tránh leak
          attack vector.
        - Audit UPDATE chỉ ghi khi có field thực sự đổi (so sánh old != new
          bằng ``!=`` để bắt cả case serializer normalize giá trị
          ``"  x  "`` → ``"x"``).
        - Sensitive field: cả old + new đều mask trước khi đưa vào ``changes``.
    """
    sensitive_masks = sensitive_masks or {}
    editable_set = set(editable_fields)

    raw = request.data if isinstance(request.data, dict) else {}
    payload = {k: v for k, v in raw.items() if k in editable_set}
    # Forensic: capture key client gửi nhưng KHÔNG nằm trong whitelist (vd
    # is_superuser, id, created_at). Chỉ log tên key, KHÔNG log value — tránh
    # leak attack vector ngược lại vào DB. AuditLog này LUÔN ghi kể cả khi
    # payload còn lại empty + raise ValueError sau đó, để forensic value cao
    # nhất (attacker thử endpoint).
    rejected_set = set(raw.keys()) - editable_set
    rejected_count = len(rejected_set)

    actor = request.user if request.user.is_authenticated else None
    client_ip = _resolve_ip(request, ip_resolver)
    ua_max_length = AuditLog._meta.get_field("user_agent").max_length
    user_agent = request.META.get("HTTP_USER_AGENT", "")[:ua_max_length]

    if rejected_count > 0:
        # Truncate key dài (chống TOAST bloat) + cap số key log (chống DoS storm).
        # Dedup sau truncate (set comprehension) tránh redundancy khi 2 key khác
        # nhau collapse cùng prefix 64 char. Sort để output deterministic, tránh
        # test flaky theo set iteration order. rejected_count vẫn đếm SET GỐC
        # trước truncate → forensic source-of-truth không bị lệch.
        truncated_keys = sorted({k[:MAX_REJECTED_KEY_LENGTH] for k in rejected_set})
        if len(truncated_keys) > MAX_REJECTED_FIELDS_LOGGED:
            logged_keys = (
                truncated_keys[:MAX_REJECTED_FIELDS_LOGGED] + ["__truncated__"]
            )
        else:
            logged_keys = truncated_keys
        AuditLog.objects.create(
            user=actor,
            action=AuditLog.Action.SUSPICIOUS_FIELD,
            target_model=audit_target_model,
            # target_id rỗng: SUSPICIOUS log forensic event của attempt, KHÔNG
            # gắn instance cụ thể vì attacker chưa chạm row. Tránh mismatch với
            # UPDATE log target_id=instance.pk thật (django-solo custom pk).
            target_id="",
            changes={
                "rejected_fields": logged_keys,
                "rejected_count": rejected_count,
            },
            ip_address=client_ip,
            user_agent=user_agent,
        )

    if not payload:
        raise EmptyPayloadError("payload_empty")

    context = {"request": request}
    if extra_serializer_context:
        context.update(extra_serializer_context)

    solo_pk = getattr(model, "singleton_instance_id", 1)

    with transaction.atomic():
        # Lock row tới hết transaction. SingletonModel: id luôn = singleton_instance_id
        # (mặc định 1) do django-solo enforce. ``select_for_update().get_or_create``
        # NẰM TRONG transaction.atomic đóng race window: khi DB rỗng + 2 superuser
        # PATCH đồng thời, PG cấp row-level lock (hoặc IntegrityError pk=1 cho
        # loser → retry). Tránh được tình huống get_solo() ngoài atomic chạy
        # trước rồi luồng khác đọc trước commit.
        instance, _created = model.objects.select_for_update().get_or_create(
            pk=solo_pk
        )

        # Snapshot old values TRƯỚC khi serializer mutate instance.
        old_values: dict[str, Any] = {f: getattr(instance, f) for f in payload}

        serializer = serializer_cls(
            instance, data=payload, partial=True, context=context
        )
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        fields_changed: list[str] = []
        new_values: dict[str, Any] = {}
        for field in payload:
            new_val = getattr(instance, field)
            if new_val != old_values[field]:
                fields_changed.append(field)
                new_values[field] = new_val

        if fields_changed:
            changes = _build_audit_changes(
                fields_changed=fields_changed,
                old_values=old_values,
                new_values=new_values,
                sensitive_masks=sensitive_masks,
            )
            AuditLog.objects.create(
                user=actor,
                action=audit_action,
                target_model=audit_target_model,
                target_id=str(instance.pk),
                changes=changes,
                ip_address=client_ip,
                user_agent=user_agent,
            )

    return instance, fields_changed


def _build_audit_changes(
    *,
    fields_changed: list[str],
    old_values: dict[str, Any],
    new_values: dict[str, Any],
    sensitive_masks: SensitiveMaskMap,
) -> dict[str, Any]:
    """Tổ hợp ``changes`` dict với old+new đầy đủ + mask sensitive.

    Schema output (NĐ 13/2023):

    ::

        {
            "fields_changed": ["brand_name", "bank_account_number"],
            "old": {
                "brand_name": "Trung tâm cũ",
                "bank_account_number": "*****3344"   # masked
            },
            "new": {
                "brand_name": "Trung tâm mới",
                "bank_account_number": "*****7766"   # masked
            },
            # Legacy keys giữ back-compat audit query cũ (bank_account_number_*).
            "bank_account_number_old_masked": "*****3344",
            "bank_account_number_new_masked": "*****7766"
        }

    Field non-sensitive lưu raw value vào ``old``/``new`` để truy vết đầy đủ.
    Field sensitive lưu giá trị đã mask (callable trong ``sensitive_masks``).
    """
    old_dump: dict[str, Any] = {}
    new_dump: dict[str, Any] = {}

    for field in fields_changed:
        if field in sensitive_masks:
            mask = sensitive_masks[field]
            old_dump[field] = mask(old_values[field])
            new_dump[field] = mask(new_values[field])
        else:
            old_dump[field] = _json_safe(old_values[field])
            new_dump[field] = _json_safe(new_values[field])

    changes: dict[str, Any] = {
        "fields_changed": fields_changed,
        "old": old_dump,
        "new": new_dump,
    }

    # Legacy back-compat: query cũ dò bank_account_number_old_masked / _new_masked.
    if "bank_account_number" in sensitive_masks and "bank_account_number" in fields_changed:
        changes["bank_account_number_old_masked"] = old_dump["bank_account_number"]
        changes["bank_account_number_new_masked"] = new_dump["bank_account_number"]

    return changes


def _json_safe(value: Any) -> Any:
    """Convert giá trị model → kiểu JSON-serializable cho ``JSONField``.

    Chủ yếu cho Decimal/Date/Datetime — model field DecimalField (map_lat/lng)
    không stringify mặc định trong json.dumps. Bool/int/float/str/None giữ nguyên.
    """
    from datetime import date, datetime
    from decimal import Decimal

    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value)


def _resolve_ip(
    request: Request, resolver: Callable[[Request], str | None] | None
) -> str | None:
    if resolver is not None:
        return resolver(request)
    return request.META.get("REMOTE_ADDR") or None
