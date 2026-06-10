"""DRF serializers cho app orders."""
from rest_framework import serializers

from apps.courses.models import Course

from .models import Enrollment


class EnrollmentConvertInputSerializer(serializers.Serializer):
    """Input cho API convert lead → enrollment.

    Cho phép override `student_name` / `student_phone` nếu sale phát hiện lead nhập sai.
    Course bắt buộc — sale tư vấn xong mới biết HV chọn khóa nào.
    """

    course = serializers.PrimaryKeyRelatedField(queryset=Course.objects.all())
    student_name = serializers.CharField(max_length=200, required=False, allow_blank=True)
    student_phone = serializers.CharField(max_length=15, required=False, allow_blank=True)
    student_email = serializers.EmailField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_student_phone(self, value: str) -> str:
        if not value:
            return value
        cleaned = "".join(c for c in value if c.isdigit())
        if not cleaned.startswith("0") or len(cleaned) != 10:
            raise serializers.ValidationError(
                "Số điện thoại không hợp lệ. Định dạng đúng: 0xxxxxxxxx (10 số)."
            )
        return cleaned


class EnrollmentListSerializer(serializers.ModelSerializer):
    """List view — gọn, dùng cho danh sách trong admin."""

    course_title = serializers.CharField(source="course.title", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    remaining_amount = serializers.DecimalField(
        max_digits=12, decimal_places=0, read_only=True
    )

    class Meta:
        model = Enrollment
        fields = [
            "id",
            "code",
            "student_name",
            "student_phone",
            "course",
            "course_title",
            "vehicle_class",
            "tuition_fee",
            "deposit_amount",
            "paid_amount",
            "remaining_amount",
            "status",
            "status_display",
            "created_at",
            "deposit_paid_at",
        ]


class EnrollmentDetailSerializer(serializers.ModelSerializer):
    """Detail view — đầy đủ + link đặt cọc public."""

    course_title = serializers.CharField(source="course.title", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    remaining_amount = serializers.DecimalField(
        max_digits=12, decimal_places=0, read_only=True
    )
    deposit_url = serializers.SerializerMethodField()
    created_by_name = serializers.CharField(
        source="created_by.get_display_name", read_only=True, default=""
    )

    class Meta:
        model = Enrollment
        fields = "__all__"
        read_only_fields = [
            "code",
            "deposit_link_token",
            "paid_amount",
            "created_at",
            "updated_at",
            "deposit_paid_at",
            "completed_at",
        ]

    def get_deposit_url(self, obj: Enrollment) -> str:
        """Link trang đặt cọc public dùng UUID token thay vì code 6 hex
        để chống brute-force enum đơn."""
        from django.conf import settings as dj_settings

        base = dj_settings.SITE_PUBLIC_URL.rstrip("/")
        return f"{base}/dh/{obj.deposit_link_token}"


class EnrollmentPublicSerializer(serializers.ModelSerializer):
    """Public view cho trang `/dh/[code]` — chỉ field cần để render QR + polling.

    KHÔNG expose: lead, created_by, notes nội bộ, email, deposit_link_token.
    """

    course_title = serializers.CharField(source="course.title", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    is_deposit_paid = serializers.BooleanField(read_only=True)

    class Meta:
        model = Enrollment
        fields = [
            "code",
            "course_title",
            "vehicle_class",
            "student_name",
            "tuition_fee",
            "deposit_amount",
            "paid_amount",
            "status",
            "status_display",
            "is_deposit_paid",
            "created_at",
        ]
