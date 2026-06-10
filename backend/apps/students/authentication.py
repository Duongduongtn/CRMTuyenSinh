"""DRF authentication class cho học viên — JWT access token.

Khác với SessionAuthentication (admin CRM), HV dùng Authorization: Bearer <jwt>.
Sau khi xác thực, ``request.user`` là một wrapper ``StudentUser`` không phải Django
User — vì học viên ở model ``StudentAccount`` riêng.
"""
from __future__ import annotations

from rest_framework import authentication, exceptions

from .auth import TokenError, decode_token
from .models import StudentAccount


class StudentUser:
    """Wrapper request.user cho HV.

    Có ``is_authenticated = True``, ``account_id``, ``phone``, ``token_type``.
    KHÔNG có ``is_staff`` / ``is_superuser`` — đảm bảo HV không lọt vào admin.
    """

    is_authenticated = True
    is_anonymous = False
    is_staff = False
    is_superuser = False

    def __init__(self, account: StudentAccount, token_payload: dict):
        self.account = account
        self.pk = account.pk
        self.id = account.pk
        self.account_id = account.pk
        self.phone = account.phone
        self.display_name = account.display_name
        self.token_type = token_payload.get("type", "access")
        self.enrollment_id = token_payload.get("enrollment")
        self.token_payload = token_payload

    def __str__(self) -> str:
        return f"Student({self.phone})"


class StudentJWTAuthentication(authentication.BaseAuthentication):
    """``Authorization: Bearer <jwt>`` cho FE student."""

    keyword = "Bearer"

    def authenticate(self, request):
        auth_header = authentication.get_authorization_header(request).decode("utf-8", "ignore")
        if not auth_header or not auth_header.startswith(self.keyword + " "):
            return None
        token = auth_header[len(self.keyword) + 1:].strip()
        if not token:
            return None
        try:
            payload = decode_token(token, expected_type="access")
        except TokenError as exc:
            raise exceptions.AuthenticationFailed(str(exc))
        try:
            account = StudentAccount.objects.get(pk=payload["sub"], is_active=True)
        except StudentAccount.DoesNotExist as exc:
            raise exceptions.AuthenticationFailed("Tài khoản không tồn tại hoặc đã bị khóa.") from exc
        return (StudentUser(account, payload), token)

    def authenticate_header(self, request):
        return self.keyword
