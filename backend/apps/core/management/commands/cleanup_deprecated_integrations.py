"""Xóa orphan ``IntegrationCredential`` cho provider đã loại khỏi MVP.

Sau Sprint 3 Tuần 7 gói B (2026-06-12) — chốt bỏ ZNS Zalo + SMTP. Migration
0007 đã alter choices, command này dọn dữ liệu thật trong DB + audit log.

Chạy:

    python manage.py cleanup_deprecated_integrations
    python manage.py cleanup_deprecated_integrations --dry-run

Idempotent: gọi lại sau khi đã xóa → 0 record, không lỗi.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.core.models import AuditLog, IntegrationCredential


DEPRECATED_PROVIDERS = ("zns", "smtp")


class Command(BaseCommand):
    help = "Xóa IntegrationCredential cho provider đã loại (ZNS/SMTP)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Chỉ liệt kê record sẽ xóa, không thực thi.",
        )

    def handle(self, *args, **options):
        dry_run: bool = options["dry_run"]

        qs = IntegrationCredential.objects.filter(provider__in=DEPRECATED_PROVIDERS)
        total = qs.count()

        if total == 0:
            self.stdout.write(self.style.SUCCESS(
                "Không có IntegrationCredential nào thuộc provider đã loại."
            ))
            return

        for cred in qs.iterator():
            label = f"{cred.provider}.{cred.key} (id={cred.pk})"
            if dry_run:
                self.stdout.write(f"  [dry-run] sẽ xóa: {label}")
                continue

            AuditLog.objects.create(
                user=None,
                action=AuditLog.Action.DELETE,
                target_model="core.IntegrationCredential",
                target_id=str(cred.pk),
                changes={
                    "provider": cred.provider,
                    "key": cred.key,
                    "reason": "deprecated_provider_cleanup_sprint3_tuan7",
                },
                ip_address=None,
                user_agent="management_command:cleanup_deprecated_integrations",
            )
            cred.delete()
            self.stdout.write(self.style.WARNING(f"  Đã xóa: {label}"))

        if dry_run:
            self.stdout.write(self.style.NOTICE(
                f"\nDry-run: tổng {total} record sẽ xóa (chưa thực thi)."
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"\nHoàn tất: đã xóa {total} record + ghi audit log."
            ))
