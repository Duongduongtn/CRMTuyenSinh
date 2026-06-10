"""API học viên PWA.

Endpoints (prefix `/api/student/`):

- ``POST /auth/request-otp``  — body ``{phone}`` → tạo OTP, gửi qua ZNS/mock.
- ``POST /auth/verify-otp``   — body ``{phone, code}`` → trả ``access`` + ``refresh``.
- ``POST /auth/refresh``      — body ``{refresh}`` → trả access mới.
- ``GET  /me``                — thông tin tài khoản + persons link.
- ``GET  /enrollments``       — list Enrollment của HV (theo phone match).
- ``GET  /enrollments/<id>``  — chi tiết 1 enrollment (IDOR-safe).
- ``PATCH /persons/<id>``     — cập nhật thông tin cá nhân person mà HV đã link.
"""
from __future__ import annotations

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.orders.models import Enrollment
from .auth import (
    TokenError,
    decode_token,
    issue_access_token,
    issue_refresh_token,
)
from .authentication import StudentJWTAuthentication
from .models import (
    AccountPersonLink,
    OTPRequest,
    Person,
    StudentAccount,
    normalize_phone,
)
from .serializers import (
    EnrollmentDashboardSerializer,
    OTPRequestSerializer,
    OTPVerifySerializer,
    PersonUpdateSerializer,
    RefreshSerializer,
    StudentMeSerializer,
)
from .throttles import OTPRequestThrottle, OTPVerifyThrottle
from .zns_adapter import send_otp


def _client_ip(request) -> str | None:
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
@throttle_classes([OTPRequestThrottle])
def request_otp(request):
    """Tạo OTP và gửi qua ZNS (hoặc mock dev).

    Response luôn 200 thành công, không leak thông tin "SĐT này có tồn tại trong
    hệ thống không" để chống user enumeration. Tạo mới account nếu chưa có —
    cũng giúp HV tự đăng ký lần đầu nếu sale chưa nhập kịp (mặc dù flow chính
    là sale chốt đơn trước, HV login sau).
    """
    ser = OTPRequestSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    phone = ser.validated_data["phone"]

    otp, plain_code = OTPRequest.create_for_phone(
        phone,
        ip_address=_client_ip(request),
        user_agent=request.META.get("HTTP_USER_AGENT", ""),
    )
    result = send_otp(phone, plain_code)
    otp.sent_via = result["sent_via"]
    otp.sent_meta = result["meta"]
    otp.save(update_fields=["sent_via", "sent_meta"])

    return Response(
        {
            "detail": "Đã gửi OTP. Vui lòng kiểm tra Zalo trong vòng 5 phút.",
            "expires_in_seconds": 300,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
@throttle_classes([OTPVerifyThrottle])
def verify_otp(request):
    """Xác thực OTP → cấp access + refresh JWT.

    Nếu SĐT chưa có account → auto-provision (theo memory [[student-auth-flow]]).
    """
    ser = OTPVerifySerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    phone = ser.validated_data["phone"]
    code = ser.validated_data["code"]

    otp = (
        OTPRequest.objects
        .filter(phone=phone, status=OTPRequest.Status.PENDING)
        .order_by("-created_at")
        .first()
    )
    if not otp:
        return Response(
            {"detail": "Không tìm thấy mã OTP còn hiệu lực. Gửi lại mã mới."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    ok = otp.verify(code)
    otp.save(update_fields=["status", "attempts", "consumed_at"])
    if not ok:
        return Response(
            {"detail": "Mã OTP không đúng hoặc đã hết hạn."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    account, created = StudentAccount.objects.get_or_create(phone=phone)
    account.last_login_at = timezone.now()
    if created and not account.display_name:
        # Nếu có Enrollment với SĐT này, lấy student_name làm display
        enr = Enrollment.objects.filter(student_phone=phone).order_by("-created_at").first()
        if enr:
            account.display_name = enr.student_name
    account.save(update_fields=["last_login_at", "display_name"])

    return Response({
        "access": issue_access_token(account.pk, account.phone),
        "refresh": issue_refresh_token(account.pk, account.phone),
        "account": {
            "id": account.pk,
            "phone": account.phone,
            "display_name": account.display_name,
            "is_new": created,
        },
    })


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def refresh_token(request):
    ser = RefreshSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    try:
        payload = decode_token(ser.validated_data["refresh"], expected_type="refresh")
    except TokenError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_401_UNAUTHORIZED)

    account = get_object_or_404(StudentAccount, pk=payload["sub"], is_active=True)
    return Response({
        "access": issue_access_token(account.pk, account.phone),
    })


# ---- Authenticated endpoints ----


class StudentAuthMixin:
    authentication_classes = [StudentJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]


class MeView(StudentAuthMixin, APIView):
    def get(self, request):
        return Response(StudentMeSerializer(request.user.account).data)


class EnrollmentListView(StudentAuthMixin, generics.ListAPIView):
    """List Enrollment của HV theo SĐT.

    Lấy bằng cách match ``student_phone == account.phone`` (đảm bảo HV chỉ thấy
    đơn của chính mình). Khi Sprint 3 hoàn thiện Person link sẽ đổi sang join
    qua ``AccountPersonLink`` để mẹ thấy đơn của con.
    """

    serializer_class = EnrollmentDashboardSerializer

    def get_queryset(self):
        phone = self.request.user.phone
        return (
            Enrollment.objects
            .filter(student_phone=phone)
            .select_related("course")
            .order_by("-created_at")
        )


class EnrollmentDetailView(StudentAuthMixin, generics.RetrieveAPIView):
    """Chi tiết 1 enrollment — IDOR check bằng filter trên phone."""

    serializer_class = EnrollmentDashboardSerializer
    lookup_field = "pk"

    def get_queryset(self):
        phone = self.request.user.phone
        return Enrollment.objects.filter(student_phone=phone).select_related("course")


class PersonUpdateView(StudentAuthMixin, generics.UpdateAPIView):
    """HV cập nhật thông tin Person mà tài khoản này đã link.

    IDOR-safe: filter qua ``AccountPersonLink`` của account hiện tại.
    """

    serializer_class = PersonUpdateSerializer
    lookup_field = "pk"
    http_method_names = ["patch"]

    def get_queryset(self):
        account = self.request.user.account
        person_ids = AccountPersonLink.objects.filter(account=account).values_list(
            "person_id", flat=True
        )
        return Person.objects.filter(pk__in=person_ids)
