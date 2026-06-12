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

    # ----- Forensic audit: SUSPICIOUS_FIELD khi attacker PATCH key cấm -----

    def test_patch_with_only_rejected_fields_logs_suspicious_and_returns_400(self):
        """Payload toàn key cấm (is_superuser, created_at) → 400 + 1 AuditLog
        SUSPICIOUS_FIELD ghi tên key (KHÔNG ghi value để tránh leak attack vector)."""
        self.client.force_authenticate(self.superuser)
        resp = self.client.patch(
            reverse("admin-site-settings"),
            data={"is_superuser": True, "created_at": "2030-01-01T00:00:00Z"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

        log = AuditLog.objects.filter(
            action=AuditLog.Action.SUSPICIOUS_FIELD,
            target_model="SiteSettings",
        ).first()
        self.assertIsNotNone(
            log, "Phải có 1 AuditLog SUSPICIOUS_FIELD khi attacker PATCH key cấm."
        )
        self.assertEqual(log.user, self.superuser)
        self.assertEqual(
            sorted(log.changes["rejected_fields"]),
            ["created_at", "is_superuser"],
        )
        self.assertEqual(log.changes["rejected_count"], 2)
        # target_id rỗng: SUSPICIOUS không gắn instance vì attacker chưa chạm row.
        self.assertEqual(log.target_id, "")
        # KHÔNG có giá trị raw trong log (tránh leak attack vector).
        self.assertNotIn("True", str(log.changes))
        self.assertNotIn("2030", str(log.changes))

        # KHÔNG có AuditLog UPDATE vì payload sau filter rỗng.
        self.assertEqual(
            AuditLog.objects.filter(
                action=AuditLog.Action.UPDATE, target_model="SiteSettings"
            ).count(),
            0,
        )

    def test_patch_with_mixed_valid_and_rejected_logs_suspicious_and_updates(self):
        """Payload mix valid (brand_name) + rejected (is_superuser) → 200 +
        brand_name update + 2 AuditLog (SUSPICIOUS_FIELD + UPDATE)."""
        self.client.force_authenticate(self.superuser)
        resp = self.client.patch(
            reverse("admin-site-settings"),
            data={
                "brand_name": "Trung tâm hợp lệ",
                "is_superuser": True,
                "id": 999,
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 200)

        # brand_name update.
        site = SiteSettings.get_solo()
        self.assertEqual(site.brand_name, "Trung tâm hợp lệ")
        # Superuser flag KHÔNG bị đụng (whitelist defense).
        self.assertTrue(self.superuser.is_superuser)

        # AuditLog SUSPICIOUS_FIELD: 1 entry với rejected_fields = sorted.
        susp_log = AuditLog.objects.filter(
            action=AuditLog.Action.SUSPICIOUS_FIELD,
            target_model="SiteSettings",
        ).first()
        self.assertIsNotNone(susp_log)
        self.assertEqual(
            susp_log.changes["rejected_fields"], ["id", "is_superuser"]
        )

        # AuditLog UPDATE: 1 entry với brand_name.
        upd_log = AuditLog.objects.filter(
            action=AuditLog.Action.UPDATE,
            target_model="SiteSettings",
        ).first()
        self.assertIsNotNone(upd_log)
        self.assertEqual(upd_log.changes["fields_changed"], ["brand_name"])

    def test_patch_with_only_editable_fields_no_suspicious_log(self):
        """Payload sạch (chỉ key trong whitelist) → KHÔNG có SUSPICIOUS_FIELD log,
        chỉ có UPDATE log thường."""
        self.client.force_authenticate(self.superuser)
        self.client.patch(
            reverse("admin-site-settings"),
            data={"brand_name": "Tên mới"},
            format="json",
        )
        self.assertEqual(
            AuditLog.objects.filter(
                action=AuditLog.Action.SUSPICIOUS_FIELD,
                target_model="SiteSettings",
            ).count(),
            0,
        )
        self.assertEqual(
            AuditLog.objects.filter(
                action=AuditLog.Action.UPDATE,
                target_model="SiteSettings",
            ).count(),
            1,
        )

    def test_patch_with_list_payload_returns_400_without_suspicious_log(self):
        """request.data là list (vd `[{"is_superuser": true}]`) → guard isinstance
        đẩy về dict rỗng → KHÔNG có SUSPICIOUS log + 400 + không crash 500."""
        self.client.force_authenticate(self.superuser)
        resp = self.client.patch(
            reverse("admin-site-settings"),
            data=[{"is_superuser": True}],
            format="json",
        )
        # Bị filter ra dict rỗng → raise ValueError → 400, KHÔNG 500.
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(
            AuditLog.objects.filter(
                action=AuditLog.Action.SUSPICIOUS_FIELD,
                target_model="SiteSettings",
            ).count(),
            0,
            "List payload → guard fall-back dict rỗng → rejected_fields rỗng.",
        )

    def test_patch_rejected_fields_capped_at_max_logged(self):
        """Payload chứa > MAX_REJECTED_FIELDS_LOGGED (20) key cấm → log chứa
        tối đa 20 key + marker __truncated__ + rejected_count thật (forensic).
        Chống DoS bloat AuditLog JSONB."""
        self.client.force_authenticate(self.superuser)
        # Gửi 100 key lạ (kxx_001 → kxx_100) → 100 rejected.
        bad_keys = {f"kxx_{i:03d}": i for i in range(100)}
        resp = self.client.patch(
            reverse("admin-site-settings"),
            data=bad_keys,
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

        log = AuditLog.objects.filter(
            action=AuditLog.Action.SUSPICIOUS_FIELD,
            target_model="SiteSettings",
        ).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.changes["rejected_count"], 100)
        # 20 key + 1 marker = 21 phần tử.
        self.assertEqual(len(log.changes["rejected_fields"]), 21)
        self.assertEqual(log.changes["rejected_fields"][-1], "__truncated__")
        # 20 key đầu (sorted) phải bắt đầu từ kxx_000.
        self.assertEqual(log.changes["rejected_fields"][0], "kxx_000")
        self.assertEqual(log.changes["rejected_fields"][19], "kxx_019")

    def test_patch_rejected_key_length_truncated(self):
        """Key dài > MAX_REJECTED_KEY_LENGTH (64) chars → log chỉ giữ 64 ký tự
        đầu. Chống PG TOAST bloat khi attacker gửi key 50k chars."""
        self.client.force_authenticate(self.superuser)
        long_key = "X" * 1000
        resp = self.client.patch(
            reverse("admin-site-settings"),
            data={long_key: 1},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

        log = AuditLog.objects.filter(
            action=AuditLog.Action.SUSPICIOUS_FIELD,
            target_model="SiteSettings",
        ).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.changes["rejected_count"], 1)
        self.assertEqual(len(log.changes["rejected_fields"]), 1)
        # Key truncate đúng 64 chars.
        self.assertEqual(log.changes["rejected_fields"][0], "X" * 64)
        # Original 1000-char key không lưu raw.
        self.assertNotIn("X" * 100, str(log.changes))

    def test_suspicious_field_log_persists_when_validation_fails_after(self):
        """SUSPICIOUS_FIELD emit NGOÀI transaction.atomic → kể cả khi validation
        sau đó fail (vd email sai), suspicious log vẫn lưu để forensic."""
        self.client.force_authenticate(self.superuser)
        resp = self.client.patch(
            reverse("admin-site-settings"),
            data={
                "email": "không-phải-email",
                "is_superuser": True,
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

        susp_log = AuditLog.objects.filter(
            action=AuditLog.Action.SUSPICIOUS_FIELD,
            target_model="SiteSettings",
        ).first()
        self.assertIsNotNone(
            susp_log,
            "SUSPICIOUS log phải persist kể cả khi validation field hợp lệ fail.",
        )
        self.assertEqual(susp_log.changes["rejected_fields"], ["is_superuser"])

    # ----- AE5: mask bank_account_name (vishing defense SEC P2) -----

    def test_patch_audit_bank_account_name_only_masked(self):
        """AE5 SEC P2: tên chủ TK mask first+last letter mỗi từ, plaintext
        KHÔNG xuất hiện trong AuditLog (chống vishing giả mạo giám đốc)."""
        self.client.force_authenticate(self.superuser)
        self.client.patch(
            reverse("admin-site-settings"),
            data={"bank_account_name": "NGUYEN VAN ANH"},
            format="json",
        )

        log = AuditLog.objects.filter(target_model="SiteSettings").first()
        self.assertIsNotNone(log)
        # Mask: N****N V*N A*H (first+last letter, * giữa, "ANH" 3 chars → 1 *).
        self.assertEqual(
            log.changes["new"]["bank_account_name"], "N****N V*N A*H"
        )
        self.assertNotIn("NGUYEN VAN ANH", str(log.changes))

    def test_patch_audit_bank_account_name_short_word_passthrough(self):
        """Từ <= 2 ký tự không mask (vd "TM" giữ nguyên) — không có gì để mask."""
        self.client.force_authenticate(self.superuser)
        self.client.patch(
            reverse("admin-site-settings"),
            data={"bank_account_name": "TM XYZ"},
            format="json",
        )
        log = AuditLog.objects.filter(target_model="SiteSettings").first()
        self.assertEqual(log.changes["new"]["bank_account_name"], "TM X*Z")

    # ----- AE5: CaptureQueriesContext PG-only verify SQL FOR UPDATE -----

    def test_patch_emits_select_for_update_sql_on_postgres(self):
        """AE5 BE MINOR-2: thay test mock Manager.select_for_update bằng
        CaptureQueriesContext robust hơn (không phụ thuộc Django internals).
        Chỉ chạy trên PG vì SQLite KHÔNG render FOR UPDATE."""
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        if connection.vendor != "postgresql":
            self.skipTest("select_for_update SQL chỉ render trên PostgreSQL")

        self.client.force_authenticate(self.superuser)
        with CaptureQueriesContext(connection) as ctx:
            resp = self.client.patch(
                reverse("admin-site-settings"),
                data={"brand_name": "Y"},
                format="json",
            )
        self.assertEqual(resp.status_code, 200)
        sfu_queries = [
            q for q in ctx.captured_queries
            if "FOR UPDATE" in q["sql"].upper()
        ]
        self.assertGreater(
            len(sfu_queries),
            0,
            "PATCH phải render ít nhất 1 SELECT ... FOR UPDATE để lock row.",
        )

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
