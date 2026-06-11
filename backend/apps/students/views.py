"""API học viên PWA.

Auth chốt 2026-06-11 (xem [[student-auth-flow]]):
- HV đăng nhập bằng SĐT + 6 số cuối CCCD/CMND đã được văn thư nhập vào ``Person``.
- Văn thư CRM staff bấm "Tạo link xem nhanh" → BE gen JWT 24h → văn thư copy
  link, gửi tay cho HV qua Zalo/SMS/gọi điện.

Endpoints (prefix `/api/student/`):

- ``POST /auth/login``           — body ``{phone, last6_cccd}`` → ``access`` + ``refresh``.
- ``POST /auth/refresh``         — body ``{refresh}`` → trả access mới.
- ``GET  /me``                   — thông tin tài khoản + persons link.
- ``GET  /enrollments``          — list Enrollment của HV (theo phone match).
- ``GET  /enrollments/<id>``     — chi tiết 1 enrollment (IDOR-safe).
- ``PATCH /persons/<id>``        — cập nhật thông tin cá nhân person mà HV đã link.
- ``POST /me/delete-request``    — HV yêu cầu xóa dữ liệu (NĐ 13/2023).
- ``GET  /quick/<token>``        — quick view 24h (token gen bởi staff).
- ``POST /staff/quick-token``    — văn thư CRM (staff session) gen link quick view.
"""
from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.models import AuditLog
from apps.orders.models import Enrollment
from .auth import (
    QUICK_TTL_SECONDS,
    TokenError,
    decode_token,
    issue_access_token,
    issue_quick_token,
    issue_refresh_token,
)
from .authentication import StudentJWTAuthentication
from .models import (
    AccountPersonLink,
    Person,
    StudentAccount,
    StudentDeleteRequest,
)
from .serializers import (
    DeleteRequestSerializer,
    EnrollmentDashboardSerializer,
    PersonUpdateSerializer,
    QuickEnrollmentSerializer,
    RefreshSerializer,
    StaffQuickTokenSerializer,
    StudentLoginSerializer,
    StudentMeSerializer,
)
from .tasks import send_delete_request_telegram
from .throttles import (
    DeleteRequestThrottle,
    StudentLoginIPThrottle,
    StudentLoginPhoneDayThrottle,
    StudentLoginPhoneHourThrottle,
)


def _client_ip(request) -> str | None:
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _audit_login(*, action: str, phone: str, ip: str | None, ua: str, reason: str = "") -> None:
    """Ghi audit log login/login_failed.

    KHÔNG log 6 số cuối CCCD — tránh dump DB hoặc backup audit log để brute force
    ngược. Chỉ ghi SĐT (mask 4 số giữa) + lý do generic.
    """
    masked = phone[:3] + "****" + phone[-3:] if len(phone) >= 7 else "***"
    AuditLog.objects.create(
        user=None,
        action=action,
        target_model="students.StudentAccount",
        target_id="",
        changes={"phone_masked": masked, "reason": reason} if reason else {"phone_masked": masked},
        ip_address=ip,
        user_agent=ua[:255] if ua else "",
    )


_DUMMY_LAST6 = "X" * 6
_TIMING_PAD_SLOTS = 5  # số Person tối đa trung bình để pad loop, chống timing leak.


def _verify_last6_cccd(account: StudentAccount | None, last6: str) -> bool:
    """True nếu CCCD/CMND của Person nào đó link với account có 6 số cuối khớp.

    Constant-time so sánh để chống timing attack giữa các Person.

    Pad vòng lặp tới ``_TIMING_PAD_SLOTS`` (5) lần so sánh dummy để wall-time
    không leak (a) số Person link với account, (b) tài khoản tồn tại hay không
    (account=None vẫn chạy đủ 5 dummy compare).
    """
    import hmac

    id_numbers: list[str] = []
    if account is not None:
        # 1 query gộp: lấy Person id_number qua reverse relation.
        id_numbers = list(
            Person.objects
            .filter(account_links__account=account)
            .values_list("id_number", flat=True)
        )

    matched = False
    for slot in range(_TIMING_PAD_SLOTS):
        if slot < len(id_numbers):
            raw = (id_numbers[slot] or "").strip()
            # rjust pad để mọi nhánh đều có 6 ký tự — KHÔNG dùng ``continue``.
            candidate = raw[-6:] if len(raw) >= 6 else raw.rjust(6, "X")
        else:
            candidate = _DUMMY_LAST6
        if hmac.compare_digest(candidate, last6):
            matched = True
    return matched


