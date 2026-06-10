"""Test endpoint PDF + render HTML.

Acceptance:
- HTML preview render OK với data đầy đủ (brand không hard-code).
- Quyền: admin/clerk/accountant → 200; sale tạo đơn → 200; sale khác → 403.
- Format=pdf: nếu WeasyPrint chưa cài → 503, ?as=html vẫn OK.
- Audit log được tạo mỗi lần xem.
"""
from __future__ import annotations

from decimal import Decimal

from django.contrib.auth.models import Group
from django.test import TestCase
from rest_framework.test import APIClient

from apps.core.models import AuditLog, SiteSettings
from apps.courses.models import Course, VehicleClass, VehicleGroup
from apps.orders.models import Enrollment, EnrollmentStatus
from apps.users.models import User


def _make_course():
    return Course.objects.create(
        slug="b-mt",
        title="B số sàn",
        vehicle_class=VehicleClass.B_MT,
        vehicle_group=VehicleGroup.CAR,
        tuition_fee=Decimal("17500000"),
        deposit_amount=Decimal("500000"),
    )


def _make_enrollment(creator: User | None = None, code: str = "ORD-PDF001") -> Enrollment:
    course = Course.objects.filter(slug="b-mt").first() or _make_course()
    return Enrollment.objects.create(
        code=code,
        course=course,
        student_name="Nguyễn Văn A",
        student_phone="0903123456",
        student_email="a@example.vn",
        vehicle_class=VehicleClass.B_MT,
        tuition_fee=Decimal("17500000"),
        deposit_amount=Decimal("500000"),
        paid_amount=Decimal("500000"),
        status=EnrollmentStatus.DEPOSITED,
        created_by=creator,
    )


class EnrollmentPDFViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        # Tạo group chuẩn
        for name in ("admin", "clerk", "accountant", "sale"):
            Group.objects.get_or_create(name=name)
        # Set brand name tùy biến để verify không hard-code
        site = SiteSettings.get_solo()
        site.brand_name = "Trung tâm Thử Nghiệm"
        site.hotline_display = "0911.000.999"
        site.save()

    def _login(self, group_name: str) -> User:
        import secrets

        user = User.objects.create_user(
            username=f"u_{group_name}_{secrets.token_hex(3)}",
            phone="",
            password="x",
        )
        user.groups.add(Group.objects.get(name=group_name))
        self.client.force_authenticate(user=user)
        return user

    def test_html_preview_contains_brand_and_no_hardcode(self):
        self._login("admin")
        enr = _make_enrollment()
        resp = self.client.get(f"/api/admin/enrollments/{enr.pk}/pdf?as=html")
        self.assertEqual(resp.status_code, 200)
        body = resp.content.decode("utf-8")
        # Brand từ SiteSettings — KHÔNG hard-code "Đông Á"
        self.assertIn("Trung tâm Thử Nghiệm", body)
        self.assertIn("0911.000.999", body)
        self.assertIn("ORD-PDF001", body)
        # Số tiền hiển thị format VN có phân cách
        self.assertIn("17.500.000", body)
        self.assertIn("Đơn đăng ký học lái xe", body)

    def test_clerk_can_print(self):
        self._login("clerk")
        enr = _make_enrollment()
        resp = self.client.get(f"/api/admin/enrollments/{enr.pk}/pdf?as=html")
        self.assertEqual(resp.status_code, 200)

    def test_sale_owner_can_print_own_enrollment(self):
        sale = self._login("sale")
        enr = _make_enrollment(creator=sale)
        resp = self.client.get(f"/api/admin/enrollments/{enr.pk}/pdf?as=html")
        self.assertEqual(resp.status_code, 200)

    def test_sale_cannot_print_others_enrollment(self):
        # Tạo enrollment do sale khác làm
        other_sale = User.objects.create_user(
            username="u_other_sale", phone="0900099999", password="x"
        )
        other_sale.groups.add(Group.objects.get(name="sale"))
        enr = _make_enrollment(creator=other_sale)
        # Đăng nhập sale mới (không phải owner)
        self._login("sale")
        resp = self.client.get(f"/api/admin/enrollments/{enr.pk}/pdf?as=html")
        self.assertEqual(resp.status_code, 403)

    def test_unauthenticated_rejected(self):
        enr = _make_enrollment()
        resp = self.client.get(f"/api/admin/enrollments/{enr.pk}/pdf?as=html")
        # DRF không có www-authenticate challenge → trả 403 cho anonymous
        # với SessionAuthentication default. Cả hai đều đủ chặn truy cập.
        self.assertIn(resp.status_code, (401, 403))

    def test_audit_log_created_on_each_view(self):
        self._login("admin")
        enr = _make_enrollment()
        self.client.get(f"/api/admin/enrollments/{enr.pk}/pdf?as=html")
        log = AuditLog.objects.filter(
            target_model="orders.Enrollment", target_id=str(enr.pk)
        ).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.action, AuditLog.Action.VIEW_SENSITIVE)
        self.assertEqual(log.changes.get("action"), "print_pdf")

    def test_sensitive_cache_headers(self):
        # NĐ 13/2023 Điều 21: PDF chứa CCCD KHÔNG được cache.
        self._login("admin")
        enr = _make_enrollment()
        resp = self.client.get(f"/api/admin/enrollments/{enr.pk}/pdf?as=html")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("no-store", resp["Cache-Control"])
        self.assertEqual(resp["X-Content-Type-Options"], "nosniff")
        self.assertEqual(resp["Referrer-Policy"], "no-referrer")

    def test_cccd_masked_in_template(self):
        # CCCD đầy đủ KHÔNG xuất hiện trong PDF — chỉ hiện 3 đầu + 4 cuối + che giữa.
        from apps.students.models import (
            AccountPersonLink,
            Person,
            StudentAccount,
        )

        enr = _make_enrollment()
        account = StudentAccount.objects.get(phone=enr.student_phone)
        person = Person.objects.create(
            full_name="Nguyễn Văn A",
            id_number="012345678901",
        )
        AccountPersonLink.objects.create(
            account=account, person=person, is_primary=True
        )
        self._login("admin")
        resp = self.client.get(f"/api/admin/enrollments/{enr.pk}/pdf?as=html")
        self.assertEqual(resp.status_code, 200)
        body = resp.content.decode("utf-8")
        self.assertNotIn("012345678901", body)
        # 3 đầu + 4 cuối phải còn
        self.assertIn("012", body)
        self.assertIn("8901", body)
        # Phải có ký tự mask
        self.assertIn("•", body)
