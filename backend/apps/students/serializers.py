"""DRF serializers cho học viên — login OTP + dashboard."""
from __future__ import annotations

import re

from rest_framework import serializers

from apps.orders.models import Enrollment
from .models import Person, StudentAccount, normalize_phone


PHONE_RE = re.compile(r"^0\d{9}$")


class PhoneField(serializers.CharField):
    """SĐT VN — normalize trước, validate format ``0xxxxxxxxx``."""

    def to_internal_value(self, data):
        normalized = normalize_phone(str(data or ""))
        if not PHONE_RE.match(normalized):
            raise serializers.ValidationError(
                "Số điện thoại không hợp lệ. Định dạng đúng: 10 số, bắt đầu bằng 0."
            )
        return normalized


class OTPRequestSerializer(serializers.Serializer):
    phone = PhoneField(max_length=15)


class OTPVerifySerializer(serializers.Serializer):
    phone = PhoneField(max_length=15)
    code = serializers.RegexField(r"^\d{6}$", error_messages={
        "invalid": "Mã OTP gồm đúng 6 chữ số.",
    })


class RefreshSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class PersonShortSerializer(serializers.ModelSerializer):
    """Dùng nested trong dashboard — KHÔNG trả CCCD đầy đủ.

    CCCD chỉ trả 4 số cuối để hiển thị, FE xem chi tiết phải gọi endpoint riêng
    (sẽ log audit). Học viên xem được CCCD chính mình; tài khoản mẹ xem hộ con
    cũng được vì đã có ``AccountPersonLink``.
    """

    id_number_last4 = serializers.SerializerMethodField()

    class Meta:
        model = Person
        fields = ("id", "full_name", "id_number_last4", "date_of_birth", "gender")

    def get_id_number_last4(self, obj: Person) -> str:
        if not obj.id_number or len(obj.id_number) < 4:
            return ""
        return obj.id_number[-4:]


class EnrollmentDashboardSerializer(serializers.ModelSerializer):
    """Item enrollment hiển thị trong dashboard PWA — gọn, không leak nội bộ."""

    course_title = serializers.CharField(source="course.title", read_only=True)
    course_slug = serializers.CharField(source="course.slug", read_only=True)
    vehicle_class_display = serializers.CharField(
        source="get_vehicle_class_display", read_only=True
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    remaining_amount = serializers.DecimalField(
        max_digits=12, decimal_places=0, read_only=True
    )
    person = PersonShortSerializer(read_only=True)
    docs_missing = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Enrollment
        fields = (
            "id",
            "code",
            "course_title",
            "course_slug",
            "vehicle_class",
            "vehicle_class_display",
            "status",
            "status_display",
            "tuition_fee",
            "deposit_amount",
            "paid_amount",
            "remaining_amount",
            "deposit_link_token",
            "created_at",
            "deposit_paid_at",
            "completed_at",
            "person",
            "docs_missing",
        )


class QuickEnrollmentSerializer(serializers.ModelSerializer):
    """Serializer cho quick-view (link Zalo ZNS 24h).

    Read-only, scope cứng vào 1 enrollment. KHÔNG trả:
    - notes nội bộ
    - lead_id, created_by (lộ phân công sale)
    - deposit_link_token (chỉ link đặt cọc gốc mới có)
    - student_email (chống enumeration)

    Trả thêm ``bank`` info từ SiteSettings để HV biết chuyển khoản tiếp.
    """

    course_title = serializers.CharField(source="course.title", read_only=True)
    course_slug = serializers.CharField(source="course.slug", read_only=True)
    vehicle_class_display = serializers.CharField(
        source="get_vehicle_class_display", read_only=True
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    remaining_amount = serializers.DecimalField(
        max_digits=12, decimal_places=0, read_only=True
    )
    student_phone_masked = serializers.SerializerMethodField()

    class Meta:
        model = Enrollment
        fields = (
            "id",
            "code",
            "course_title",
            "course_slug",
            "vehicle_class",
            "vehicle_class_display",
            "status",
            "status_display",
            "tuition_fee",
            "deposit_amount",
            "paid_amount",
            "remaining_amount",
            "student_name",
            "student_phone_masked",
            "created_at",
            "deposit_paid_at",
            "completed_at",
        )

    def get_student_phone_masked(self, obj: Enrollment) -> str:
        phone = obj.student_phone or ""
        if len(phone) < 7:
            return "***"
        return phone[:4] + "***" + phone[-3:]


class StudentMeSerializer(serializers.ModelSerializer):
    """Thông tin tài khoản đăng nhập + danh sách persons đã link."""

    persons = serializers.SerializerMethodField()

    class Meta:
        model = StudentAccount
        fields = ("id", "phone", "display_name", "last_login_at", "persons")

    def get_persons(self, obj: StudentAccount):
        persons = [link.person for link in obj.person_links.select_related("person").all()]
        return PersonShortSerializer(persons, many=True).data


class DeleteRequestSerializer(serializers.Serializer):
    """Body cho POST /api/student/me/delete-request.

    Lý do không bắt buộc theo NĐ 13/2023 — chủ thể dữ liệu có quyền yêu cầu
    xóa mà không cần giải trình. Tuy nhiên giới hạn 500 ký tự để tránh spam.
    """

    reason = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        default="",
    )


class PersonUpdateSerializer(serializers.ModelSerializer):
    """HV tự cập nhật thông tin cá nhân Person.

    KHÔNG cho phép sửa ``id_number`` qua API này — phải qua văn thư duyệt
    để chống giả mạo. Sửa CCCD chỉ thực hiện trong admin CRM.
    """

    class Meta:
        model = Person
        fields = (
            "full_name",
            "date_of_birth",
            "gender",
            "permanent_address",
            "current_address",
        )
