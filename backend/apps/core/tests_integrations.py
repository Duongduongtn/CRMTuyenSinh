"""Tests cho IntegrationCredential + Fernet crypto + loader + API admin.

Cover:
- Crypto: encrypt/decrypt roundtrip, empty handling.
- Model: set_value lưu encrypted, get_value decrypt, masked an toàn.
- Loader: priority cache → DB → ENV → default, invalidate.
- API: GET 403 non-superuser, 200 superuser; PUT bulk update + audit log.
"""
from cryptography.fernet import Fernet
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from apps.core import crypto, integrations
from apps.core.models import AuditLog, IntegrationCredential

User = get_user_model()

# Sinh key thật để test (KHÔNG dùng dev-default vì _build_cipher reject).
TEST_FERNET_KEY = Fernet.generate_key().decode()


def _reset_crypto():
    """Reset singleton cipher + cache để mỗi test isolated."""
    crypto.reset_cipher_cache()
    cache.clear()


@override_settings(FERNET_SECRET=TEST_FERNET_KEY)
class CryptoTests(TestCase):
    def setUp(self):
        _reset_crypto()

    def test_encrypt_decrypt_roundtrip(self):
        plaintext = "casso-secret-abc-123-xyz"
        ciphertext = crypto.encrypt_str(plaintext)
        self.assertNotEqual(ciphertext, plaintext.encode())
        self.assertEqual(crypto.decrypt_to_str(ciphertext), plaintext)

    def test_encrypt_empty_returns_empty_bytes(self):
        self.assertEqual(crypto.encrypt_str(""), b"")
        self.assertEqual(crypto.decrypt_to_str(b""), "")

    def test_decrypt_invalid_token_returns_empty(self):
        # Token sai → InvalidToken → trả "" thay vì raise (caller fallback ENV).
        self.assertEqual(crypto.decrypt_to_str(b"not-a-valid-fernet-token"), "")

    def test_unicode_diacritic_roundtrip(self):
        plaintext = "Mã bí mật tiếng Việt có dấu đầy đủ"
        ciphertext = crypto.encrypt_str(plaintext)
        self.assertEqual(crypto.decrypt_to_str(ciphertext), plaintext)


@override_settings(FERNET_SECRET=TEST_FERNET_KEY)
class IntegrationCredentialModelTests(TestCase):
    def setUp(self):
        _reset_crypto()

    def test_set_get_value_roundtrip(self):
        cred = IntegrationCredential.objects.create(
            provider="casso", key="webhook_secret"
        )
        cred.set_value("super-secret-token-123")
        cred.save()

        # Reload từ DB.
        fresh = IntegrationCredential.objects.get(pk=cred.pk)
        self.assertEqual(fresh.get_value(), "super-secret-token-123")

    def test_masked_hides_value(self):
        cred = IntegrationCredential(provider="casso", key="api_key")
        cred.set_value("ABCDEFGHIJ1234")
        cred.save()
        # 4 ký tự cuối hiện rõ, phần trước mask.
        self.assertEqual(cred.masked, "****1234")

    def test_masked_short_value(self):
        cred = IntegrationCredential(provider="casso", key="api_key")
        cred.set_value("xy")
        cred.save()
        self.assertEqual(cred.masked, "****")

    def test_masked_empty(self):
        cred = IntegrationCredential.objects.create(provider="zns", key="access_token")
        self.assertEqual(cred.masked, "")

    def test_unique_constraint_provider_key(self):
        IntegrationCredential.objects.create(provider="fb", key="app_secret")
        from django.db import IntegrityError

        with self.assertRaises(IntegrityError):
            IntegrationCredential.objects.create(provider="fb", key="app_secret")


