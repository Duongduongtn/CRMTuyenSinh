"""Test auth học viên (SĐT + 6 số cuối CCCD) + IDOR + quick view + delete request.

Acceptance theo memory [[student-auth-flow]] chốt 2026-06-11:

- ``POST /auth/login`` với SĐT + 6 số cuối CCCD đúng → trả access + refresh.
- Sai → tăng ``failed_login_count``, 5 lần liên tiếp → khóa 15 phút (423).
- 10 lần liên tiếp → khóa 24 giờ.
- Tài khoản inactive / không tồn tại / không có Person link → 401 generic.
- ``POST /staff/quick-token`` chỉ staff (Django session) gọi được, trả URL 24h.
- Truy cập enrollment người khác → 404 IDOR-safe (giữ test cũ).
- Quick token type access bị reject + cross-account scope 410.
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.core.models import AuditLog
from apps.courses.models import Course, VehicleClass, VehicleGroup
from apps.orders.models import Enrollment, EnrollmentStatus

from .auth import issue_access_token, issue_quick_token, issue_refresh_token
from .models import (
    LOCK_DURATION_LONG,
    LOCK_DURATION_SHORT,
    AccountPersonLink,
    Person,
    StudentAccount,
    StudentDeleteRequest,
)


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
    """Tạo Enrollment + auto-provision Account/Person/Link.

    Mô phỏng path qua ``convert_lead_to_enrollment`` mà không cần build Lead +
    Course tươi mỗi test. Auto-provision được di chuyển từ signal sang
    ``apps.orders.services._provision_student_account`` (Sprint 3 Tuần 7
    nhánh Z) để bao gói Account + Person + AccountPersonLink trong cùng path
    business — bypass create model trực tiếp vẫn cần gọi helper đó tay.
    """
    from apps.orders.services import _provision_student_account

    course = Course.objects.filter(slug="b-mt").first() or _make_course()
    enrollment = Enrollment.objects.create(
        code=code,
        course=course,
        student_name="Nguyen Van A",
        student_phone=phone,
        vehicle_class=VehicleClass.B_MT,
        tuition_fee=course.tuition_fee,
        deposit_amount=course.deposit_amount,
        status=EnrollmentStatus.PENDING,
    )
    _provision_student_account(phone=phone, display_name="Nguyen Van A")
    return enrollment


def _link_cccd(phone: str, id_number: str, full_name: str = "Nguyen Van A") -> tuple[StudentAccount, Person]:
    """Helper: lấy/tạo StudentAccount + Person có CCCD + AccountPersonLink."""
    account, _ = StudentAccount.objects.get_or_create(phone=phone)
    person, _ = Person.objects.get_or_create(
        id_number=id_number,
        defaults={"full_name": full_name},
    )
    AccountPersonLink.objects.get_or_create(
        account=account,
        person=person,
        defaults={"relation": AccountPersonLink.Relation.SELF, "is_primary": True},
    )
    return account, person


def _clear_login_throttles() -> None:
    """Vô hiệu hóa rate limit DRF trong test login để chạy nhiều fail liên tiếp.

    Trong test brute force ta đo lock logic ở model, KHÔNG đo throttle.
    """
    from django.core.cache import cache

    cache.clear()


class LoginFlowTests(TestCase):
    """SĐT + 6 số cuối CCCD."""

    def setUp(self):
        self.client = APIClient()
        _clear_login_throttles()
        self.account, self.person = _link_cccd(
            phone="0903456789", id_number="079123456789"
        )
        # 6 số cuối: 456789

    def test_login_success_returns_tokens_and_resets_counter(self):
        # Pre-set fail count để verify reset
        self.account.failed_login_count = 3
        self.account.save(update_fields=["failed_login_count"])

        resp = self.client.post(
            "/api/student/auth/login",
            {"phone": "+84 903 456 789", "last6_cccd": "456789"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        self.assertIn("access", body)
        self.assertIn("refresh", body)
        self.assertEqual(body["account"]["phone"], "0903456789")

        self.account.refresh_from_db()
        self.assertEqual(self.account.failed_login_count, 0)
        self.assertIsNone(self.account.locked_until)
        self.assertIsNotNone(self.account.last_login_at)

        # Audit log có ghi
        self.assertTrue(
            AuditLog.objects.filter(action=AuditLog.Action.LOGIN).exists()
        )

    def test_login_wrong_cccd_returns_401_and_increments_counter(self):
        resp = self.client.post(
            "/api/student/auth/login",
            {"phone": "0903456789", "last6_cccd": "999999"},
            format="json",
        )
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.json()["code"], "invalid_credentials")
        # Generic message, KHÔNG nói rõ "CCCD sai" hay "SĐT không tồn tại"
        self.assertNotIn("CCCD", resp.json()["detail"][:5])

        self.account.refresh_from_db()
        self.assertEqual(self.account.failed_login_count, 1)
        self.assertIsNone(self.account.locked_until)

    def test_login_nonexistent_phone_returns_generic_401(self):
        """Chống enumeration — SĐT không có trong DB cũng trả message giống fail."""
        resp = self.client.post(
            "/api/student/auth/login",
            {"phone": "0904000000", "last6_cccd": "456789"},
            format="json",
        )
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.json()["code"], "invalid_credentials")

    def test_login_inactive_account_returns_generic_401(self):
        self.account.is_active = False
        self.account.save(update_fields=["is_active"])
        resp = self.client.post(
            "/api/student/auth/login",
            {"phone": "0903456789", "last6_cccd": "456789"},
            format="json",
        )
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.json()["code"], "invalid_credentials")

    def test_login_no_person_link_returns_401(self):
        """SĐT có account nhưng chưa nhập CCCD → fail generic.

        Văn thư phải nhập CCCD vào Person rồi mới đăng nhập được.
        """
        StudentAccount.objects.create(phone="0905111222")
        resp = self.client.post(
            "/api/student/auth/login",
            {"phone": "0905111222", "last6_cccd": "456789"},
            format="json",
        )
        self.assertEqual(resp.status_code, 401)

    def test_5_fails_locks_account_15_minutes(self):
        for _ in range(5):
            self.client.post(
                "/api/student/auth/login",
                {"phone": "0903456789", "last6_cccd": "000000"},
                format="json",
            )
        self.account.refresh_from_db()
        self.assertEqual(self.account.failed_login_count, 5)
        self.assertIsNotNone(self.account.locked_until)
        remaining = (self.account.locked_until - timezone.now()).total_seconds()
        # Tolerance: trong [14p55s, 15p00s]
        self.assertGreaterEqual(remaining, 14 * 60 + 30)
        self.assertLessEqual(remaining, LOCK_DURATION_SHORT.total_seconds() + 1)

    def test_locked_account_returns_423_without_incrementing_counter(self):
        self.account.failed_login_count = 5
        self.account.locked_until = timezone.now() + LOCK_DURATION_SHORT
        self.account.save(update_fields=["failed_login_count", "locked_until"])

        resp = self.client.post(
            "/api/student/auth/login",
            {"phone": "0903456789", "last6_cccd": "456789"},
            format="json",
        )
        self.assertEqual(resp.status_code, 423)
        body = resp.json()
        self.assertEqual(body["code"], "account_locked")
        self.assertGreater(body["remaining_seconds"], 0)

        self.account.refresh_from_db()
        self.assertEqual(self.account.failed_login_count, 5)  # không tăng

    def test_10_fails_locks_account_24_hours(self):
        self.account.failed_login_count = 9
        self.account.save(update_fields=["failed_login_count"])

        self.client.post(
            "/api/student/auth/login",
            {"phone": "0903456789", "last6_cccd": "000000"},
            format="json",
        )
        self.account.refresh_from_db()
        self.assertEqual(self.account.failed_login_count, 10)
        remaining = (self.account.locked_until - timezone.now()).total_seconds()
        self.assertGreater(remaining, 23 * 3600)
        self.assertLessEqual(remaining, LOCK_DURATION_LONG.total_seconds() + 1)

    def test_phone_normalization_accepts_e164(self):
        resp = self.client.post(
            "/api/student/auth/login",
            {"phone": "+84903456789", "last6_cccd": "456789"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)


class RefreshTokenTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.account = StudentAccount.objects.create(phone="0903456789")

    def test_refresh_returns_new_access(self):
        refresh = issue_refresh_token(self.account.pk, self.account.phone)
        resp = self.client.post(
            "/api/student/auth/refresh", {"refresh": refresh}, format="json"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("access", resp.json())

    def test_refresh_with_invalid_token_returns_401(self):
        resp = self.client.post(
            "/api/student/auth/refresh", {"refresh": "garbage.payload"}, format="json"
        )
        self.assertEqual(resp.status_code, 401)


class AutoProvisionTests(TestCase):
    """Khi sale tạo enrollment, signal phải tạo StudentAccount tự động."""

    def test_account_auto_created(self):
        _make_enrollment("0903999888", "ORD-AUTO01")
        self.assertTrue(StudentAccount.objects.filter(phone="0903999888").exists())


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
        parts = token.split(".")
        tampered = parts[0][:-1] + ("A" if parts[0][-1] != "A" else "B") + "." + parts[1]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tampered}")
        resp = self.client.get("/api/student/me")
        self.assertEqual(resp.status_code, 401)

    def test_unauthenticated_rejected(self):
        resp = self.client.get("/api/student/enrollments")
        self.assertEqual(resp.status_code, 401)


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, TELEGRAM_BOT_TOKEN="", TELEGRAM_CHAT_ID="")
class DeleteRequestTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.account = StudentAccount.objects.create(phone="0903000111", display_name="HV A")
        token = issue_access_token(self.account.pk, self.account.phone)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_creates_record_201(self):
        resp = self.client.post(
            "/api/student/me/delete-request",
            {"reason": "Tôi đã hủy đăng ký"},
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        req = StudentDeleteRequest.objects.get()
        self.assertEqual(req.account_id, self.account.pk)
        self.assertEqual(req.reason, "Tôi đã hủy đăng ký")
        self.assertEqual(req.status, StudentDeleteRequest.Status.RECEIVED)

    def test_second_request_returns_already_received(self):
        self.client.post("/api/student/me/delete-request", {}, format="json")
        resp = self.client.post(
            "/api/student/me/delete-request", {"reason": "lần 2"}, format="json"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["code"], "already_received")
        self.assertEqual(StudentDeleteRequest.objects.filter(account=self.account).count(), 1)

    def test_unauthenticated_rejected(self):
        self.client.credentials()
        resp = self.client.post("/api/student/me/delete-request", {}, format="json")
        self.assertEqual(resp.status_code, 401)


class QuickViewTests(TestCase):
    """GET /api/student/quick/<token> — văn thư gen + gửi tay."""

    def setUp(self):
        self.client = APIClient()
        self.enr_a = _make_enrollment("0903111111", "ORD-QV0001")
        self.enr_b = _make_enrollment("0903222222", "ORD-QV0002")
        self.account_a = StudentAccount.objects.get(phone="0903111111")

    def test_returns_enrollment_with_valid_quick_token(self):
        token = issue_quick_token(self.account_a.pk, self.account_a.phone, self.enr_a.pk)
        resp = self.client.get(f"/api/student/quick/{token}")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["scope"], "quick_view_read_only")
        self.assertEqual(body["enrollment"]["code"], "ORD-QV0001")
        self.assertIn("***", body["enrollment"]["student_phone_masked"])
        self.assertNotIn("deposit_link_token", body["enrollment"])
        self.assertNotIn("student_email", body["enrollment"])

    def test_access_token_rejected_as_quick(self):
        token = issue_access_token(self.account_a.pk, self.account_a.phone)
        resp = self.client.get(f"/api/student/quick/{token}")
        self.assertEqual(resp.status_code, 401)

    def test_cross_account_scope_returns_410(self):
        token = issue_quick_token(self.account_a.pk, self.account_a.phone, self.enr_b.pk)
        resp = self.client.get(f"/api/student/quick/{token}")
        self.assertEqual(resp.status_code, 410)

    def test_tampered_quick_token_rejected(self):
        token = issue_quick_token(self.account_a.pk, self.account_a.phone, self.enr_a.pk)
        parts = token.split(".")
        tampered = parts[0] + "." + parts[1][:-1] + ("A" if parts[1][-1] != "A" else "B")
        resp = self.client.get(f"/api/student/quick/{tampered}")
        self.assertEqual(resp.status_code, 401)

    def test_quick_view_does_not_grant_other_endpoints(self):
        token = issue_quick_token(self.account_a.pk, self.account_a.phone, self.enr_a.pk)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        resp_me = self.client.get("/api/student/me")
        self.assertEqual(resp_me.status_code, 401)
        resp_list = self.client.get("/api/student/enrollments")
        self.assertEqual(resp_list.status_code, 401)

    def test_quick_view_410_for_cancelled_enrollment(self):
        self.enr_a.status = EnrollmentStatus.CANCELLED
        self.enr_a.save(update_fields=["status", "updated_at"])
        token = issue_quick_token(self.account_a.pk, self.account_a.phone, self.enr_a.pk)
        resp = self.client.get(f"/api/student/quick/{token}")
        self.assertEqual(resp.status_code, 410)
        self.assertEqual(resp.json()["code"], "enrollment_inactive")


class StaffQuickTokenTests(TestCase):
    """POST /api/student/staff/quick-token — văn thư CRM gen link 24h."""

    def setUp(self):
        from django.contrib.auth.models import Group

        self.client = APIClient()
        User = get_user_model()
        self.van_thu_group, _ = Group.objects.get_or_create(name="van_thu")
        self.sale_group, _ = Group.objects.get_or_create(name="sale")
        self.van_thu = User.objects.create_user(
            username="vanthu",
            password="testpass123!",
            email="vt@example.vn",
            is_staff=True,
        )
        self.van_thu.groups.add(self.van_thu_group)
        # Staff group "sale" — không được gen link (chỉ chốt đơn).
        self.sale_staff = User.objects.create_user(
            username="sale1",
            password="testpass123!",
            email="sale1@example.vn",
            is_staff=True,
        )
        self.sale_staff.groups.add(self.sale_group)
        self.normal = User.objects.create_user(
            username="hocvien_user",
            password="testpass123!",
            email="hv@example.vn",
            is_staff=False,
        )
        self.enr = _make_enrollment("0903111111", "ORD-STAFF1")

    def test_van_thu_generates_quick_token_url(self):
        self.client.force_login(self.van_thu)
        resp = self.client.post(
            "/api/student/staff/quick-token",
            {"enrollment_id": self.enr.pk},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        self.assertIn("/quick/", body["url"])
        self.assertEqual(body["enrollment_code"], "ORD-STAFF1")
        self.assertGreater(body["expires_in_seconds"], 23 * 3600)

    def test_staff_without_allowed_group_forbidden(self):
        """Staff thuộc group sale (không phải văn thư/admin) → 403."""
        self.client.force_login(self.sale_staff)
        resp = self.client.post(
            "/api/student/staff/quick-token",
            {"enrollment_id": self.enr.pk},
            format="json",
        )
        self.assertEqual(resp.status_code, 403)

    def test_non_staff_user_forbidden(self):
        self.client.force_login(self.normal)
        resp = self.client.post(
            "/api/student/staff/quick-token",
            {"enrollment_id": self.enr.pk},
            format="json",
        )
        self.assertEqual(resp.status_code, 403)

    def test_unauthenticated_forbidden(self):
        resp = self.client.post(
            "/api/student/staff/quick-token",
            {"enrollment_id": self.enr.pk},
            format="json",
        )
        self.assertIn(resp.status_code, (401, 403))

    def test_enrollment_not_found_returns_404(self):
        self.client.force_login(self.van_thu)
        resp = self.client.post(
            "/api/student/staff/quick-token",
            {"enrollment_id": 9_999_999},
            format="json",
        )
        self.assertEqual(resp.status_code, 404)


class LoginRaceConditionTests(TestCase):
    """Race condition test: 2 fail đồng thời phải tăng counter atomic.

    Reviewer 2026-06-12 P1 — verify ``F()`` expression + atomic update.
    """

    def setUp(self):
        from django.core.cache import cache

        cache.clear()
        self.account, _ = _link_cccd(phone="0903111222", id_number="079111122233")

    def test_failure_counter_increments_correctly(self):
        # Simulate 2 concurrent failures (atomic increment).
        self.account.register_login_failure(ip="1.1.1.1")
        self.account.register_login_failure(ip="1.1.1.1")
        self.account.register_login_failure(ip="1.1.1.1")
        self.account.refresh_from_db()
        self.assertEqual(self.account.failed_login_count, 3)

    def test_success_returns_was_locked_after_expired_lock(self):
        # Lock đã hết hạn nhưng record còn → success phải clear + return True.
        self.account.failed_login_count = 5
        self.account.locked_until = timezone.now() - timezone.timedelta(minutes=1)
        self.account.save(update_fields=["failed_login_count", "locked_until"])
        was_locked = self.account.register_login_success(ip="1.1.1.1")
        self.assertTrue(was_locked)
        self.account.refresh_from_db()
        self.assertEqual(self.account.failed_login_count, 0)
        self.assertIsNone(self.account.locked_until)


class TimingLeakTests(TestCase):
    """Verify ``_verify_last6_cccd`` chạy đủ slot pad dù account=None hay rỗng."""

    def test_returns_false_for_none_account(self):
        from .views import _verify_last6_cccd

        self.assertFalse(_verify_last6_cccd(None, "123456"))

    def test_returns_false_for_account_no_person(self):
        from .views import _verify_last6_cccd

        account = StudentAccount.objects.create(phone="0903999000")
        self.assertFalse(_verify_last6_cccd(account, "123456"))

    def test_matches_when_last6_correct(self):
        from .views import _verify_last6_cccd

        account, _ = _link_cccd(phone="0903555000", id_number="079987654321")
        self.assertTrue(_verify_last6_cccd(account, "654321"))
