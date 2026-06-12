"""Tests cho admin SiteSettings API: GET full + PATCH partial + audit log.

Cover:
- Permission: 401/403 cho non-superuser, 200 cho superuser.
- GET: trả full field text + URL ảnh empty khi chưa upload.
- PATCH: update field bank/brand/social, audit log liệt kê field đã đổi.
- PATCH idempotent: cùng value 2 lần → audit log không nhân đôi.
- PATCH bỏ qua key lạ + image fields (không cho upload qua endpoint này).
- PATCH validation: email sai → 400.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.core.models import AuditLog, SiteSettings

User = get_user_model()


class SiteSettingsAdminAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.superuser = User.objects.create_user(
            username="admin_settings",
            password="x" * 16,
            is_staff=True,
            is_superuser=True,
        )
        self.staff_user = User.objects.create_user(
            username="staff_settings",
            password="x" * 16,
            is_staff=True,
        )

    def test_get_requires_superuser(self):
        url = reverse("admin-site-settings")

        # Chưa login → 401/403.
        resp = self.client.get(url)
        self.assertIn(resp.status_code, (401, 403))

        # Staff thường (không superuser) → 403.
        self.client.force_authenticate(self.staff_user)
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 403)

    def test_get_returns_full_settings_for_superuser(self):
        self.client.force_authenticate(self.superuser)
        resp = self.client.get(reverse("admin-site-settings"))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        # Field text/number editable phải có trong response.
        for key in (
            "brand_name",
            "hotline",
            "bank_code",
            "bank_account_number",
            "bank_account_name",
            "facebook_url",
            "meta_title_default",
            "stat_students_count",
        ):
            self.assertIn(key, data, f"Field {key} thiếu trong GET response")

        # Image fields trả URL (empty string khi chưa upload).
        self.assertIn("logo_url", data)
        self.assertEqual(data["logo_url"], "")

    def test_patch_updates_bank_info_and_audit_log(self):
        self.client.force_authenticate(self.superuser)
        url = reverse("admin-site-settings")

        # SiteSettings mặc định bank_code="BIDV" — đổi sang VCB để có diff đủ 3 field.
        resp = self.client.patch(
            url,
            data={
                "bank_code": "VCB",
                "bank_account_number": "12345678901234",
                "bank_account_name": "TRUNG TAM DAO TAO LAI XE THANH DAT",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)

        # DB đã cập nhật.
        site = SiteSettings.get_solo()
        self.assertEqual(site.bank_code, "VCB")
        self.assertEqual(site.bank_account_number, "12345678901234")
        self.assertEqual(
            site.bank_account_name, "TRUNG TAM DAO TAO LAI XE THANH DAT"
        )

        # Audit log 1 entry.
        log = AuditLog.objects.filter(
            action=AuditLog.Action.UPDATE,
            target_model="SiteSettings",
        ).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.user, self.superuser)
        self.assertIn("bank_code", log.changes["fields_changed"])
        self.assertIn("bank_account_number", log.changes["fields_changed"])
        self.assertIn("bank_account_name", log.changes["fields_changed"])

        # Số TK đầy đủ KHÔNG được log — chỉ mask 4 số cuối.
        self.assertNotIn("12345678901234", str(log.changes))
        self.assertEqual(
            log.changes["bank_account_number_new_masked"][-4:], "1234"
        )
        # STK cũ rỗng (default DB) → mask cũ rỗng.
        self.assertEqual(log.changes["bank_account_number_old_masked"], "")

    def test_patch_bank_account_audit_logs_old_and_new_masked(self):
        """Đổi STK 2 lần — lần 2 log phải có old_masked = mask STK lần 1."""
        # Seed STK lần đầu.
        site = SiteSettings.get_solo()
        site.bank_account_number = "11112222333344"
        site.save()

        self.client.force_authenticate(self.superuser)
        url = reverse("admin-site-settings")
        resp = self.client.patch(
            url,
            data={"bank_account_number": "99998888777766"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)

        log = AuditLog.objects.filter(target_model="SiteSettings").first()
        self.assertIsNotNone(log)
        self.assertEqual(log.changes["bank_account_number_old_masked"][-4:], "3344")
        self.assertEqual(log.changes["bank_account_number_new_masked"][-4:], "7766")
        # Plaintext cũ + mới không xuất hiện.
        self.assertNotIn("11112222333344", str(log.changes))
        self.assertNotIn("99998888777766", str(log.changes))

    def test_patch_map_embed_url_rejects_non_google(self):
        """URL map không phải Google → 400 (chống superuser bị compromise paste phishing URL)."""
        self.client.force_authenticate(self.superuser)
        url = reverse("admin-site-settings")
        resp = self.client.patch(
            url,
            data={"map_embed_url": "https://evil.com/fake-maps.html"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("map_embed_url", resp.json())

    def test_patch_map_embed_url_accepts_google(self):
        self.client.force_authenticate(self.superuser)
        url = reverse("admin-site-settings")
        resp = self.client.patch(
            url,
            data={
                "map_embed_url": "https://www.google.com/maps/embed?pb=!1m18!1m12"
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 200)

    def test_patch_map_embed_url_rejects_http_scheme(self):
        self.client.force_authenticate(self.superuser)
        url = reverse("admin-site-settings")
        resp = self.client.patch(
            url,
            data={"map_embed_url": "http://www.google.com/maps/embed?pb=..."},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_patch_map_embed_url_empty_ok(self):
        """Cho phép xóa URL map (set empty)."""
        self.client.force_authenticate(self.superuser)
        url = reverse("admin-site-settings")
        resp = self.client.patch(url, data={"map_embed_url": ""}, format="json")
        self.assertEqual(resp.status_code, 200)

    def test_patch_idempotent_no_change_no_audit(self):
        """PATCH cùng giá trị 2 lần — lần 2 không tạo audit log."""
        self.client.force_authenticate(self.superuser)
        url = reverse("admin-site-settings")
        payload = {"brand_name": "Trung tâm Lái xe Thành Đạt"}

        self.client.patch(url, data=payload, format="json")
        first_count = AuditLog.objects.filter(
            target_model="SiteSettings"
        ).count()

        self.client.patch(url, data=payload, format="json")
        second_count = AuditLog.objects.filter(
            target_model="SiteSettings"
        ).count()

        self.assertEqual(first_count, second_count)

    def test_patch_ignores_unknown_keys(self):
        """Body có key lạ + image key → bị bỏ qua, các key hợp lệ vẫn update."""
        self.client.force_authenticate(self.superuser)
        url = reverse("admin-site-settings")

        resp = self.client.patch(
            url,
            data={
                "brand_name": "Tên mới có dấu",
                "random_key": "ignored",
                "logo": "/path/should/be/ignored",  # image field không cho PATCH ở đây
                "is_superuser": True,  # cố attack escalation
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 200)

        site = SiteSettings.get_solo()
        self.assertEqual(site.brand_name, "Tên mới có dấu")

        # Superuser của REQUEST không được leak vào model.
        log = AuditLog.objects.filter(target_model="SiteSettings").first()
        self.assertIsNotNone(log)
        self.assertEqual(set(log.changes["fields_changed"]), {"brand_name"})

    def test_patch_empty_payload_returns_400(self):
        self.client.force_authenticate(self.superuser)
        url = reverse("admin-site-settings")
        resp = self.client.patch(url, data={"random_only": "x"}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_patch_invalid_email_returns_400(self):
        self.client.force_authenticate(self.superuser)
        url = reverse("admin-site-settings")
        resp = self.client.patch(
            url, data={"email": "không-phải-email"}, format="json"
        )
        self.assertEqual(resp.status_code, 400)

    def test_patch_requires_superuser(self):
        self.client.force_authenticate(self.staff_user)
        url = reverse("admin-site-settings")
        resp = self.client.patch(
            url, data={"brand_name": "x"}, format="json"
        )
        self.assertEqual(resp.status_code, 403)

    def test_patch_diacritics_preserved(self):
        """Đảm bảo dấu tiếng Việt round-trip qua API không bị mojibake."""
        self.client.force_authenticate(self.superuser)
        url = reverse("admin-site-settings")
        payload = {
            "brand_name": "Trung tâm Đào tạo Lái xe Bình Phước",
            "address_line": "Phường Tân Phú, Đồng Xoài, Bình Phước",
            "slogan": "Học lái xe an toàn — đúng lộ trình.",
        }
        resp = self.client.patch(url, data=payload, format="json")
        self.assertEqual(resp.status_code, 200)

        data = resp.json()
        self.assertEqual(data["brand_name"], payload["brand_name"])
        self.assertEqual(data["address_line"], payload["address_line"])
        self.assertEqual(data["slogan"], payload["slogan"])

    # ----- Audit log full old → new (NĐ 13/2023) -----

    def test_patch_audit_logs_old_and_new_for_non_sensitive_field(self):
        """Field non-sensitive (brand_name) phải log cả old + new raw value
        để truy vết được \"đổi từ X sang Y\", không chỉ tên field (NĐ 13/2023)."""
        # Seed brand_name cũ rõ ràng.
        site = SiteSettings.get_solo()
        site.brand_name = "Trung tâm cũ"
        site.save()

        self.client.force_authenticate(self.superuser)
        resp = self.client.patch(
            reverse("admin-site-settings"),
            data={"brand_name": "Trung tâm mới"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)

        log = AuditLog.objects.filter(target_model="SiteSettings").first()
        self.assertIsNotNone(log)
        self.assertEqual(log.changes["fields_changed"], ["brand_name"])
        self.assertEqual(log.changes["old"]["brand_name"], "Trung tâm cũ")
        self.assertEqual(log.changes["new"]["brand_name"], "Trung tâm mới")

    def test_patch_audit_sensitive_field_only_masked_in_old_new(self):
        """Field sensitive (bank_account_number) trong `old`/`new` chỉ chứa
        giá trị mask, KHÔNG plaintext kể cả ở key mới `old`/`new`."""
        site = SiteSettings.get_solo()
        site.bank_account_number = "11112222333344"
        site.save()

        self.client.force_authenticate(self.superuser)
        self.client.patch(
            reverse("admin-site-settings"),
            data={"bank_account_number": "99998888777766"},
            format="json",
        )

        log = AuditLog.objects.filter(target_model="SiteSettings").first()
        self.assertIsNotNone(log)
        # Old + new đều mask, không plaintext.
        self.assertEqual(log.changes["old"]["bank_account_number"][-4:], "3344")
        self.assertEqual(log.changes["new"]["bank_account_number"][-4:], "7766")
        self.assertNotIn("11112222333344", str(log.changes))
        self.assertNotIn("99998888777766", str(log.changes))

    def test_patch_audit_tax_code_only_masked(self):
        """Mã số thuế là dữ liệu định danh gián tiếp (NĐ 13/2023) — chỉ mask
        4 số cuối trong audit log, không leak plaintext."""
        site = SiteSettings.get_solo()
        site.tax_code = "0123456789"
        site.save()

        self.client.force_authenticate(self.superuser)
        self.client.patch(
            reverse("admin-site-settings"),
            data={"tax_code": "9876543210"},
            format="json",
        )

        log = AuditLog.objects.filter(target_model="SiteSettings").first()
        self.assertIsNotNone(log)
        self.assertEqual(log.changes["old"]["tax_code"][-4:], "6789")
        self.assertEqual(log.changes["new"]["tax_code"][-4:], "3210")
        self.assertNotIn("0123456789", str(log.changes))
        self.assertNotIn("9876543210", str(log.changes))

    def test_patch_audit_serializes_decimal_field(self):
        """DecimalField (map_lat) phải JSON-serialize được vào AuditLog.changes."""
        self.client.force_authenticate(self.superuser)
        resp = self.client.patch(
            reverse("admin-site-settings"),
            data={"map_lat": "10.7626001"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)

        log = AuditLog.objects.filter(target_model="SiteSettings").first()
        self.assertIsNotNone(log)
        # Old là None (mặc định), new là Decimal stringified.
        self.assertIsNone(log.changes["old"]["map_lat"])
        self.assertEqual(log.changes["new"]["map_lat"], "10.7626001")

    def test_patch_uses_select_for_update_inside_atomic(self):
        """select_for_update phải được gọi để lock row → chống last-write-wins.

        Postgres only (SQLite skip vì backend không support row-level lock).
        Test bằng spy queryset method để verify code path đi qua, không phụ
        thuộc backend DB.
        """
        from unittest.mock import patch as mock_patch

        # Spy select_for_update — wraps để vẫn chạy thực, chỉ verify được gọi.
        original_sfu = SiteSettings.objects.select_for_update

        with mock_patch.object(
            SiteSettings.objects.__class__,
            "select_for_update",
            autospec=True,
            side_effect=lambda self, *args, **kwargs: original_sfu(*args, **kwargs),
        ) as spy:
            self.client.force_authenticate(self.superuser)
            resp = self.client.patch(
                reverse("admin-site-settings"),
                data={"brand_name": "X"},
                format="json",
            )
            self.assertEqual(resp.status_code, 200)
            self.assertTrue(
                spy.called,
                "select_for_update phải được gọi trong patch để lock row.",
            )