@override_settings(
    FERNET_SECRET=TEST_FERNET_KEY,
    CASSO_WEBHOOK_SECRET="env-casso-fallback",
    ZNS_ACCESS_TOKEN="env-zns-fallback",
)
class IntegrationLoaderTests(TestCase):
    def setUp(self):
        _reset_crypto()

    def test_fallback_env_when_db_empty(self):
        self.assertEqual(
            integrations.get_credential("casso", "webhook_secret"),
            "env-casso-fallback",
        )

    def test_db_overrides_env(self):
        cred = IntegrationCredential(provider="casso", key="webhook_secret")
        cred.set_value("db-casso-value")
        cred.save()

        # Invalidate cache để buộc đọc DB.
        integrations.invalidate("casso", "webhook_secret")
        self.assertEqual(
            integrations.get_credential("casso", "webhook_secret"),
            "db-casso-value",
        )

    def test_env_fallback_is_not_cached(self):
        """ENV fallback đọc trực tiếp settings mỗi lần — `@override_settings`
        trong test (và rotate ENV runtime) phản ánh ngay, không bị stale cache.
        """
        # Lần đầu đọc → ENV value, KHÔNG cache.
        self.assertEqual(
            integrations.get_credential("zns", "access_token"),
            "env-zns-fallback",
        )

        # Override settings tạm thời → giá trị mới ngay lập tức.
        with self.settings(ZNS_ACCESS_TOKEN="env-changed-mid-test"):
            self.assertEqual(
                integrations.get_credential("zns", "access_token"),
                "env-changed-mid-test",
            )

        # Khôi phục override → giá trị gốc.
        self.assertEqual(
            integrations.get_credential("zns", "access_token"),
            "env-zns-fallback",
        )

    def test_db_value_is_cached_and_invalidate_works(self):
        """Khi có DB value, kết quả được cache TTL 60s. invalidate() force re-read."""
        cred = IntegrationCredential(provider="zns", key="access_token")
        cred.set_value("db-value-v1")
        cred.save()

        # Lần đầu: cache miss → đọc DB → cache "db-value-v1".
        self.assertEqual(
            integrations.get_credential("zns", "access_token"),
            "db-value-v1",
        )

        # Đổi DB sau đó. Cache vẫn giữ v1.
        cred.set_value("db-value-v2")
        cred.save()
        self.assertEqual(
            integrations.get_credential("zns", "access_token"),
            "db-value-v1",
        )

        # Invalidate → re-read DB → v2.
        integrations.invalidate("zns", "access_token")
        self.assertEqual(
            integrations.get_credential("zns", "access_token"),
            "db-value-v2",
        )

    def test_default_when_unknown_provider(self):
        # Provider không trong schema → trả default (silent fallback prod, raise dev).
        with self.settings(DEBUG=False):
            self.assertEqual(
                integrations.get_credential("unknown", "key", default="fallback"),
                "fallback",
            )

    def test_raise_unknown_provider_dev(self):
        with self.settings(DEBUG=True):
            with self.assertRaises(ValueError):
                integrations.get_credential("nope", "k")


