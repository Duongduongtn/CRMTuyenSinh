"""Signal receivers ghi `core.AuditLog` cho action nhạy cảm.

Cover:
- post_save / post_delete cho Payment, Enrollment, PersonDocument, EnrollmentDocument.
- user_logged_in / user_logged_out (Django auth signal).
- Helper `log_audit()` cho view code log VIEW_SENSITIVE (file CCCD, list payment).

Tránh duplicate log: Enrollment.recompute_status_from_paid() được gọi từ Payment
confirm path bằng `enrollment.save(update_fields=[...])`. Đó là internal cascade
KHÔNG phải staff edit → skip để không spam audit log.
"""
from django.conf import settings
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .middleware import get_current_request
from .models import AuditLog


# Whitelist update_fields của internal recompute (Enrollment.recompute_status_from_paid).
# Save với CHỈ các field này sẽ KHÔNG sinh AuditLog.UPDATE (vì không phải staff edit).
INTERNAL_RECOMPUTE_FIELDS = {
    "status",
    "paid_amount",
    "deposit_paid_at",
    "completed_at",
    "updated_at",
}


def _client_meta(request):
    """Lấy IP + User-Agent từ request.

    `TRUST_X_FORWARDED_FOR=True` mới đọc header forwarded — khi đứng sau proxy
    đáng tin (nginx). Mặc định False để client KHÔNG forge được IP audit.
    """
    if request is None:
        return None, ""
    trust_xff = getattr(settings, "TRUST_X_FORWARDED_FOR", False)
    if trust_xff:
        ip = (
            request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
            or request.META.get("REMOTE_ADDR")
        )
    else:
        ip = request.META.get("REMOTE_ADDR")
    ua = request.META.get("HTTP_USER_AGENT", "")[:255]
    return ip, ua


def _is_crm_user(user) -> bool:
    """AuditLog.user là FK đến AUTH_USER_MODEL. StudentUser (PWA) không khớp.

    Cẩn thận: assign sai sẽ raise ValueError: must be a "User" instance.
    """
    if user is None:
        return False
    meta = getattr(user, "_meta", None)
    if meta is None:
        return False
    return meta.label_lower == settings.AUTH_USER_MODEL.lower()


def _actor_from_request(request):
    if request is None:
        return None
    user = getattr(request, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        return None
    if not _is_crm_user(user):
        return None
    return user


def log_audit(actor, action, instance, changes=None, request=None):
    """Helper public cho view code log action không capture được qua signals.

    Ví dụ: serve file CCCD, list payment, đổi quyền group. `request` được suy
    ra từ thread-local nếu không truyền.
    """
    req = request if request is not None else get_current_request()
    ip, ua = _client_meta(req)
    return AuditLog.objects.create(
        user=actor,
        action=action,
        target_model=f"{instance._meta.app_label}.{instance._meta.model_name}",
        target_id=str(instance.pk) if instance.pk is not None else "",
        changes=changes,
        ip_address=ip,
        user_agent=ua,
    )


def _is_internal_recompute(update_fields) -> bool:
    """save(update_fields=[...]) với toàn field thuộc whitelist recompute → skip."""
    if not update_fields:
        return False
    return set(update_fields).issubset(INTERNAL_RECOMPUTE_FIELDS)


def _on_post_save(sender, instance, created, **kwargs):
    if not created and _is_internal_recompute(kwargs.get("update_fields")):
        return
    req = get_current_request()
    actor = _actor_from_request(req)
    log_audit(
        actor,
        AuditLog.Action.CREATE if created else AuditLog.Action.UPDATE,
        instance,
        request=req,
    )


def _on_post_delete(sender, instance, **kwargs):
    req = get_current_request()
    actor = _actor_from_request(req)
    log_audit(actor, AuditLog.Action.DELETE, instance, request=req)


def _connect_model_signals():
    """Kết nối signal cho các model nhạy cảm. Bằng dispatch_uid để idempotent."""
    from django.apps import apps as django_apps

    targets = [
        ("payments.Payment", True),
        ("orders.Enrollment", True),
        ("documents.PersonDocument", True),
        ("documents.EnrollmentDocument", True),
    ]
    for dotted, track_delete in targets:
        try:
            Model = django_apps.get_model(dotted)
        except LookupError:
            continue
        post_save.connect(
            _on_post_save,
            sender=Model,
            dispatch_uid=f"audit_post_save_{dotted}",
            weak=False,
        )
        if track_delete:
            post_delete.connect(
                _on_post_delete,
                sender=Model,
                dispatch_uid=f"audit_post_delete_{dotted}",
                weak=False,
            )


@receiver(user_logged_in, dispatch_uid="audit_user_logged_in")
def _logged_in(sender, request, user, **kwargs):
    # AuditLog chỉ track CRM staff. StudentUser dùng JWT riêng, không qua signal này.
    if not _is_crm_user(user):
        return
    ip, ua = _client_meta(request)
    AuditLog.objects.create(
        user=user,
        action=AuditLog.Action.LOGIN,
        target_model="users.user",
        target_id=str(user.pk),
        ip_address=ip,
        user_agent=ua,
    )


@receiver(user_logged_out, dispatch_uid="audit_user_logged_out")
def _logged_out(sender, request, user, **kwargs):
    if not _is_crm_user(user):
        return
    ip, ua = _client_meta(request)
    AuditLog.objects.create(
        user=user,
        action=AuditLog.Action.LOGOUT,
        target_model="users.user",
        target_id=str(user.pk),
        ip_address=ip,
        user_agent=ua,
    )


# Kết nối khi module được load qua CoreConfig.ready().
_connect_model_signals()
