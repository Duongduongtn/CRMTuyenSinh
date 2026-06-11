"""Migration tạo IntegrationCredential cho UI quản lý 4 nhóm key prod.

Thay flow SSH `nano .env.prod` bằng form CRM SPA. Sprint 3 Tuần 7.
"""
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0004_alter_auditlog_action"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="IntegrationCredential",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "provider",
                    models.CharField(
                        choices=[
                            ("casso", "Casso (đối soát QR)"),
                            ("zns", "Zalo ZNS (OTP học viên)"),
                            ("fb", "Facebook Lead Ads"),
                            ("smtp", "Email SMTP"),
                        ],
                        max_length=20,
                        verbose_name="Tích hợp",
                    ),
                ),
                (
                    "key",
                    models.CharField(
                        help_text="Tên khóa: webhook_secret, api_key, access_token, ...",
                        max_length=80,
                        verbose_name="Khóa",
                    ),
                ),
                (
                    "value_encrypted",
                    models.BinaryField(
                        blank=True,
                        default=b"",
                        help_text="KHÔNG đọc trực tiếp — dùng .get_value().",
                        verbose_name="Giá trị (mã hóa Fernet)",
                    ),
                ),
                (
                    "description",
                    models.CharField(blank=True, max_length=255, verbose_name="Ghi chú"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="Cập nhật lúc"),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Cập nhật bởi",
                    ),
                ),
            ],
            options={
                "verbose_name": "Khóa tích hợp",
                "verbose_name_plural": "Khóa tích hợp",
                "ordering": ["provider", "key"],
            },
        ),
        migrations.AddConstraint(
            model_name="integrationcredential",
            constraint=models.UniqueConstraint(
                fields=("provider", "key"),
                name="integration_credential_provider_key_unique",
            ),
        ),
    ]