@override_settings(FERNET_SECRET=TEST_FERNET_KEY)
class IntegrationAdminAPITests(TestCase):
    def setUp(self):
        _reset_crypto()
        self.client = APIClient()
        self.superuser = User.objects.create_user(
            username="admin_test",
            password="x" * 16,
            is_staff=True,
            is_superuser=True,
        )
        self.normal_user = User.objects.create_user(
            username="staff_test",
            password="x" * 16,
            is_staff=True,
        )

    def test_list_requires_superuser(self):
        # Chưa login → 401/403.
        resp = self.client.get(reverse("integration-list"))
        self.assertIn(resp.status_code, (401, 403))

        # Login staff thường (không superuser) → 403.
        self.client.force_authenticate(self.normal_user)
        resp = self.client.get(reverse("integration-list"))
        self.assertEqual(resp.status_code, 403)

    def test_list_returns_4_providers_with_schema_items(self):
        self.client.force_authenticate(self.superuser)
        resp = self.client.get(reverse("integration-list"))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        # 4 nhóm: casso, zns, fb, smtp.
        self.assertEqual(set(data.keys()), {"casso", "zns", "fb", "smtp"})

        # Casso có 2 key: webhook_secret + api_key.
        casso_keys = {item["key"] for item in data["casso"]}
        self.assertEqual(casso_keys, {"webhook_secret", "api_key"})

        # Mỗi item phải có label + sensitive + has_value + source.
        for item in data["casso"]:
            self.assertIn("label", item)
            self.assertIn("sensitive", item)
            self.assertIn("has_value", item)
            self.assertIn("source", item)
            # Empty default → source="empty", has_value=False.
            self.assertEqual(item["source"], "empty")
            self.assertFalse(item["has_value"])

    def test_put_updates_credential_and_audit_log(self):
        self.client.force_authenticate(self.superuser)
        url = reverse("integration-provider-update", kwargs={"provider": "casso"})
        resp = self.client.put(
            url,
            data={"webhook_secret": "new-secret-value", "api_key": "key-xyz-1234"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        self.assertEqual(set(body["keys_changed"]), {"webhook_secret", "api_key"})

        # DB lưu encrypted, masked đúng.
        cred = IntegrationCredential.objects.get(
            provider="casso", key="webhook_secret"
        )
        self.assertEqual(cred.get_value(), "new-secret-value")
        self.assertEqual(cred.updated_by, self.superuser)

        # Audit log 1 entry.
        log = AuditLog.objects.filter(
            action=AuditLog.Action.UPDATE,
            target_model="IntegrationCredential",
            target_id="casso",
        ).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.user, self.superuser)
        self.assertIn("webhook_secret", log.changes["keys_changed"])
        # KHÔNG được log plaintext.
        self.assertNotIn("new-secret-value", str(log.changes))

    def test_put_empty_value_clears_credential(self):
        # Seed 1 credential, sau đó PUT empty → cleared.
        cred = IntegrationCredential(provider="zns", key="access_token")
        cred.set_value("existing-token")
        cred.save()

        self.client.force_authenticate(self.superuser)
        url = reverse("integration-provider-update", kwargs={"provider": "zns"})
        resp = self.client.put(url, data={"access_token": ""}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("access_token", resp.json()["keys_cleared"])

        fresh = IntegrationCredential.objects.get(pk=cred.pk)
        self.assertEqual(fresh.get_value(), "")

    def test_put_idempotent_no_change_no_audit(self):
        """PUT cùng value 2 lần — lần 2 không tạo audit log."""
        self.client.force_authenticate(self.superuser)
        url = reverse("integration-provider-update", kwargs={"provider": "fb"})

        self.client.put(url, data={"app_secret": "same-value"}, format="json")
        audit_count_after_first = AuditLog.objects.filter(
            target_model="IntegrationCredential", target_id="fb"
        ).count()

        self.client.put(url, data={"app_secret": "same-value"}, format="json")
        audit_count_after_second = AuditLog.objects.filter(
            target_model="IntegrationCredential", target_id="fb"
        ).count()

        # Lần 2 không thêm audit (vì value không đổi).
        self.assertEqual(audit_count_after_first, audit_count_after_second)

    def test_put_invalid_provider_404(self):
        self.client.force_authenticate(self.superuser)
        url = "/api/admin/integrations/unknown/"
        resp = self.client.put(url, data={"x": "y"}, format="json")
        self.assertEqual(resp.status_code, 404)

    def test_put_requires_superuser(self):
        self.client.force_authenticate(self.normal_user)
        url = reverse("integration-provider-update", kwargs={"provider": "casso"})
        resp = self.client.put(url, data={"webhook_secret": "x"}, format="json")
        self.assertEqual(resp.status_code, 403)

    def test_list_after_update_shows_source_db(self):
        """Sau khi PUT giá trị, item liên quan source phải đổi sang 'db'."""
        self.client.force_authenticate(self.superuser)

        self.client.put(
            reverse("integration-provider-update", kwargs={"provider": "casso"}),
            data={"webhook_secret": "new-val-12345"},
            format="json",
        )
        resp = self.client.get(reverse("integration-list"))
        casso_items = {item["key"]: item for item in resp.json()["casso"]}
        self.assertEqual(casso_items["webhook_secret"]["source"], "db")
        self.assertTrue(casso_items["webhook_secret"]["has_value"])
        # Masked phải có dạng ****xxxx.
        self.assertTrue(casso_items["webhook_secret"]["masked"].startswith("****"))
