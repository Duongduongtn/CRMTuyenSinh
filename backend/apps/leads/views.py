"""Views cho lead: capture (public) + admin viewset."""
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, ScopedRateThrottle

from .models import Lead, LeadContact, LeadReason
from .serializers import (
    LeadCaptureSerializer,
    LeadContactSerializer,
    LeadDetailSerializer,
    LeadListSerializer,
    LeadReasonSerializer,
)


class LeadCaptureThrottle(AnonRateThrottle):
    scope = "lead_capture"


class LeadCaptureView(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """`POST /api/leads/capture` — public, không cần auth.

    Rate limit 30/giờ/IP để chống spam. Honeypot field `website` chống bot đơn giản.
    """

    serializer_class = LeadCaptureSerializer
    permission_classes = [AllowAny]
    throttle_classes = [LeadCaptureThrottle]
    queryset = Lead.objects.none()  # CreateOnly, không list

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        lead = serializer.save()
        return Response(
            {
                "id": lead.id,
                "message": "Đã ghi nhận. Trung tâm sẽ liên hệ trong 5 phút.",
            },
            status=status.HTTP_201_CREATED,
        )


class LeadViewSet(viewsets.ModelViewSet):
    """Admin viewset cho nhân viên đã đăng nhập.

    Sale chỉ xem lead của mình + lead chưa assigned. Admin/Văn thư/Kế toán xem tất cả.
    """

    permission_classes = [IsAuthenticated]
    filterset_fields = ["status", "priority", "vehicle_class", "source", "assigned_to"]
    search_fields = ["name", "phone", "email"]
    ordering_fields = ["created_at", "last_contact_at", "next_contact_date"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = Lead.objects.select_related("assigned_to", "reason", "last_contact_by")
        user = self.request.user
        # Superuser hoặc admin/accountant/clerk: tất cả
        if user.is_superuser or user.groups.filter(name__in=["admin", "accountant", "clerk"]).exists():
            return qs
        # Sale: lead của mình + lead chưa assigned (để pickup)
        if user.groups.filter(name="sale").exists():
            return qs.filter(assigned_to__in=[user, None])
        return qs.none()

    def get_serializer_class(self):
        if self.action == "list":
            return LeadListSerializer
        return LeadDetailSerializer

    @action(detail=True, methods=["post"], serializer_class=LeadContactSerializer)
    def contact(self, request, pk=None):
        """Ghi nhận 1 lần liên hệ. Body: contact_type, status_after, priority_after, reason, note, next_contact_date."""
        lead: Lead = self.get_object()
        data = request.data

        status_after = data.get("status_after")
        if not status_after:
            return Response({"detail": "status_after là bắt buộc."}, status=status.HTTP_400_BAD_REQUEST)

        # Tạo contact qua helper trên model
        reason_id = data.get("reason")
        reason = LeadReason.objects.filter(pk=reason_id).first() if reason_id else None
        contact = lead.record_contact(
            user=request.user,
            contact_type=data.get("contact_type", "call"),
            status_after=status_after,
            priority_after=data.get("priority_after", ""),
            reason=reason,
            reason_text=data.get("reason_text", ""),
            note=data.get("note", ""),
            next_contact_date=data.get("next_contact_date"),
        )
        return Response(LeadContactSerializer(contact).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def assign(self, request, pk=None):
        """Phân lead cho 1 user cụ thể."""
        lead: Lead = self.get_object()
        user_id = request.data.get("user_id")
        if not user_id:
            return Response({"detail": "user_id là bắt buộc."}, status=status.HTTP_400_BAD_REQUEST)
        from apps.users.models import User

        target = User.objects.filter(pk=user_id, is_active=True).first()
        if not target:
            return Response({"detail": "User không tồn tại."}, status=status.HTTP_404_NOT_FOUND)
        lead.assigned_to = target
        lead.save(update_fields=["assigned_to", "updated_at"])
        return Response({"id": lead.id, "assigned_to": target.id})


class LeadReasonViewSet(viewsets.ReadOnlyModelViewSet):
    """Public read-only cho FE/admin dùng dropdown."""

    queryset = LeadReason.objects.filter(is_active=True)
    serializer_class = LeadReasonSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["status_scope"]