# ---- Auth endpoints ----


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
@throttle_classes([
    StudentLoginPhoneHourThrottle,
    StudentLoginPhoneDayThrottle,
    StudentLoginIPThrottle,
])
def login(request):
    """Đăng nhập học viên — SĐT + 6 số cuối CCCD (chốt 2026-06-11).

    Generic 401 "Sai SĐT hoặc CCCD" cho mọi trường hợp fail để chống enumeration
    (account không tồn tại, account inactive, không có Person link, CCCD sai).

    Pass điều kiện:
    1. Tài khoản tồn tại + ``is_active=True``.
    2. ``StudentAccount`` không trong lock (locked_until <= now).
    3. Có ít nhất 1 ``Person`` link với account có ``id_number[-6:]`` khớp.

    Lock state (handled trong ``register_login_failure`` ở model):
    - 5 fail liên tiếp → khóa 15 phút.
    - 10+ fail tổng → khóa 24 giờ (văn thư tự mở khi HV gọi điện chứng minh).
    """
    ser = StudentLoginSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    phone = ser.validated_data["phone"]
    last6 = ser.validated_data["last6_cccd"]
    ip = _client_ip(request)
    ua = request.META.get("HTTP_USER_AGENT", "")

    account = StudentAccount.objects.filter(phone=phone).first()

    # Locked → 423 + thông báo thời gian còn lại.
    if account and account.is_locked():
        _audit_login(action=AuditLog.Action.LOGIN_FAILED, phone=phone, ip=ip, ua=ua, reason="locked")
        return Response(
            {
                "detail": (
                    "Tài khoản đang tạm khóa do nhập sai quá nhiều lần. "
                    "Vui lòng thử lại sau."
                ),
                "code": "account_locked",
                "remaining_seconds": account.lock_remaining_seconds(),
            },
            status=status.HTTP_423_LOCKED,
        )

    # Verify CCCD CHẠY KỂ CẢ KHI account is None — chống timing enumeration
    # (path "không tồn tại" và "tồn tại + sai CCCD" tốn thời gian xấp xỉ nhau).
    cccd_ok = _verify_last6_cccd(account, last6)
    success = (
        account is not None
        and account.is_active
        and cccd_ok
    )

    if not success:
        # KHÔNG leak lý do cụ thể. Nếu có account → tăng counter atomic + có thể khóa.
        if account is not None:
            account.register_login_failure(ip=ip)
        _audit_login(action=AuditLog.Action.LOGIN_FAILED, phone=phone, ip=ip, ua=ua)
        return Response(
            {
                "detail": (
                    "Sai số điện thoại hoặc 6 số cuối CCCD. Vui lòng kiểm tra "
                    "lại hoặc liên hệ trung tâm để được hỗ trợ."
                ),
                "code": "invalid_credentials",
            },
            status=status.HTTP_401_UNAUTHORIZED,
        )

    # Pass — reset counter, cấp token.
    was_locked = account.register_login_success(ip=ip)
    _audit_login(
        action=AuditLog.Action.LOGIN,
        phone=phone,
        ip=ip,
        ua=ua,
        reason="was_locked" if was_locked else "",
    )

    return Response({
        "access": issue_access_token(account.pk, account.phone),
        "refresh": issue_refresh_token(account.pk, account.phone),
        "account": {
            "id": account.pk,
            "phone": account.phone,
            "display_name": account.display_name,
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
    """GET /api/student/quick/<token> — quick view 24h từ link văn thư gửi tay.

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
                    "detail": (
                        "Liên kết không còn dùng được. Vui lòng đăng nhập "
                        "bằng số điện thoại."
                    ),
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


class StaffQuickTokenView(APIView):
    """POST /api/student/staff/quick-token — văn thư CRM gen link xem nhanh 24h.

    Yêu cầu Django session auth + user staff (văn thư/sale/admin). Permission
    ``students.add_studentaccount`` đã được gán cho group Văn thư trong
    ``bootstrap_data`` — tận dụng làm cờ "có quyền hỗ trợ HV". Không cần permission
    riêng, tránh phình bảng auth_permission.

    Body: ``{enrollment_id}``. Verify Enrollment + tồn tại StudentAccount cho
    SĐT của đơn (auto-provision lúc convert lead → enrollment đã đảm bảo điều
    kiện này). Trả URL đầy đủ để văn thư copy gửi tay.
    """

    # Session auth (Django default) — văn thư đăng nhập admin CRM trước.
    authentication_classes = [SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    # Group được phép gen link xem nhanh. Bootstrap_data tạo sẵn 4 group:
    # van_thu, sale, ke_toan, admin (xem [[crm-roles-flexible]]). Văn thư + admin
    # là 2 vai trò trực tiếp hỗ trợ HV; sale chỉ chốt đơn, kế toán chỉ đối soát
    # → không cần gen link xem công nợ.
    ALLOWED_GROUPS = ("van_thu", "admin")

    def post(self, request):
        user = request.user
        if not user.is_authenticated or not user.is_staff:
            return Response(
                {"detail": "Chỉ nhân viên trung tâm mới gen được link xem nhanh."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if not (
            user.is_superuser
            or user.groups.filter(name__in=self.ALLOWED_GROUPS).exists()
        ):
            return Response(
                {
                    "detail": (
                        "Chức năng này dành cho văn thư hoặc quản trị viên. "
                        "Vui lòng liên hệ admin để được cấp quyền."
                    ),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        ser = StaffQuickTokenSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        enrollment_id = ser.validated_data["enrollment_id"]

        enrollment = (
            Enrollment.objects
            .filter(pk=enrollment_id)
            .select_related("course")
            .first()
        )
        if not enrollment:
            return Response(
                {"detail": "Không tìm thấy đơn ghi danh.", "code": "enrollment_not_found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        phone = enrollment.student_phone or ""
        if not phone:
            return Response(
                {
                    "detail": "Đơn chưa có số điện thoại học viên, không thể tạo link.",
                    "code": "missing_phone",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        account = StudentAccount.objects.filter(phone=phone, is_active=True).first()
        if not account:
            return Response(
                {
                    "detail": (
                        "Tài khoản học viên chưa được tạo hoặc đã bị khóa. "
                        "Vui lòng kiểm tra trong CRM."
                    ),
                    "code": "account_missing",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        token = issue_quick_token(account.pk, account.phone, enrollment.pk)

        from django.conf import settings as dj_settings

        student_url = dj_settings.SITE_STUDENT_URL.rstrip("/")
        url = f"{student_url}/quick/{token}"

        masked_phone = phone[:3] + "****" + phone[-3:] if len(phone) >= 7 else "***"
        AuditLog.objects.create(
            user=request.user if request.user.is_authenticated else None,
            action=AuditLog.Action.CREATE,
            target_model="students.QuickToken",
            target_id=str(enrollment.pk),
            changes={"phone_masked": masked_phone, "ttl_seconds": QUICK_TTL_SECONDS},
            ip_address=_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:255],
        )

        return Response({
            "url": url,
            "expires_in_seconds": QUICK_TTL_SECONDS,
            "enrollment_code": enrollment.code,
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
                        "phản hồi trong vòng 72 giờ."
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
