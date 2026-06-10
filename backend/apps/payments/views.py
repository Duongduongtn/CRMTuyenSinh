"""Views cho app payments.

- PaymentViewSet: list/retrieve cho admin/kế toán. Manual confirm cho kế toán.
- CassoTransactionViewSet: read-only cho admin (audit Casso).
- DepositQRView: public — sinh URL QR + bank info cho FE trang /dh/[code].
"""
from decimal import Decimal

from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from apps.orders.models import Enrollment

from .models import CassoTransaction, Payment, PaymentMethod, PaymentStatus
from .serializers import (
    CassoTransactionSerializer,
    DepositQRSerializer,
    PaymentSerializer,
)
from .vietqr import build_deposit_qr_for_enrollment


class PaymentViewSet(viewsets.ModelViewSet):
    """CRUD payments cho admin/kế toán.

    Sale chỉ thấy payments của đơn họ chốt (qua enrollment.created_by).
    """

    permission_classes = [IsAuthenticated]
    serializer_class = PaymentSerializer
    filterset_fields = ["status", "method", "enrollment"]
    search_fields = ["bank_tx_id", "reference_code", "enrollment__code", "enrollment__student_name"]
    ordering_fields = ["created_at", "amount", "confirmed_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = Payment.objects.select_related(
            "enrollment", "created_by", "confirmed_by", "casso_transaction"
        )
        user = self.request.user
        if user.is_superuser or user.groups.filter(
            name__in=["admin", "accountant"]
        ).exists():
            return qs
        if user.groups.filter(name="sale").exists():
            return qs.filter(enrollment__created_by=user)
        if user.groups.filter(name="clerk").exists():
            return qs.filter(status=PaymentStatus.CONFIRMED)
        return qs.none()

    def perform_create(self, serializer):
        """Tạo payment thủ công (kế toán nhập tay khi học viên trả tiền mặt)."""
        from django.utils import timezone

        user = self.request.user
        if not (
            user.is_superuser
            or user.groups.filter(name__in=["admin", "accountant"]).exists()
        ):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("Chỉ kế toán/admin được tạo payment thủ công.")

        instance = serializer.save(
            created_by=user,
            method=PaymentMethod.MANUAL,
            status=PaymentStatus.PENDING,
        )
        return instance

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        """Kế toán xác nhận manual payment. Cộng vào paid_amount, recompute status."""
        from django.db import transaction
        from django.utils import timezone

        user = request.user
        if not (
            user.is_superuser
            or user.groups.filter(name__in=["admin", "accountant"]).exists()
        ):
            return Response(
                {"detail": "Không có quyền xác nhận."},
                status=status.HTTP_403_FORBIDDEN,
            )

        with transaction.atomic():
            # Lock enrollment TRƯỚC (rồi mới payment) — đảm bảo 2 request confirm
            # song song cùng payment KHÔNG cộng paid_amount 2 lần.
            payment_lock = Payment.objects.select_for_update().get(pk=pk)
            enrollment = Enrollment.objects.select_for_update().get(
                pk=payment_lock.enrollment_id
            )
            # Re-fetch sau khi giữ lock — caller có thể đã confirm xong trước đó.
            payment_lock.refresh_from_db()
            if payment_lock.status == PaymentStatus.CONFIRMED:
                return Response(
                    {"detail": "Đã xác nhận trước đó.", "code": "already_confirmed"},
                    status=status.HTTP_200_OK,
                )
            payment_lock.status = PaymentStatus.CONFIRMED
            payment_lock.confirmed_by = user
            payment_lock.confirmed_at = timezone.now()
            payment_lock.save(
                update_fields=["status", "confirmed_by", "confirmed_at"]
            )

            enrollment.paid_amount = (
                enrollment.paid_amount or Decimal("0")
            ) + payment_lock.amount
            enrollment.recompute_status_from_paid()
            enrollment.save(
                update_fields=[
                    "paid_amount",
                    "status",
                    "deposit_paid_at",
                    "completed_at",
                    "updated_at",
                ]
            )
            payment = payment_lock

        return Response(PaymentSerializer(payment).data)


class CassoTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only — admin/kế toán xem log raw Casso, để truy vết khi sai sót."""

    permission_classes = [IsAuthenticated]
    serializer_class = CassoTransactionSerializer
    filterset_fields = ["matched_enrollment"]
    search_fields = ["tid", "description", "matched_code"]
    ordering = ["-received_at"]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.groups.filter(
            name__in=["admin", "accountant"]
        ).exists():
            return CassoTransaction.objects.select_related("matched_enrollment").all()
        return CassoTransaction.objects.none()


class DepositLinkThrottle(AnonRateThrottle):
    scope = "deposit_link"


class DepositQRView(APIView):
    """GET /api/public/enrollments/by-token/{token}/qr — sinh URL VietQR cho FE.

    Dùng ``deposit_link_token`` (UUID 128-bit) thay vì ``code`` 6 hex để chống brute-force
    liệt kê đơn (lộ student_name + phone + amount). Rate limit 30/phút/IP.
    """

    permission_classes = [AllowAny]
    throttle_classes = [DepositLinkThrottle]

    def get(self, request, token):
        enrollment = get_object_or_404(Enrollment, deposit_link_token=token)
        try:
            data = build_deposit_qr_for_enrollment(enrollment)
        except ValueError as exc:
            return Response(
                {"detail": str(exc), "code": "bank_not_configured"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response(DepositQRSerializer(data).data)
