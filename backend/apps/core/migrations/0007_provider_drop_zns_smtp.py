"""Sprint 3 Tuần 7 (2026-06-12) — gói B.

Loại ``Provider.ZNS`` + ``Provider.SMTP`` khỏi choices của
``IntegrationCredential.provider``. Choices chỉ còn ``casso`` + ``fb``.

Khác với migration 0006 (gói A) chỉ alter Python-side choices nhưng GIỮ ZNS/SMTP
deprecated cho code cũ, migration này XÓA hẳn 2 lựa chọn vì:

- View OTP đã bị gỡ (commit gói B).
- ZNS adapter đã bị xóa.
- ``send_deposit_zns_link`` đã bị gỡ.
- SMTP backend mặc định DummyBackend ở prod, không bao giờ đọc credential SMTP.

Orphan record ``IntegrationCredential(provider="zns"/"smtp")`` không bị xóa
trong migration này — cần chạy management command
``cleanup_deprecated_integrations`` để xóa kèm AuditLog.

KHÔNG có DB-level DROP CONSTRAINT vì ``CharField.choices`` chỉ enforce ở Python.
Nếu record orphan còn → query ``Provider.ZNS`` sẽ Raise ValueError ở enum lookup,
nhưng record vẫn tồn tại với raw string "zns" trong DB tới khi xóa bằng mgmt cmd.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0006_alter_integrationcredential_provider"),
    ]

    operations = [
        migrations.AlterField(
            model_name="integrationcredential",
            name="provider",
            field=models.CharField(
                choices=[
                    ("casso", "Casso (đối soát QR)"),
                    ("fb", "Facebook Lead Ads"),
                ],
                max_length=20,
                verbose_name="Tích hợp",
            ),
        ),
    ]
