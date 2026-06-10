"""Views cho app orders.

- `LeadConvertView`: POST /api/admin/leads/{id}/convert (auth required, sale/admin).
- `EnrollmentViewSet`: CRUD đơn cho admin/kế toán/sale.
- `EnrollmentPublicView`: GET /api/public/enrollments/{code} cho FE trang đặt cọc.
- `EnrollmentPDFView`: GET /api/admin/enrollments/{id}/pdf — văn thư/admin in PDF.
"""
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from apps.core.models import AuditLog

from .models import Enrollment
from .pdf import PDFRenderError, render_enrollment_html, render_enrollment_pdf
from .serializers import (
    EnrollmentConvertInputSerializer,
    EnrollmentDetailSerializer,
    EnrollmentListSerializer,
    EnrollmentPublicSerializer,
)
from .services import ConvertError, convert_lead_to_enrollment


class LeadConvertView(APIView):
    """POST /api/admin/leads/{lead_id}/convert — chuyển 1 lead thành đơn ghi danh.

    Auth: sale, admin (kế toán/văn thư không có quyền chốt đơn).
    Idempotent: gọi 2 lần cùng lead trả về cùng `code` (created=false).
    Race-safe: 2 sale convert song song cùng course slot=1 → 1 success, 1 fail 409.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, lead_id: int):
        if not self._can_convert(request.user):
            return Response(
                {"detail": "Bạn không có quyền chốt đơn."},
                status=status.HTTP_403_FORBIDDEN,
            )

        input_ser = EnrollmentConvertInputSerializer(data=request.data)
        input_ser.is_valid(raise_exception=True)
        data = input_ser.validated_data

        try:
            result = convert_lead_to_enrollment(
                lead_id=lead_id,
                course_id=data["course"].id,
                user=request.user,
                student_name=data.get("student_name", ""),
                student_phone=data.get("student_phone", ""),
                student_email=data.get("student_email", ""),
                notes=data.get("notes", ""),
            )
        except ConvertError as exc:
            http_status = {
                "lead_not_found": status.HTTP_404_NOT_FOUND,
                "course_not_found": status.HTTP_404_NOT_FOUND,
                "course_full": status.HTTP_409_CONFLICT,
                "course_unavailable": status.HTTP_409_CONFLICT,
                "missing_student_info": status.HTTP_400_BAD_REQUEST,
                "code_collision": status.HTTP_500_INTERNAL_SERVER_ERROR,
            }.get(exc.code, status.HTTP_400_BAD_REQUEST)
            return Response(
                {"detail": exc.message, "code": exc.code},
                status=http_status,
            )

        out = EnrollmentDetailSerializer(
            result.enrollment, context={"request": request}
        ).data
        if not result.created:
            # Idempotent hit — REST chuẩn: 200 OK + đánh dấu để FE biết không re-trigger ZNS.
            return Response(
                {
                    "detail": "Lead đã được chuyển thành đơn trước đó.",
                    "code": "already_converted",
                    "order_code": result.enrollment.code,
                    "enrollment": out,
                },
                status=status.HTTP_200_OK,
            )
        return Response(
            {"detail": "Đã tạo đơn ghi danh.", "enrollment": out},
            status=status.HTTP_201_CREATED,
        )

    @staticmethod
    def _can_convert(user) -> bool:
        if user.is_superuser:
            return True
        return user.groups.filter(name__in=["sale", "admin"]).exists()


class EnrollmentViewSet(viewsets.ModelViewSet):
    """CRUD đơn cho nhân viên đăng nhập admin.

    Sale chỉ thấy đơn họ tạo. Admin/Kế toán xem tất cả. Văn thư xem để in PDF.

    KHÔNG cho POST/DELETE trực tiếp — đơn chỉ tạo qua endpoint convert
    (đảm bảo snapshot price + slot atomic), xóa qua action ``cancel``.
    """

    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "patch", "head", "options"]
    filterset_fields = ["status", "course", "vehicle_class", "created_by"]
    search_fields = ["code", "student_name", "student_phone"]
    ordering_fields = ["created_at", "deposit_paid_at", "paid_amount"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = Enrollment.objects.select_related("course", "created_by", "lead")
        user = self.request.user
        if user.is_superuser or user.groups.filter(
            name__in=["admin", "accountant", "clerk"]
        ).exists():
            return qs
        if user.groups.filter(name="sale").exists():
            return qs.filter(created_by=user)
        return qs.none()

    def get_serializer_class(self):
        if self.action == "list":
            return EnrollmentListSerializer
        return EnrollmentDetailSerializer

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """Hủy đơn — chỉ admin/kế toán. Hoàn lại slot cho course."""
        from django.db import transaction

        from .models import EnrollmentStatus

        if not (
            request.user.is_superuser
            or request.user.groups.filter(name__in=["admin", "accountant"]).exists()
        ):
            return Response(
                {"detail": "Không có quyền hủy đơn."},
                status=status.HTTP_403_FORBIDDEN,
            )

        with transaction.atomic():
            enrollment: Enrollment = (
                Enrollment.objects.select_for_update().get(pk=pk)
            )
            if enrollment.status in (
                EnrollmentStatus.CANCELLED,
                EnrollmentStatus.REFUNDED,
            ):
                return Response(
                    {"detail": "Đơn đã hủy trước đó."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if enrollment.paid_amount > 0:
                return Response(
                    {
                        "detail": "Đơn đã có thanh toán. Cần hoàn tiền trước khi hủy.",
                        "code": "has_payment",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            enrollment.status = EnrollmentStatus.CANCELLED
            enrollment.save(update_fields=["status", "updated_at"])

            # Hoàn slot
            from apps.courses.models import Course

            course = Course.objects.select_for_update().get(pk=enrollment.course_id)
            course.available_slots += 1
            course.save(update_fields=["available_slots", "updated_at"])

        return Response(
            EnrollmentDetailSerializer(enrollment, context={"request": request}).data
        )


class EnrollmentPDFView(APIView):
    """GET /api/admin/enrollments/{id}/pdf — văn thư/admin in PDF đơn đăng ký.

    Query ``?as=html`` → trả HTML preview (cho dev, khi WeasyPrint chưa cài).
    KHÔNG dùng tham số ``?format=`` vì DRF nó dành cho content negotiation.
    Mặc định trả PDF với header ``Content-Disposition: attachment``.

    Quyền:
    - superuser, group ``admin``, ``clerk`` (văn thư), ``accountant`` → cho phép.
    - Group ``sale`` → cho phép nếu là người tạo đơn.
    - Học viên PWA → KHÔNG dùng endpoint này (FE student xem qua /api/student/...).

    Audit log mọi lần in (view_sensitive) để truy vết khi tài liệu lộ ra ngoài.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, pk: int):
        # `select_for_update` để chốt snapshot paid_amount nhất quán với webhook Casso
        # đang chạy song song (xem payment-integration-reviewer P1.1).
        with transaction.atomic():
            enrollment: Enrollment = get_object_or_404(
                Enrollment.objects.select_for_update().select_related("course"),
                pk=pk,
            )
            if not self._can_print(request.user, enrollment):
                return Response(
                    {"detail": "Bạn không có quyền in PDF đơn này."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            fmt = (request.query_params.get("as") or "pdf").lower()
            # Ghi audit log trước khi render (kể cả khi render fail) — phục vụ điều tra.
            AuditLog.objects.create(
                user=request.user,
                action=AuditLog.Action.VIEW_SENSITIVE,
                target_model="orders.Enrollment",
                target_id=str(enrollment.pk),
                changes={"as": fmt, "action": "print_pdf"},
                ip_address=self._client_ip(request),
                user_agent=request.META.get("HTTP_USER_AGENT", "")[:255],
            )

            if fmt == "html":
                resp = HttpResponse(
                    render_enrollment_html(enrollment),
                    content_type="text/html; charset=utf-8",
                )
                self._apply_sensitive_headers(resp)
                return resp

            try:
                pdf_bytes = render_enrollment_pdf(enrollment)
            except PDFRenderError as exc:
                return Response(
                    {
                        "detail": str(exc),
                        "code": "pdf_unavailable",
                        "hint": "Thử lại với ?as=html để xem bản preview.",
                    },
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )

            resp = HttpResponse(pdf_bytes, content_type="application/pdf")
            filename = f"don-dang-ky-{enrollment.code}.pdf"
            resp["Content-Disposition"] = f'attachment; filename="{filename}"'
            self._apply_sensitive_headers(resp)
            return resp

    @staticmethod
    def _apply_sensitive_headers(resp: HttpResponse) -> None:
        """Cache-Control + X-Content-Type-Options cho file chứa CCCD (NĐ 13/2023)."""
        resp["Cache-Control"] = "private, no-store, no-cache, must-revalidate"
        resp["Pragma"] = "no-cache"
        resp["X-Content-Type-Options"] = "nosniff"
        resp["Referrer-Policy"] = "no-referrer"

    @staticmethod
    def _can_print(user, enrollment: Enrollment) -> bool:
        if user.is_superuser:
            return True
        groups = set(user.groups.values_list("name", flat=True))
        if groups & {"admin", "clerk", "accountant"}:
            return True
        if "sale" in groups and enrollment.created_by_id == user.id:
            return True
        return False

    @staticmethod
    def _client_ip(request) -> str | None:
        xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if xff:
            return xff.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")


class DepositLinkThrottle(AnonRateThrottle):
    scope = "deposit_link"


class EnrollmentPublicView(APIView):
    """GET /api/public/enrollments/by-token/{token} — không cần auth, FE polling trang đặt cọc.

    Dùng ``deposit_link_token`` (UUID 128-bit) thay vì ``code`` (6 hex) để chống
    brute-force liệt kê đơn. Token chỉ chia sẻ qua Zalo ZNS cho HV đúng đơn.

    Rate limit 30/phút/IP qua DepositLinkThrottle.
    Chỉ trả field public, KHÔNG có notes nội bộ, lead, created_by.
    """

    permission_classes = [AllowAny]
    throttle_classes = [DepositLinkThrottle]

    def get(self, request, token):
        enrollment = get_object_or_404(Enrollment, deposit_link_token=token)
        return Response(EnrollmentPublicSerializer(enrollment).data)
