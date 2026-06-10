"""Test webhook Casso + HMAC verify + idempotent.

Tiêu chí 2: Casso webhook với HMAC sai → 401. HMAC đúng → Payment tạo + Enrollment.paid_amount cộng.
"""
import hashlib
import hmac
import json
from decimal import Decimal

from django.contrib.auth.models import Group
from django.test import TestCase, override_settings

from apps.core.models import SiteSettings
from apps.courses.models import Course, VehicleClass, VehicleGroup
from apps.leads.models import Lead
from apps.orders.models import EnrollmentStatus
from apps.orders.services import convert_lead_to_enrollment
from apps.users.models import User

from .models import CassoTransaction, Payment, PaymentStatus
from .vietqr import build_deposit_qr_for_enrollment, build_vietqr_url
from .webhooks import verify_casso_signature


SECRET = "casso-test-secret-2026"


def _sign(body: bytes, secret: str = SECRET) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


@override_settings(CASSO_WEBHOOK_SECRET=SECRET)
class CassoWebhookTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.sale_group, _ = Group.objects.get_or_create(name="sale")
        cls.sale_user = User.objects.create_user(
            username="sale_cs", password="x", full_name="Sale Casso"
        )
        cls.sale_user.groups.add(cls.sale_group)

        cls.course = Course.objects.create(
            slug="test-casso",
            title="Test Casso",
            vehicle_class=VehicleClass.B_MT,
            vehicle_group=VehicleGroup.CAR,
            tuition_fee=Decimal("10000000"),
            deposit_amount=Decimal("1000000"),
            total_slots=10,
            available_slots=10,
        )

        lead = Lead.objects.create(name="HV Test", phone="0903333333")
        result = convert_lead_to_enrollment(
            lead_id=lead.id,
            course_id=cls.course.id,
            user=cls.sale_user,
        )
        cls.enrollment = result.enrollment

    # --- HMAC verify ---

    def test_webhook_without_signature_returns_401(self):
        body = json.dumps({"error": 0, "data": []}).encode()
        resp = self.client.post("/webhook/casso", data=body, content_type="application/json")
        self.assertEqual(resp.status_code, 401)

    def test_webhook_with_wrong_signature_returns_401(self):
        body = json.dumps(
            {"error": 0, "data": [{"tid": "T1", "amount": 1000000, "description": f"{self.enrollment.code} NCK"}]}
        ).encode()
        resp = self.client.post(
            "/webhook/casso",
            data=body,
            content_type="application/json",
            HTTP_SECURE_TOKEN="deadbeef" * 8,
        )
        self.assertEqual(resp.status_code, 401)
        # KHÔNG tạo CassoTransaction khi sai signature
        self.assertEqual(CassoTransaction.objects.count(), 0)
        self.assertEqual(Payment.objects.count(), 0)

    def test_verify_casso_signature_helper(self):
        body = b'{"x": 1}'
        sig = _sign(body)
        self.assertTrue(verify_casso_signature(body, sig, SECRET))
        self.assertFalse(verify_casso_signature(body, sig, "wrong-secret"))
        self.assertFalse(verify_casso_signature(body, "", SECRET))
        self.assertFalse(verify_casso_signature(body, sig, ""))

    @override_settings(CASSO_WEBHOOK_SECRET="")
    def test_webhook_without_secret_configured_returns_503(self):
        body = json.dumps({"error": 0, "data": []}).encode()
        resp = self.client.post(
            "/webhook/casso", data=body, content_type="application/json", HTTP_SECURE_TOKEN="x"
        )
        self.assertEqual(resp.status_code, 503)

    # --- Match ORD-XXXXXX ---

    def test_webhook_valid_signature_matched_creates_payment_and_updates_enrollment(self):
        """Webhook đúng HMAC + match ORD-XXXXXX → Payment tạo + Enrollment.paid_amount += amount."""
        amount = 1000000  # đúng deposit
        body_dict = {
            "error": 0,
            "data": [
                {
                    "id": 99001,
                    "tid": "FT-TEST-001",
                    "description": f"NCK HV nop coc {self.enrollment.code} BIDV",
                    "amount": amount,
                    "when": "2026-06-10T14:25:00+0700",
                    "subAccId": "0123456789",
                    "bankBrandName": "BIDV",
                }
            ],
        }
        body = json.dumps(body_dict).encode()
        sig = _sign(body)
        resp = self.client.post(
            "/webhook/casso",
            data=body,
            content_type="application/json",
            HTTP_SECURE_TOKEN=sig,
        )
        self.assertEqual(resp.status_code, 200)
        results = resp.json()["results"]
        self.assertEqual(results[0]["status"], "matched")
        self.assertEqual(results[0]["code"], self.enrollment.code)

        # Payment tạo với amount = 1tr, method=casso, status=confirmed
        payment = Payment.objects.get(bank_tx_id="FT-TEST-001")
        self.assertEqual(payment.amount, Decimal("1000000"))
        self.assertEqual(payment.status, PaymentStatus.CONFIRMED)
        self.assertEqual(payment.reference_code, self.enrollment.code)
        self.assertIsNotNone(payment.casso_transaction)

        # Enrollment cộng paid_amount, status → deposited
        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.paid_amount, Decimal("1000000"))
        self.assertEqual(self.enrollment.status, EnrollmentStatus.DEPOSITED)
        self.assertIsNotNone(self.enrollment.deposit_paid_at)

    def test_webhook_idempotent_same_tid_does_not_double_pay(self):
        """Cùng tid gửi 2 lần → Payment chỉ tạo 1 lần."""
        body_dict = {
            "error": 0,
            "data": [
                {
                    "id": 99002,
                    "tid": "FT-DUP-002",
                    "description": f"{self.enrollment.code}",
                    "amount": 500000,
                }
            ],
        }
        body = json.dumps(body_dict).encode()
        sig = _sign(body)
        kwargs = {
            "data": body,
            "content_type": "application/json",
            "HTTP_SECURE_TOKEN": sig,
        }
        resp1 = self.client.post("/webhook/casso", **kwargs)
        resp2 = self.client.post("/webhook/casso", **kwargs)
        self.assertEqual(resp1.status_code, 200)
        self.assertEqual(resp2.status_code, 200)
        self.assertEqual(resp2.json()["results"][0]["status"], "skipped")
        self.assertEqual(Payment.objects.filter(bank_tx_id="FT-DUP-002").count(), 1)

        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.paid_amount, Decimal("500000"))

    def test_webhook_unmatched_creates_casso_tx_but_no_payment(self):
        """Description không có ORD-XXXXXX → lưu CassoTransaction, KHÔNG tạo Payment."""
        body_dict = {
            "error": 0,
            "data": [
                {
                    "id": 99003,
                    "tid": "FT-UNMATCHED-003",
                    "description": "Tien khac, khong co ma don",
                    "amount": 200000,
                }
            ],
        }
        body = json.dumps(body_dict).encode()
        sig = _sign(body)
        resp = self.client.post(
            "/webhook/casso", data=body, content_type="application/json", HTTP_SECURE_TOKEN=sig
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["results"][0]["status"], "unmatched")
        self.assertTrue(CassoTransaction.objects.filter(tid="FT-UNMATCHED-003").exists())
        self.assertFalse(Payment.objects.filter(bank_tx_id="FT-UNMATCHED-003").exists())

    def test_webhook_full_payment_completes_enrollment(self):
        """Webhook với amount = học phí → status = completed."""
        body_dict = {
            "error": 0,
            "data": [
                {
                    "id": 99004,
                    "tid": "FT-FULL-004",
                    "description": f"Nop full {self.enrollment.code}",
                    "amount": int(self.enrollment.tuition_fee),
                }
            ],
        }
        body = json.dumps(body_dict).encode()
        sig = _sign(body)
        resp = self.client.post(
            "/webhook/casso", data=body, content_type="application/json", HTTP_SECURE_TOKEN=sig
        )
        self.assertEqual(resp.status_code, 200)
        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.status, EnrollmentStatus.COMPLETED)
        self.assertIsNotNone(self.enrollment.completed_at)

    def test_webhook_ambiguous_multiple_codes_does_not_match(self):
        """Description chứa >1 mã ORD-XXXXXX → KHÔNG auto-match (chống nhầm đơn)."""
        # Tạo enrollment thứ 2 để giả lập 2 mã thật
        from apps.leads.models import Lead

        lead2 = Lead.objects.create(name="HV 2", phone="0905555555")
        result2 = convert_lead_to_enrollment(
            lead_id=lead2.id, course_id=self.course.id, user=self.sale_user
        )
        body_dict = {
            "error": 0,
            "data": [
                {
                    "id": 99006,
                    "tid": "FT-AMBI-006",
                    "description": (
                        f"chuyen tu {self.enrollment.code} sang {result2.enrollment.code}"
                    ),
                    "amount": 500000,
                }
            ],
        }
        body = json.dumps(body_dict).encode()
        sig = _sign(body)
        resp = self.client.post(
            "/webhook/casso",
            data=body,
            content_type="application/json",
            HTTP_SECURE_TOKEN=sig,
        )
        self.assertEqual(resp.status_code, 200)
        result = resp.json()["results"][0]
        self.assertEqual(result["status"], "unmatched")
        self.assertEqual(result["reason"], "multiple_order_codes")
        # CassoTransaction được lưu để kế toán xử lý tay, KHÔNG tạo Payment
        self.assertTrue(CassoTransaction.objects.filter(tid="FT-AMBI-006").exists())
        self.assertFalse(Payment.objects.filter(bank_tx_id="FT-AMBI-006").exists())

    def test_webhook_data_null_returns_200_empty(self):
        """data=null → 200 + processed=0 (không crash)."""
        body = json.dumps({"error": 0, "data": None}).encode()
        sig = _sign(body)
        resp = self.client.post(
            "/webhook/casso",
            data=body,
            content_type="application/json",
            HTTP_SECURE_TOKEN=sig,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["processed"], 0)

    def test_webhook_negative_amount_is_ignored_but_logged(self):
        """Tiền ra (refund) lưu CassoTransaction, KHÔNG tạo Payment."""
        body_dict = {
            "error": 0,
            "data": [
                {
                    "id": 99005,
                    "tid": "FT-NEG-005",
                    "description": f"Hoan tien {self.enrollment.code}",
                    "amount": -500000,
                }
            ],
        }
        body = json.dumps(body_dict).encode()
        sig = _sign(body)
        resp = self.client.post(
            "/webhook/casso", data=body, content_type="application/json", HTTP_SECURE_TOKEN=sig
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["results"][0]["status"], "ignored")
        self.assertTrue(CassoTransaction.objects.filter(tid="FT-NEG-005").exists())
        self.assertFalse(Payment.objects.filter(bank_tx_id="FT-NEG-005").exists())


class VietQRTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        site = SiteSettings.get_solo()
        site.bank_code = "BIDV"
        site.bank_account_number = "0123456789"
        site.bank_account_name = "TRUNG TAM DAO TAO LAI XE"
        site.save()

        cls.course = Course.objects.create(
            slug="test-qr",
            title="Test QR",
            vehicle_class=VehicleClass.B_MT,
            vehicle_group=VehicleGroup.CAR,
            tuition_fee=Decimal("10000000"),
            deposit_amount=Decimal("1000000"),
            total_slots=5,
            available_slots=5,
        )

    def test_build_vietqr_url_uses_site_settings(self):
        url = build_vietqr_url(amount=1000000, add_info="ORD-ABC123")
        self.assertIn("BIDV-0123456789", url)
        self.assertIn("amount=1000000", url)
        self.assertIn("addInfo=ORD-ABC123", url)
        self.assertIn("accountName=", url)

    def test_build_vietqr_url_raises_if_bank_not_configured(self):
        site = SiteSettings.get_solo()
        site.bank_code = ""
        site.bank_account_number = ""
        site.save()
        with self.assertRaises(ValueError):
            build_vietqr_url(amount=100000, add_info="ORD-XXX")

    def test_build_deposit_qr_for_enrollment_returns_full_block(self):
        user = User.objects.create_user(username="x", password="x")
        Group.objects.get_or_create(name="sale")[0].user_set.add(user)
        lead = Lead.objects.create(name="A", phone="0904444444")
        result = convert_lead_to_enrollment(
            lead_id=lead.id, course_id=self.course.id, user=user
        )
        data = build_deposit_qr_for_enrollment(result.enrollment)
        self.assertIn("qr_url", data)
        self.assertEqual(data["bank_code"], "BIDV")
        self.assertEqual(data["add_info"], result.enrollment.code)
        self.assertEqual(data["amount"], int(self.course.deposit_amount))
