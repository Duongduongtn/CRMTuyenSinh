"""Test 3 tiêu chí xong cho Sprint 1 Tuần 3a.

1. Idempotent: convert lead 2 lần → 2nd trả 400 + order_code cũ.
2. Race-safe: 2 lead cùng course slots=1 → 1 success, 1 fail course_full.
3. Atomic snapshot: enrollment giữ price snapshot ngay cả khi course đổi giá sau.

Chạy: ``python manage.py test apps.orders``.
"""
from decimal import Decimal

from django.contrib.auth.models import Group
from django.test import TestCase
from rest_framework.test import APIClient

from apps.courses.models import Course, VehicleClass, VehicleGroup
from apps.leads.models import Lead
from apps.users.models import User

from .models import Enrollment, EnrollmentStatus
from .services import ConvertError, convert_lead_to_enrollment


class ConvertLeadTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.sale_group, _ = Group.objects.get_or_create(name="sale")
        cls.admin_group, _ = Group.objects.get_or_create(name="admin")

        cls.sale_user = User.objects.create_user(
            username="sale1", password="x", full_name="Sale 1"
        )
        cls.sale_user.groups.add(cls.sale_group)

        cls.course = Course.objects.create(
            slug="test-b-mt",
            title="Test B số sàn",
            vehicle_class=VehicleClass.B_MT,
            vehicle_group=VehicleGroup.CAR,
            tuition_fee=Decimal("17500000"),
            deposit_amount=Decimal("1000000"),
            total_slots=5,
            available_slots=5,
        )

    def _make_lead(self, name="Nguyễn Văn A", phone="0901234567"):
        return Lead.objects.create(name=name, phone=phone)

    # --- 1. Idempotent ---

    def test_convert_lead_twice_returns_existing_enrollment(self):
        """Tiêu chí 1: convert 2 lần cùng 1 lead → 2nd KHÔNG tạo mới."""
        lead = self._make_lead()
        result1 = convert_lead_to_enrollment(
            lead_id=lead.id,
            course_id=self.course.id,
            user=self.sale_user,
        )
        self.assertTrue(result1.created)
        first_code = result1.enrollment.code

        # Lần 2 phải trả enrollment cũ với created=False
        result2 = convert_lead_to_enrollment(
            lead_id=lead.id,
            course_id=self.course.id,
            user=self.sale_user,
        )
        self.assertFalse(result2.created)
        self.assertEqual(result2.enrollment.code, first_code)
        # Slot KHÔNG bị trừ 2 lần
        self.course.refresh_from_db()
        self.assertEqual(self.course.available_slots, 4)

    def test_convert_api_idempotent_returns_400_with_old_code(self):
        """API convert 2 lần → lần 2 HTTP 400 kèm order_code cũ."""
        lead = self._make_lead()
        client = APIClient()
        client.force_authenticate(self.sale_user)

        url = f"/api/admin/leads/{lead.id}/convert"
        body = {"course": self.course.id}
        resp1 = client.post(url, body, format="json")
        self.assertEqual(resp1.status_code, 201, resp1.data)
        first_code = resp1.data["enrollment"]["code"]

        resp2 = client.post(url, body, format="json")
        # REST chuẩn idempotent: 200 OK (KHÔNG phải 400) — FE retry không tưởng lỗi
        self.assertEqual(resp2.status_code, 200)
        self.assertEqual(resp2.data["code"], "already_converted")
        self.assertEqual(resp2.data["order_code"], first_code)

    # --- 2. Race-safe ---

    def test_two_converts_same_course_with_one_slot_only_one_succeeds(self):
        """Tiêu chí 3 (race): course slots=1 + 2 lead khác nhau → 1 success, 1 course_full."""
        self.course.available_slots = 1
        self.course.total_slots = 1
        self.course.save(update_fields=["available_slots", "total_slots"])

        lead_a = self._make_lead(name="HV A", phone="0901111111")
        lead_b = self._make_lead(name="HV B", phone="0902222222")

        # Lead A convert trước
        result_a = convert_lead_to_enrollment(
            lead_id=lead_a.id,
            course_id=self.course.id,
            user=self.sale_user,
        )
        self.assertTrue(result_a.created)

        # Lead B convert sau khi slot = 0 → ConvertError course_full
        with self.assertRaises(ConvertError) as ctx:
            convert_lead_to_enrollment(
                lead_id=lead_b.id,
                course_id=self.course.id,
                user=self.sale_user,
            )
        self.assertEqual(ctx.exception.code, "course_full")

        # Đảm bảo chỉ 1 enrollment tạo ra cho course này
        self.assertEqual(Enrollment.objects.filter(course=self.course).count(), 1)
        # Lead B vẫn chưa convert
        lead_b.refresh_from_db()
        self.assertFalse(lead_b.converted_to_order)

    # --- 3. Atomic snapshot ---

    def test_enrollment_snapshots_price_at_convert_time(self):
        """Đơn ghi nhận học phí + cọc TẠI THỜI ĐIỂM convert, không follow course sau."""
        lead = self._make_lead()
        result = convert_lead_to_enrollment(
            lead_id=lead.id,
            course_id=self.course.id,
            user=self.sale_user,
        )
        enrollment = result.enrollment
        original_fee = enrollment.tuition_fee
        original_deposit = enrollment.deposit_amount

        # Đổi giá khóa
        self.course.tuition_fee = Decimal("99999999")
        self.course.deposit_amount = Decimal("88888888")
        self.course.save()

        enrollment.refresh_from_db()
        self.assertEqual(enrollment.tuition_fee, original_fee)
        self.assertEqual(enrollment.deposit_amount, original_deposit)

    # --- 4. Validations + helpers ---

    def test_enrollment_code_format(self):
        """Mã đơn ORD-XXXXXX với 6 ký tự hex viết hoa."""
        lead = self._make_lead()
        result = convert_lead_to_enrollment(
            lead_id=lead.id,
            course_id=self.course.id,
            user=self.sale_user,
        )
        code = result.enrollment.code
        self.assertTrue(code.startswith("ORD-"))
        hex_part = code[4:]
        self.assertEqual(len(hex_part), 6)
        self.assertTrue(all(c in "0123456789ABCDEF" for c in hex_part))

    def test_convert_unauthorized_user_returns_403(self):
        """User không thuộc sale/admin → 403."""
        lead = self._make_lead()
        other = User.objects.create_user(username="other", password="x")
        client = APIClient()
        client.force_authenticate(other)
        resp = client.post(
            f"/api/admin/leads/{lead.id}/convert",
            {"course": self.course.id},
            format="json",
        )
        self.assertEqual(resp.status_code, 403)

    def test_recompute_status_from_paid(self):
        """Status tự cập nhật theo paid_amount."""
        lead = self._make_lead()
        result = convert_lead_to_enrollment(
            lead_id=lead.id,
            course_id=self.course.id,
            user=self.sale_user,
        )
        enr = result.enrollment
        self.assertEqual(enr.status, EnrollmentStatus.PENDING)

        # Đóng đúng cọc
        enr.paid_amount = enr.deposit_amount
        enr.recompute_status_from_paid()
        self.assertEqual(enr.status, EnrollmentStatus.DEPOSITED)

        # Đóng thêm
        enr.paid_amount = enr.deposit_amount + Decimal("500000")
        enr.recompute_status_from_paid()
        self.assertEqual(enr.status, EnrollmentStatus.PARTIAL)

        # Đóng đủ
        enr.paid_amount = enr.tuition_fee
        enr.recompute_status_from_paid()
        self.assertEqual(enr.status, EnrollmentStatus.COMPLETED)
        self.assertIsNotNone(enr.completed_at)
