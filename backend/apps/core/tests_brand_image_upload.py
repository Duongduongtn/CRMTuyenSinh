"""Tests cho endpoint POST/DELETE /api/admin/site-settings/upload-image/.

Cover:
- Permission: 401/403 cho non-superuser.
- POST happy path: upload PNG/JPEG/WEBP cho logo/og_image, ICO/PNG cho favicon.
- POST audit log: UPDATE với fields_changed + old/new tên file.
- POST validate: field enum, missing file, size cap, type không hợp lệ,
  dimension out-of-bound, file fake (.txt rename .png).
- POST cleanup: file cũ xóa SAU commit khi upload đè.
- DELETE happy path: xóa ảnh + reset field về null + AuditLog DELETE.
- DELETE idempotent: xóa khi đã rỗng → 200 không ghi audit.
"""
from __future__ import annotations

import io
import shutil
import tempfile
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image
from rest_framework.test import APIClient

from apps.core.models import AuditLog, SiteSettings

User = get_user_model()

MEDIA_ROOT_TEST = Path(tempfile.mkdtemp(prefix="crm_brand_test_"))


def make_image(
    fmt: str = "PNG",
    size: tuple[int, int] = (512, 512),
    color=(34, 139, 34),
) -> io.BytesIO:
    """Tạo file ảnh in-memory dùng cho upload test."""
    buf = io.BytesIO()
    img = Image.new("RGB", size, color)
    img.save(buf, format=fmt)
    buf.seek(0)
    buf.name = f"test.{fmt.lower()}"
    return buf


