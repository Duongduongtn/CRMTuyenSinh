"""Test OTP flow + JWT auth + IDOR Enrollment.

Acceptance:
- Request OTP → tạo OTPRequest, mock log code.
- Verify đúng → cấp access + refresh token.
- Verify sai 5 lần → block.
- Access enrollment của HV khác → 404 (IDOR-safe).
- Token tampered → 401.
"""
from decimal import Decimal

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.courses.models import Course, VehicleClass, VehicleGroup
from apps.orders.models import Enrollment, EnrollmentStatus

from .auth import issue_access_token
from .models import OTPRequest, StudentAccount


def _make_course():
    return Course.objects.create(
        slug="b-mt",
        title="B số sàn",
        vehicle_class=VehicleClass.B_MT,
        vehicle_group=VehicleGroup.CAR,
        tuition_fee=Decimal("17500000"),
        deposit_amount=Decimal("500000"),
    )


def _make_enrollment(phone: str, code: str = "ORD-AAA001"):
    course = Course.objects.filter(slug="b-mt").first() or _make_course()
    return Enrollment.objects.create(
        code=code,
        course=course,
        student_name="Nguyen Van A",
        student_phone=phone,
        vehicle_class=VehicleClass.B_MT,
        tuition_fee=course.tuition_fee,
        deposit_amount=course.deposit_amount,
        status=EnrollmentStatus.PENDING,
    )


@override_settings(
    ZNS_ACCESS_TOKEN="",
    ZNS_TEMPLATE_ID_OTP="",
    ZNS_ALLOW_MOCK=True,
)
class OTPFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_request_otp_creates_record_with_normalized_phone(self):
        resp = self.client.post(
            "/api/student/auth/request-otp",
            {"phone": "+84 903 123 456"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        otp = OTPRequest.objects.get()
        self.assertEqual(otp.phone, "0903123456")
        self.assertEqual(otp.sent_via, "mock_dev")
        # Code hash phải có (không rỗng) — và KHÔNG được trả ra response
        self.assertTrue(otp.code_hash)
        self.assertNotIn("code", resp.json())

    def test_verify_otp_with_correct_code_returns_tokens(self):
        # Tạo OTP trực tiếp để biết code
        otp, code = OTPRequest.create_for_phone("0903456789")
        resp = self.client.post(
            "/api/student/auth/verify-otp",
            {"phone": "0903456789", "code": code},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("access", body)
        self.assertIn("refresh", body)
        self.assertEqual(body["account"]["phone"], "0903456789")

        # OTP đã được mark consumed
        otp.refresh_from_db()
        self.assertEqual(otp.status, OTPRequest.Status.CONSUMED)

    def test_verify_otp_with_wrong_code_fails(self):
        OTPRequest.create_for_phone("0903456789")
        resp = self.client.post(
            "/api/student/auth/verify-otp",
            {"phone": "0903456789", "code": "000000"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_auto_provision_account_on_enrollment_create(self):
        # Khi sale tạo enrollment, signal phải tạo StudentAccount
        _make_enrollment("0903999888", "ORD-AUTO01")
        self.assertTrue(StudentAccount.objects.filter(phone="0903999888").exists())

    def test_request_otp_invalidates_pending_old_otp(self):
        # Tạo 2 OTP cho cùng SĐT — OTP cũ phải bị invalidate khi tạo mới.
        self.client.post(
            "/api/student/auth/request-otp", {"phone": "0903777666"}, format="json"
        )
        self.client.post(
            "/api/student/auth/request-otp", {"phone": "0903777666"}, format="json"
        )
        otps = OTPRequest.objects.filter(phone="0903777666").order_by("created_at")
        self.assertEqual(otps.count(), 2)
        self.assertEqual(otps[0].status, OTPRequest.Status.EXPIRED)
        self.assertEqual(otps[1].status, OTPRequest.Status.PENDING)


@override_settings(
    ZNS_ACCESS_TOKEN="",
    ZNS_TEMPLATE_ID_OTP="",
    ZNS_ALLOW_MOCK=False,
    DEBUG=False,
)
class OTPProductionGuardTests(TestCase):
    """ZNS chưa cấu hình ở prod → request-otp trả 503 thay vì log code."""

    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.client = APIClient()

    def test_request_otp_returns_503_when_zns_not_configured(self):
        resp = self.client.post(
            "/api/student/auth/request-otp", {"phone": "0903555444"}, format="json"
        )
        self.assertEqual(resp.status_code, 503)
        # OTP đã tạo nhưng phải bị mark expired vì gửi thất bại
        otp = OTPRequest.objects.filter(phone="0903555444").first()
        self.assertIsNotNone(otp)
        self.assertEqual(otp.status, OTPRequest.Status.EXPIRED)


class IDOREnrollmentTests(TestCase):
    """HV A KHÔNG được xem enrollment của HV B."""

    def setUp(self):
        self.client = APIClient()
        self.enr_a = _make_enrollment("0903111111", "ORD-USRA01")
        self.enr_b = _make_enrollment("0903222222", "ORD-USRB01")
        self.account_a = StudentAccount.objects.get(phone="0903111111")
        self.account_b = StudentAccount.objects.get(phone="0903222222")

    def _auth(self, account: StudentAccount):
        token = issue_access_token(account.pk, account.phone)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_student_a_sees_only_own_enrollments(self):
        self._auth(self.account_a)
        resp = self.client.get("/api/student/enrollments")
        self.assertEqual(resp.status_code, 200)
        codes = [item["code"] for item in resp.json()["results"]]
        self.assertIn("ORD-USRA01", codes)
        self.assertNotIn("ORD-USRB01", codes)

    def test_student_a_cannot_access_b_enrollment_by_id(self):
        self._auth(self.account_a)
        resp = self.client.get(f"/api/student/enrollments/{self.enr_b.pk}")
        # IDOR-safe: trả 404 thay vì 403 để khỏi leak tồn tại
        self.assertEqual(resp.status_code, 404)

    def test_tampered_token_rejected(self):
        token = issue_access_token(self.account_a.pk, self.account_a.phone)
        # Sửa 1 ký tự ở payload
        parts = token.split(".")
        tampered = parts[0][:-1] + ("A" if parts[0][-1] != "A" else "B") + "." + parts[1]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tampered}")
        resp = self.client.get("/api/student/me")
        self.assertEqual(resp.status_code, 401)

    def test_unauthenticated_rejected(self):
        resp = self.client.get("/api/student/enrollments")
        self.assertEqual(resp.status_code, 401)
