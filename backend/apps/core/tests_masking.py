"""Test helper mask PII trong apps/core/masking.py."""
from __future__ import annotations

from django.test import SimpleTestCase

from apps.core.masking import (
    SENSITIVE_KEYS,
    mask_cccd,
    mask_phone,
    scrub_sentry_pii,
)


class MaskPhoneTests(SimpleTestCase):
    def test_phone_10_so_chuan(self):
        self.assertEqual(mask_phone("0903111222"), "090****222")

    def test_phone_quoc_te_11_so(self):
        self.assertEqual(mask_phone("84903111222"), "849****222")

    def test_phone_rong_tra_3_sao(self):
        self.assertEqual(mask_phone(""), "***")

    def test_phone_none_tra_3_sao(self):
        self.assertEqual(mask_phone(None), "***")

    def test_phone_qua_ngan_tra_3_sao(self):
        self.assertEqual(mask_phone("12345"), "***")


class MaskCccdTests(SimpleTestCase):
    def test_cccd_12_so(self):
        self.assertEqual(mask_cccd("036123456789"), "********6789")

    def test_cmnd_9_so(self):
        self.assertEqual(mask_cccd("123456789"), "*****6789")

    def test_cccd_rong(self):
        self.assertEqual(mask_cccd(""), "***")

    def test_cccd_none(self):
        self.assertEqual(mask_cccd(None), "***")

    def test_cccd_qua_ngan(self):
        self.assertEqual(mask_cccd("1234"), "***")


class ScrubSentryPiiTests(SimpleTestCase):
    """Verify Sentry before_send hook strip PII recursive."""

    def test_strip_phone_top_level(self):
        event = {"phone": "0903111222", "level": "error"}
        result = scrub_sentry_pii(event, {})
        self.assertEqual(result["phone"], "***")
        self.assertEqual(result["level"], "error")

    def test_strip_cccd_nested_request_data(self):
        event = {
            "request": {
                "data": {
                    "name": "Nguyễn Văn A",
                    "cccd": "036123456789",
                    "phone": "0903111222",
                }
            }
        }
        result = scrub_sentry_pii(event, {})
        self.assertEqual(result["request"]["data"]["cccd"], "***")
        self.assertEqual(result["request"]["data"]["phone"], "***")
        self.assertEqual(result["request"]["data"]["name"], "Nguyễn Văn A")  # name không nhạy cảm

    def test_strip_secret_token_api_key(self):
        event = {
            "extra": {
                "webhook_secret": "abc123",
                "api_key": "key-xxx",
                "django_secret_key": "very-secret",
                "fernet_secret": "fernet-key",
                "harmless_field": "ok",
            }
        }
        result = scrub_sentry_pii(event, {})
        self.assertEqual(result["extra"]["webhook_secret"], "***")
        self.assertEqual(result["extra"]["api_key"], "***")
        self.assertEqual(result["extra"]["django_secret_key"], "***")
        self.assertEqual(result["extra"]["fernet_secret"], "***")
        self.assertEqual(result["extra"]["harmless_field"], "ok")

    def test_strip_in_list_of_dicts(self):
        event = {
            "breadcrumbs": [
                {"data": {"phone": "0901", "ok": 1}},
                {"data": {"cccd_front": "url-binh-thuong", "ok": 2}},
            ]
        }
        result = scrub_sentry_pii(event, {})
        self.assertEqual(result["breadcrumbs"][0]["data"]["phone"], "***")
        self.assertEqual(result["breadcrumbs"][1]["data"]["cccd_front"], "***")
        self.assertEqual(result["breadcrumbs"][0]["data"]["ok"], 1)

    def test_case_insensitive_key_match(self):
        event = {"PHONE": "0903111222", "Cccd": "036123456789"}
        result = scrub_sentry_pii(event, {})
        self.assertEqual(result["PHONE"], "***")
        self.assertEqual(result["Cccd"], "***")

    def test_event_rong_tra_event(self):
        self.assertEqual(scrub_sentry_pii({}, {}), {})
        self.assertIsNone(scrub_sentry_pii(None, {}))

    def test_non_sensitive_field_giu_nguyen(self):
        event = {
            "message": "Có lỗi khi xử lý đơn",
            "level": "error",
            "user": {"id": 42, "username": "sale01"},
        }
        result = scrub_sentry_pii(event, {})
        self.assertEqual(result, event)

    def test_sensitive_keys_contain_all_pii_categories(self):
        # Sanity check: SENSITIVE_KEYS phải có 6 nhóm theo NĐ 13/2023 + secret.
        expected_phone_keys = {"phone", "student_phone"}
        expected_id_keys = {"cccd", "id_number"}
        expected_email_keys = {"email", "student_email"}
        expected_dob_keys = {"date_of_birth", "dob"}
        expected_address_keys = {"address", "permanent_address"}
        expected_secret_keys = {"webhook_secret", "api_key", "fernet_secret"}
        self.assertTrue(expected_phone_keys.issubset(SENSITIVE_KEYS))
        self.assertTrue(expected_id_keys.issubset(SENSITIVE_KEYS))
        self.assertTrue(expected_email_keys.issubset(SENSITIVE_KEYS))
        self.assertTrue(expected_dob_keys.issubset(SENSITIVE_KEYS))
        self.assertTrue(expected_address_keys.issubset(SENSITIVE_KEYS))
        self.assertTrue(expected_secret_keys.issubset(SENSITIVE_KEYS))

    def test_strip_email_dob_address_NĐ_13_2023(self):
        # Bổ sung AF3 sau security review M2/M3/M4.
        event = {
            "request": {
                "data": {
                    "student_email": "hocvien@example.com",
                    "lead_email": "lead@example.com",
                    "date_of_birth": "1990-01-15",
                    "permanent_address": "123 Đường ABC, Phường XYZ",
                    "address_line": "Số 5 Ngõ 10",
                    "full_name": "Nguyễn Văn A",  # KHÔNG strip (debug operational)
                }
            }
        }
        result = scrub_sentry_pii(event, {})
        data = result["request"]["data"]
        self.assertEqual(data["student_email"], "***")
        self.assertEqual(data["lead_email"], "***")
        self.assertEqual(data["date_of_birth"], "***")
        self.assertEqual(data["permanent_address"], "***")
        self.assertEqual(data["address_line"], "***")
        self.assertEqual(data["full_name"], "Nguyễn Văn A")  # giữ debug