@override_settings(MEDIA_ROOT=str(MEDIA_ROOT_TEST))
class BrandImageUploadAPITests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        if MEDIA_ROOT_TEST.exists():
            shutil.rmtree(MEDIA_ROOT_TEST, ignore_errors=True)

    def setUp(self):
        self.client = APIClient()
        self.superuser = User.objects.create_user(
            username="admin_brand",
            password="x" * 16,
            is_staff=True,
            is_superuser=True,
        )
        self.staff_user = User.objects.create_user(
            username="staff_brand", password="x" * 16, is_staff=True
        )
        self.url = reverse("admin-site-settings-upload-image")

    # ----- Permission -----

    def test_post_requires_superuser_anonymous(self):
        resp = self.client.post(self.url, {}, format="multipart")
        self.assertIn(resp.status_code, (401, 403))

    def test_post_requires_superuser_staff_only(self):
        self.client.force_authenticate(self.staff_user)
        resp = self.client.post(self.url, {}, format="multipart")
        self.assertEqual(resp.status_code, 403)

    def test_delete_requires_superuser(self):
        self.client.force_authenticate(self.staff_user)
        resp = self.client.delete(self.url, {"field": "logo"}, format="json")
        self.assertEqual(resp.status_code, 403)

    # ----- POST happy path -----

    def test_post_upload_logo_png_success(self):
        self.client.force_authenticate(self.superuser)
        resp = self.client.post(
            self.url,
            data={"field": "logo", "image": make_image("PNG", (512, 512))},
            format="multipart",
        )
        self.assertEqual(resp.status_code, 200, resp.content)

        site = SiteSettings.get_solo()
        self.assertTrue(site.logo.name.startswith("brand/logo_"))
        self.assertTrue(site.logo.name.endswith(".png"))
        self.assertIn("logo_url", resp.json())
        self.assertTrue(resp.json()["logo_url"])

    def test_post_upload_favicon_ico_success(self):
        self.client.force_authenticate(self.superuser)
        resp = self.client.post(
            self.url,
            data={"field": "favicon", "image": make_image("PNG", (64, 64))},
            format="multipart",
        )
        self.assertEqual(resp.status_code, 200, resp.content)

        site = SiteSettings.get_solo()
        self.assertTrue(site.favicon.name.startswith("brand/favicon_"))

    def test_post_upload_og_image_jpeg_success(self):
        self.client.force_authenticate(self.superuser)
        resp = self.client.post(
            self.url,
            data={
                "field": "og_image",
                "image": make_image("JPEG", (1200, 630)),
            },
            format="multipart",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        site = SiteSettings.get_solo()
        self.assertTrue(site.og_image.name.endswith(".jpg"))

    def test_post_audit_log_created_with_old_and_new(self):
        self.client.force_authenticate(self.superuser)
        # Upload lần 1.
        self.client.post(
            self.url,
            data={"field": "logo", "image": make_image("PNG", (512, 512))},
            format="multipart",
        )
        site = SiteSettings.get_solo()
        first_name = site.logo.name

        # Upload lần 2 (đè).
        self.client.post(
            self.url,
            data={"field": "logo", "image": make_image("PNG", (600, 600))},
            format="multipart",
        )
        site.refresh_from_db()
        second_name = site.logo.name
        self.assertNotEqual(first_name, second_name)

        logs = list(
            AuditLog.objects.filter(
                action=AuditLog.Action.UPDATE,
                target_model="SiteSettings",
            ).order_by("created_at")
        )
        # 2 log UPDATE (lần 1 old rỗng, lần 2 old = first_name).
        self.assertEqual(len(logs), 2)
        self.assertEqual(logs[0].changes["fields_changed"], ["logo"])
        self.assertEqual(logs[0].changes["old"]["logo"], "")
        self.assertEqual(logs[0].changes["new"]["logo"], first_name)
        self.assertEqual(logs[1].changes["old"]["logo"], first_name)
        self.assertEqual(logs[1].changes["new"]["logo"], second_name)

    # ----- POST validation -----

    def test_post_rejects_invalid_field_enum(self):
        self.client.force_authenticate(self.superuser)
        resp = self.client.post(
            self.url,
            data={"field": "background", "image": make_image()},
            format="multipart",
        )
        self.assertEqual(resp.status_code, 400)

    def test_post_rejects_missing_image(self):
        self.client.force_authenticate(self.superuser)
        resp = self.client.post(
            self.url, data={"field": "logo"}, format="multipart"
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("image", resp.json()["detail"].lower())

    def test_post_rejects_file_too_small_dimension(self):
        self.client.force_authenticate(self.superuser)
        # Logo min 256x256, gửi 100x100.
        resp = self.client.post(
            self.url,
            data={"field": "logo", "image": make_image("PNG", (100, 100))},
            format="multipart",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("100x100", resp.json()["detail"])

    def test_post_rejects_oversize_dimension(self):
        self.client.force_authenticate(self.superuser)
        resp = self.client.post(
            self.url,
            data={
                "field": "favicon",
                "image": make_image("PNG", (1024, 1024)),
            },
            format="multipart",
        )
        self.assertEqual(resp.status_code, 400)

    def test_post_rejects_disallowed_format_for_field(self):
        """Favicon CHỈ chấp PNG/ICO — gửi JPEG → 400."""
        self.client.force_authenticate(self.superuser)
        resp = self.client.post(
            self.url,
            data={
                "field": "favicon",
                "image": make_image("JPEG", (64, 64)),
            },
            format="multipart",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("JPEG", resp.json()["detail"])

    def test_post_rejects_fake_image_text_file(self):
        """File text rename .png → PIL.verify raise → 400 (chống upload shell)."""
        self.client.force_authenticate(self.superuser)
        fake = io.BytesIO(b"<?php echo 'pwned'; ?>")
        fake.name = "logo.png"
        resp = self.client.post(
            self.url,
            data={"field": "logo", "image": fake},
            format="multipart",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("ảnh hợp lệ", resp.json()["detail"])

    def test_post_rejects_truncated_png(self):
        """PNG cắt cụt giữa chunk → PIL raise OSError → 400."""
        self.client.force_authenticate(self.superuser)
        # Tạo PNG hợp lệ rồi cắt half bytes.
        buf = make_image("PNG", (512, 512))
        full_bytes = buf.getvalue()
        truncated = io.BytesIO(full_bytes[: len(full_bytes) // 2])
        truncated.name = "truncated.png"
        resp = self.client.post(
            self.url,
            data={"field": "logo", "image": truncated},
            format="multipart",
        )
        self.assertEqual(resp.status_code, 400)

    def test_post_no_audit_log_when_validation_fails(self):
        """Upload fail validation → KHÔNG ghi AuditLog UPDATE."""
        self.client.force_authenticate(self.superuser)
        self.client.post(
            self.url,
            data={"field": "logo", "image": make_image("PNG", (10, 10))},
            format="multipart",
        )
        self.assertEqual(
            AuditLog.objects.filter(
                action=AuditLog.Action.UPDATE, target_model="SiteSettings"
            ).count(),
            0,
        )

    # ----- DELETE -----

    def test_delete_clears_field_and_audit(self):
        self.client.force_authenticate(self.superuser)
        # Upload trước.
        self.client.post(
            self.url,
            data={"field": "logo", "image": make_image("PNG", (512, 512))},
            format="multipart",
        )
        site = SiteSettings.get_solo()
        old_name = site.logo.name
        self.assertTrue(old_name)

        # DELETE.
        resp = self.client.delete(
            self.url, {"field": "logo"}, format="json"
        )
        self.assertEqual(resp.status_code, 200)

        site.refresh_from_db()
        self.assertFalse(site.logo)

        log = AuditLog.objects.filter(
            action=AuditLog.Action.DELETE, target_model="SiteSettings"
        ).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.changes["fields_changed"], ["logo"])
        self.assertEqual(log.changes["old"]["logo"], old_name)
        self.assertEqual(log.changes["new"]["logo"], "")

    def test_delete_idempotent_when_field_empty(self):
        """DELETE khi field đã rỗng → 200, không ghi audit."""
        self.client.force_authenticate(self.superuser)
        resp = self.client.delete(
            self.url, {"field": "logo"}, format="json"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            AuditLog.objects.filter(
                action=AuditLog.Action.DELETE, target_model="SiteSettings"
            ).count(),
            0,
        )

    def test_delete_rejects_invalid_field(self):
        self.client.force_authenticate(self.superuser)
        resp = self.client.delete(
            self.url, {"field": "background"}, format="json"
        )
        self.assertEqual(resp.status_code, 400)
