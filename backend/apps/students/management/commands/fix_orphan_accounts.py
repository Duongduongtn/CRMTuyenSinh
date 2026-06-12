"""Management command tìm StudentAccount mồ côi (không có AccountPersonLink nào).

AE6: ops tool dọn dẹp Account orphan có thể phát sinh khi:
- Auto-provision tạo Account get_or_create thành công nhưng raise sau đó (AE4
  DatabaseError nhánh log ERROR) → Account tồn tại nhưng Person + Link không tạo.
- Admin xóa Person/Link tay qua Django admin mà quên xóa Account.
- Migration cũ có bug để partial state.

Run:
    python manage.py fix_orphan_accounts            # dry-run, in list + count
    python manage.py fix_orphan_accounts --delete   # xóa thật, có confirm

Z defer (`fix_orphan_accounts` command) đã đóng.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db.models import Count

from apps.students.models import StudentAccount


class Command(BaseCommand):
    help = (
        "Tìm StudentAccount mồ côi (không có AccountPersonLink). "
        "Mặc định dry-run; --delete để xóa thật."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--delete",
            action="store_true",
            help="Xóa Account mồ côi (có confirm interactive trừ khi --noinput).",
        )
        parser.add_argument(
            "--noinput",
            action="store_true",
            help="Skip confirm prompt (dùng cho automation/CI). KHÔNG dùng tay.",
        )

    def handle(self, *, delete: bool, noinput: bool, **opts):
        orphans = (
            StudentAccount.objects
            .annotate(link_count=Count("person_links"))
            .filter(link_count=0)
            .order_by("created_at")
        )
        count = orphans.count()

        if count == 0:
            self.stdout.write(self.style.SUCCESS("Không có Account mồ côi."))
            return

        self.stdout.write(
            self.style.WARNING(f"Tìm thấy {count} Account mồ côi:")
        )
        for acc in orphans[:50]:  # cap display 50 để không spam terminal.
            self.stdout.write(
                f"  - id={acc.pk} phone={_mask_phone(acc.phone)} "
                f"display_name={acc.display_name!r} created={acc.created_at:%d/%m/%Y %H:%M}"
            )
        if count > 50:
            self.stdout.write(f"  ... và {count - 50} Account khác.")

        if not delete:
            self.stdout.write(
                self.style.NOTICE(
                    "\nDry-run: không xóa gì. Chạy lại với --delete để xóa thật."
                )
            )
            return

        if not noinput:
            answer = input(
                f"\nXác nhận XÓA {count} Account mồ côi? (yes/no): "
            ).strip().lower()
            if answer != "yes":
                self.stdout.write(self.style.ERROR("Đã hủy."))
                return

        deleted, _per_model = orphans.delete()
        self.stdout.write(
            self.style.SUCCESS(f"Đã xóa {deleted} bản ghi (gồm Account + cascade).")
        )


def _mask_phone(phone: str) -> str:
    """Hiển thị SĐT giấu giữa, giữ 3 đầu + 3 cuối."""
    if not phone or len(phone) < 7:
        return "***"
    return phone[:3] + "****" + phone[-3:]
