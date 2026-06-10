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

from apps.core.models import AuditLog
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
    StudentDeleteRequest,
)
from .serializers import (
    DeleteRequestSerializer,
    EnrollmentDashboardSerializer,
    OTPRequestSerializer,
    OTPVerifySerializer,
    PersonUpdateSerializer,
    QuickEnrollmentSerializer,
    RefreshSerializer,
    StudentMeSerializer,
)
from .tasks import send_delete_request_telegram
from .throttles import (
    DeleteRequestThrottle,
    OTPRequestThrottle,
    OTPVerifyPhoneThrottle,
    OTPVerifyThrottle,
)
from .zns_adapter import ZNSError, send_otp


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

    Invalidate mọi OTP ``pending`` cũ cho cùng SĐT trước khi tạo OTP mới —
    chống abuse "tạo nhiều OTP song song để tăng cơ hội brute-force".
    """
    ser = OTPRequestSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    phone = ser.validated_data["phone"]

    # Invalidate OTP cũ pending cho cùng SĐT
    OTPRequest.objects.filter(
        phone=phone, status=OTPRequest.Status.PENDING
    ).update(status=OTPRequest.Status.EXPIRED)

    otp, plain_code = OTPRequest.create_for_phone(
        phone,
        ip_address=_client_ip(request),
        user_agent=request.META.get("HTTP_USER_AGENT", ""),
    )
    try:
        result = send_otp(phone, plain_code)
    except ZNSError as exc:
        # Mark OTP đã tạo là expired vì gửi thất bại
        otp.status = OTPRequest.Status.EXPIRED
        otp.sent_via = "zns_unconfigured"
        otp.sent_meta = {"error": str(exc)}
        otp.save(update_fields=["status", "sent_via", "sent_meta"])
        return Response(
            {"detail": str(exc)},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
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
@throttle_classes([OTPVerifyThrottle, OTPVerifyPhoneThrottle])
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


class QuickEnrollmentView(APIView):
    """GET /api/student/quick/<token> — quick view 24h từ link Zalo ZNS.

    Theo memory [[student-auth-flow]]:
    - Token type = ``quick``, TTL 24h, scope cứng ``enrollment`` ID.
    - Trả chi tiết đúng enrollment trong scope. KHÔNG list, KHÔNG /me, KHÔNG
      /persons.
    - Read-only — không có PATCH/POST kể cả khi có token hợp lệ.
    - KHÔNG cần Authorization header — token đã ở URL.

    IDOR check: account.phone trong token PHẢI khớp enrollment.student_phone.
    Token hợp lệ nhưng enrollment đã đổi SĐT (văn thư thao tác) → 410 Gone.
    """

    authentication_classes: list = []
    permission_classes = [permissions.AllowAny]

    def get(self, request, token: str):
        try:
            payload = decode_token(token, expected_type="quick")
        except TokenError as exc:
            return Response(
                {"detail": str(exc), "code": "invalid_token"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        enrollment_id = payload.get("enrollment")
        if not enrollment_id:
            return Response(
                {"detail": "Token thiếu scope đơn.", "code": "missing_scope"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            account = StudentAccount.objects.get(pk=payload["sub"], is_active=True)
        except StudentAccount.DoesNotExist:
            return Response(
                {"detail": "Tài khoản đã bị khóa.", "code": "account_disabled"},
                status=status.HTTP_410_GONE,
            )

        enrollment = (
            Enrollment.objects
            .filter(pk=enrollment_id, student_phone=account.phone)
            .select_related("course")
            .first()
        )
        if not enrollment:
            # Token hợp lệ nhưng đơn không còn match → IDOR-safe trả 410.
            return Response(
                {
                    "detail": "Liên kết không còn dùng được. Vui lòng đăng nhập lại bằng SĐT.",
                    "code": "enrollment_unavailable",
                },
                status=status.HTTP_410_GONE,
            )
        # Đơn đã hủy/hoàn → không serve qua quick link nữa.
        from apps.orders.models import EnrollmentStatus

        if enrollment.status in (EnrollmentStatus.CANCELLED, EnrollmentStatus.REFUNDED):
            return Response(
                {
                    "detail": "Đơn này đã hủy. Vui lòng liên hệ trung tâm.",
                    "code": "enrollment_inactive",
                },
                status=status.HTTP_410_GONE,
            )

        # Audit log xem dữ liệu nhạy cảm (quick token có thể forward).
        masked_phone = (
            account.phone[:3] + "****" + account.phone[-3:]
            if len(account.phone) >= 7
            else "***"
        )
        AuditLog.objects.create(
            user=None,
            action=AuditLog.Action.VIEW_SENSITIVE,
            target_model="orders.Enrollment",
            target_id=str(enrollment.pk),
            changes={
                "via": "quick_token",
                "phone_masked": masked_phone,
                "jti": payload.get("jti", ""),
            },
            ip_address=_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:255],
        )

        return Response({
            "scope": "quick_view_read_only",
            "expires_at": payload.get("exp"),
            "enrollment": QuickEnrollmentSerializer(enrollment).data,
        })


class DeleteRequestView(StudentAuthMixin, APIView):
    """POST /api/student/me/delete-request — HV yêu cầu xóa dữ liệu (NĐ 13/2023).

    KHÔNG xóa dữ liệu ngay. Tạo record ``StudentDeleteRequest`` (status=received)
    và bắn Telegram cho admin xử lý thủ công vì phải đối soát công nợ + hồ sơ
    đã nộp Sở GTVT. Theo điều 9 NĐ 13/2023, đơn vị có 72 giờ để phản hồi.

    Anti-spam: 1 account chỉ được tạo 1 yêu cầu ``received``/``in_review`` đang
    chờ tại 1 thời điểm. Gọi lại trả về record cũ (idempotent từ góc HV).
    Throttle 5 lần/giờ/account để chặn audit log spam có chủ ý.
    """

    throttle_classes = [DeleteRequestThrottle]

    def post(self, request):
        ser = DeleteRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        reason = ser.validated_data.get("reason", "")

        account = request.user.account
        existing = StudentDeleteRequest.objects.filter(
            account=account,
            status__in=[
                StudentDeleteRequest.Status.RECEIVED,
                StudentDeleteRequest.Status.IN_REVIEW,
            ],
        ).order_by("-created_at").first()
        if existing:
            return Response(
                {
                    "detail": (
                        "Yêu cầu xóa dữ liệu đã được tiếp nhận. Trung tâm sẽ "
                        "phản hồi qua Zalo trong vòng 72 giờ."
                    ),
                    "request_id": existing.id,
                    "status": existing.status,
                    "created_at": existing.created_at,
                    "code": "already_received",
                },
                status=status.HTTP_200_OK,
            )

        req = StudentDeleteRequest.objects.create(
            account=account,
            reason=reason,
            ip_address=_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:255],
        )
        AuditLog.objects.create(
            user=None,
            action=AuditLog.Action.CREATE,
            target_model="students.StudentDeleteRequest",
            target_id=str(req.pk),
            changes={"phone": account.phone, "via": "pwa"},
            ip_address=_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:255],
        )

        try:
            send_delete_request_telegram.delay(req.id)
        except Exception:  # noqa: BLE001 — broker chưa sẵn ở dev không được làm vỡ flow
            import logging

            logging.getLogger("apps.students").exception(
                "Không enqueue được Telegram task — đã tạo request %s", req.id
            )

        return Response(
            {
                "detail": (
                    "Đã tiếp nhận yêu cầu xóa dữ liệu. Trung tâm sẽ phản hồi "
                    "trong vòng 72 giờ theo Nghị định 13/2023/NĐ-CP."
                ),
                "request_id": req.id,
                "status": req.status,
                "created_at": req.created_at,
            },
            status=status.HTTP_201_CREATED,
        )


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
