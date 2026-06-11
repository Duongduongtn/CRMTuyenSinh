"""Tests cho AuditLog middleware + signals (Sprint 3 Tuần 6).

Cover:
- Login/logout signal tạo AuditLog đúng action.
- Payment + Enrollment post_save tạo AuditLog với target_model chuẩn.
- AuditLogAdmin disable add/change (chống forge); delete chỉ superuser.
- Helper `log_audit()` lấy IP từ X-Forwarded-For qua thread-local middleware.
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, RequestFactory, TestCase, override_settings

from apps.core.admin import AuditLogAdmin
from apps.core.middleware import AuditContextMiddleware
from apps.core.models import AuditLog
from apps.core.signals import log_audit
from apps.courses.models import Course, VehicleClass
from apps.orders.models import Enrollment
from apps.payments.models import Payment, PaymentMethod, PaymentStatus

User = get_user_model()


def _make_course():
    return Course.objects.create(
        slug="b-mt-test",
        title="Khoá B-MT audit test",
        vehicle_class=VehicleClass.B_MT,
        tuition_fee=Decimal("8000000"),
        deposit_amount=Decimal("1000000"),
    )


def _make_enrollment(course, suffix="A"):
    return Enrollment.objects.create(
        code=f"ORD-TEST{suffix}",
        course=course,
        student_name=f"Nguyễn Văn {suffix}",
        student_phone="0903456789",
        tuition_fee=Decimal("8000000"),
        deposit_amount=Decimal("1000000"),
    )


class AuditLoginLogoutTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="sale1", password="pw-strong-123")
        self.client = Client()

    def test_login_creates_audit_with_login_action(self):
        ok = self.client.login(username="sale1", password="pw-strong-123")
        self.assertTrue(ok)
        log = AuditLog.objects.filter(action=AuditLog.Action.LOGIN).latest("created_at")
        self.assertEqual(log.user_id, self.user.pk)
        self.assertEqual(log.target_model, "users.user")

    def test_logout_creates_audit_with_logout_action(self):
        self.client.login(username="sale1", password="pw-strong-123")
        before = AuditLog.objects.count()
        self.client.logout()
        self.assertEqual(AuditLog.objects.count(), before + 1)
        logout_log = AuditLog.objects.latest("created_at")
        self.assertEqual(logout_log.action, AuditLog.Action.LOGOUT)
        self.assertEqual(logout_log.user_id, self.user.pk)


class AuditModelSignalTests(TestCase):
    def setUp(self):
        course = _make_course()
        self.enrollment = _make_enrollment(course)
        # Bỏ tất cả audit log do _make_course + _make_enrollment tạo ra để đếm sạch.
        AuditLog.objects.all().delete()

    def test_payment_create_creates_audit_create(self):
        Payment.objects.create(
            enrollment=self.enrollment,
            amount=Decimal("1000000"),
            method=PaymentMethod.MANUAL,
            status=PaymentStatus.CONFIRMED,
        )
        logs = AuditLog.objects.filter(
            target_model="payments.payment", action=AuditLog.Action.CREATE
        )
        self.assertEqual(logs.count(), 1)

    def test_payment_update_creates_audit_update(self):
        payment = Payment.objects.create(
            enrollment=self.enrollment,
            amount=Decimal("1000000"),
            method=PaymentMethod.MANUAL,
            status=PaymentStatus.PENDING,
        )
        AuditLog.objects.all().delete()
        payment.status = PaymentStatus.CONFIRMED
        payment.save()
        logs = AuditLog.objects.filter(
            target_model="payments.payment", action=AuditLog.Action.UPDATE
        )
        self.assertEqual(logs.count(), 1)

    def test_enrollment_save_creates_audit(self):
        course = Course.objects.create(
            slug="c-test",
            title="Khoá C test",
            vehicle_class=VehicleClass.C,
            tuition_fee=Decimal("15000000"),
            deposit_amount=Decimal("2000000"),
        )
        AuditLog.objects.all().delete()
        Enrollment.objects.create(
            course=course,
            student_name="Lê Văn C",
            student_phone="0903111222",
            tuition_fee=Decimal("15000000"),
            deposit_amount=Decimal("2000000"),
        )
        logs = AuditLog.objects.filter(
            target_model="orders.enrollment", action=AuditLog.Action.CREATE
        )
        self.assertEqual(logs.count(), 1)


class AuditAdminPermissionTests(TestCase):
    """Admin AuditLog không cho add/change. Delete chỉ superuser."""

    def test_admin_disables_add_change(self):
        admin = AuditLogAdmin(AuditLog, None)
        self.assertFalse(admin.has_add_permission(None))
        self.assertFalse(admin.has_change_permission(None))

    def test_admin_delete_only_superuser(self):
        admin = AuditLogAdmin(AuditLog, None)
        super_user = User.objects.create_superuser(username="super1", password="pw-strong-123")
        normal_user = User.objects.create_user(username="staff1", password="pw-strong-123")
        factory = RequestFactory()
        req_super = factory.get("/")
        req_super.user = super_user
        req_normal = factory.get("/")
        req_normal.user = normal_user
        self.assertTrue(admin.has_delete_permission(req_super))
        self.assertFalse(admin.has_delete_permission(req_normal))


@override_settings(TRUST_X_FORWARDED_FOR=True)
class LogAuditHelperTests(TestCase):
    """Helper log_audit() lấy IP từ X-Forwarded-For qua thread-local middleware.

    Cần `TRUST_X_FORWARDED_FOR=True` (đứng sau proxy) để honor header forwarded.
    """

    def test_log_audit_with_xff_captures_client_ip(self):
        user = User.objects.create_user(username="clerk1", password="pw-strong-123")
        course = _make_course()
        enrollment = _make_enrollment(course)
        AuditLog.objects.all().delete()

        factory = RequestFactory()
        request = factory.get(
            "/api/student/documents/1/file",
            HTTP_X_FORWARDED_FOR="203.0.113.7, 10.0.0.1",
            HTTP_USER_AGENT="pytest-client",
        )
        request.user = user

        middleware = AuditContextMiddleware(get_response=lambda r: None)
        captured = {}

        def fake_response(req):
            captured["log"] = log_audit(user, AuditLog.Action.VIEW_SENSITIVE, enrollment)
            return None

        middleware.get_response = fake_response
        middleware(request)

        log = captured["log"]
        self.assertEqual(log.ip_address, "203.0.113.7")
        self.assertEqual(log.user_agent, "pytest-client")
        self.assertEqual(log.target_model, "orders.enrollment")
        self.assertEqual(log.action, AuditLog.Action.VIEW_SENSITIVE)
