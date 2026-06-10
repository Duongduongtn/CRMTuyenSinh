"""Test FB Lead Ads webhook + service.

Acceptance Sprint 3:
- GET verify token đúng → trả challenge.
- GET verify token sai → 403.
- POST signature sai (khi FB_APP_SECRET set) → 403.
- POST payload hợp lệ → tạo Lead + FBLeadAdsEvent.
- POST lặp lại cùng leadgen_id → không tạo Lead trùng (idempotent).
- POST thiếu SĐT → event.status = failed, KHÔNG tạo Lead.
"""
from __future__ import annotations

import hashlib
import hmac
import json

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.leads.models import Lead

from .models import FBLeadAdsEvent
from .services import process_fb_leadgen


def _sample_payload(leadgen_id: str = "leadgen_1", phone: str = "0903123456") -> dict:
    return {
        "leadgen_id": leadgen_id,
        "page_id": "page_123",
        "form_id": "form_abc",
        "ad_id": "ad_999",
        "campaign_id": "camp_777",
        "field_data": [
            {"name": "full_name", "values": ["Nguyễn Văn A"]},
            {"name": "phone_number", "values": [phone]},
            {"name": "email", "values": ["a@example.vn"]},
            {"name": "city", "values": ["Bình Phước"]},
            {"name": "message", "values": ["Quan tâm B số tự động"]},
        ],
    }


@override_settings(FB_LEAD_VERIFY_TOKEN="verify_secret_123", FB_APP_SECRET="")
class FBVerifyTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_verify_with_correct_token_returns_challenge(self):
        resp = self.client.get(
            "/webhook/fb-leadgen",
            {
                "hub.mode": "subscribe",
                "hub.verify_token": "verify_secret_123",
                "hub.challenge": "1234567",
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content.decode(), "1234567")

    def test_verify_with_wrong_token_returns_403(self):
        resp = self.client.get(
            "/webhook/fb-leadgen",
            {
                "hub.mode": "subscribe",
                "hub.verify_token": "sai_token",
                "hub.challenge": "1234567",
            },
        )
        self.assertEqual(resp.status_code, 403)

    @override_settings(FB_LEAD_VERIFY_TOKEN="")
    def test_verify_token_unconfigured_returns_403(self):
        resp = self.client.get(
            "/webhook/fb-leadgen",
            {"hub.mode": "subscribe", "hub.verify_token": "anything", "hub.challenge": "x"},
        )
        self.assertEqual(resp.status_code, 403)


@override_settings(
    FB_LEAD_VERIFY_TOKEN="verify_x",
    FB_APP_SECRET="",
    FB_ALLOW_INSECURE_DEV=True,
)
class FBPostNoSignatureDevTests(TestCase):
    """Ở dev (FB_ALLOW_INSECURE_DEV=True) + FB_APP_SECRET rỗng → skip verify."""

    def setUp(self):
        self.client = APIClient()

    def test_post_creates_lead_and_event(self):
        body = {
            "object": "page",
            "entry": [
                {
                    "changes": [
                        {"field": "leadgen", "value": _sample_payload()},
                    ],
                },
            ],
        }
        resp = self.client.post(
            "/webhook/fb-leadgen",
            data=json.dumps(body),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["processed"], 1)

        lead = Lead.objects.get()
        self.assertEqual(lead.phone, "0903123456")
        self.assertEqual(lead.source, "fb_ads")
        self.assertEqual(lead.utm_source, "facebook")

        event = FBLeadAdsEvent.objects.get()
        self.assertEqual(event.status, FBLeadAdsEvent.Status.PROCESSED)
        self.assertEqual(event.matched_lead_id, lead.id)


@override_settings(
    FB_LEAD_VERIFY_TOKEN="verify_x",
    FB_APP_SECRET="app_secret_xyz",
    DEBUG=False,
)
class FBPostSignatureTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def _sign(self, body: bytes) -> str:
        return "sha256=" + hmac.new(
            b"app_secret_xyz", body, hashlib.sha256
        ).hexdigest()

    def test_post_without_signature_returns_403(self):
        body = json.dumps({"object": "page", "entry": []}).encode()
        resp = self.client.post(
            "/webhook/fb-leadgen", data=body, content_type="application/json"
        )
        self.assertEqual(resp.status_code, 403)

    def test_post_with_invalid_signature_returns_403(self):
        body = json.dumps({"object": "page", "entry": []}).encode()
        resp = self.client.post(
            "/webhook/fb-leadgen",
            data=body,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256="sha256=" + "0" * 64,
        )
        self.assertEqual(resp.status_code, 403)

    def test_post_with_correct_signature_creates_lead(self):
        body = json.dumps({
            "object": "page",
            "entry": [
                {"changes": [{"field": "leadgen", "value": _sample_payload("leadgen_signed")}]},
            ],
        }).encode()
        resp = self.client.post(
            "/webhook/fb-leadgen",
            data=body,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256=self._sign(body),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(FBLeadAdsEvent.objects.filter(leadgen_id="leadgen_signed").exists())


class FBProcessServiceTests(TestCase):
    """Unit test cho service xử lý lead — không qua webhook."""

    def test_idempotent_same_leadgen_id(self):
        process_fb_leadgen(_sample_payload("dup_1"))
        process_fb_leadgen(_sample_payload("dup_1"))
        # Chỉ 1 event + 1 Lead
        self.assertEqual(FBLeadAdsEvent.objects.filter(leadgen_id="dup_1").count(), 1)
        self.assertEqual(Lead.objects.filter(phone="0903123456").count(), 1)

    def test_missing_phone_marks_failed_without_creating_lead(self):
        payload = _sample_payload("no_phone")
        payload["field_data"] = [
            {"name": "full_name", "values": ["X"]},
        ]
        event = process_fb_leadgen(payload)
        self.assertEqual(event.status, FBLeadAdsEvent.Status.FAILED)
        self.assertEqual(Lead.objects.count(), 0)

    def test_phone_normalization(self):
        payload = _sample_payload("norm_1", phone="+84 903 444 555")
        event = process_fb_leadgen(payload)
        self.assertEqual(event.status, FBLeadAdsEvent.Status.PROCESSED)
        self.assertEqual(event.matched_lead.phone, "0903444555")

    def test_duplicate_phone_within_7_days_marks_duplicate(self):
        process_fb_leadgen(_sample_payload("first"))
        event2 = process_fb_leadgen(_sample_payload("second"))
        self.assertEqual(event2.status, FBLeadAdsEvent.Status.DUPLICATE)
        # Vẫn chỉ 1 Lead trong CRM (không tạo trùng)
        self.assertEqual(Lead.objects.filter(phone="0903123456").count(), 1)
