"""Tests cho management command fix_orphan_accounts (AE6 ops tool).

Cover:
- Account không có link → dry-run liệt kê, --delete xóa.
- Account có link → KHÔNG bị liệt kê là mồ côi.
- --delete --noinput skip confirm.
"""
from __future__ import annotations

from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from apps.students.models import (
    AccountPersonLink,
    Person,
    StudentAccount,
)


class FixOrphanAccountsCommandTests(TestCase):
    def setUp(self):
        # Account 1: có link (KHÔNG mồ côi).
        self.account_with_link = StudentAccount.objects.create(
            phone="0901234567", display_name="HV Linked"
        )
        person = Person.objects.create(full_name="HV Linked")
        AccountPersonLink.objects.create(
            account=self.account_with_link,
            person=person,
            is_primary=True,
        )
        # Account 2 + 3: mồ côi.
        self.orphan_1 = StudentAccount.objects.create(
            phone="0902222222", display_name="Mồ côi 1"
        )
        self.orphan_2 = StudentAccount.objects.create(
            phone="0903333333", display_name=""
        )

    def test_dry_run_lists_orphans_only(self):
        out = StringIO()
        call_command("fix_orphan_accounts", stdout=out)
        output = out.getvalue()
        # 2 orphans liệt kê.
        self.assertIn("Tìm thấy 2 Account mồ côi", output)
        self.assertIn("090****222", output)
        self.assertIn("090****333", output)
        # Account có link KHÔNG xuất hiện.
        self.assertNotIn("090****567", output)
        # Dry-run hint hiện.
        self.assertIn("Dry-run", output)
        # KHÔNG xóa gì.
        self.assertEqual(StudentAccount.objects.count(), 3)

    def test_no_orphans_returns_success_message(self):
        # Link cả 2 orphan để không còn mồ côi.
        person_2 = Person.objects.create(full_name="HV 2")
        AccountPersonLink.objects.create(
            account=self.orphan_1, person=person_2, is_primary=True
        )
        person_3 = Person.objects.create(full_name="HV 3")
        AccountPersonLink.objects.create(
            account=self.orphan_2, person=person_3, is_primary=True
        )

        out = StringIO()
        call_command("fix_orphan_accounts", stdout=out)
        self.assertIn("Không có Account mồ côi", out.getvalue())

    def test_delete_noinput_removes_orphans(self):
        out = StringIO()
        call_command(
            "fix_orphan_accounts", delete=True, noinput=True, stdout=out
        )
        # 2 orphan đã xóa.
        self.assertFalse(
            StudentAccount.objects.filter(phone="0902222222").exists()
        )
        self.assertFalse(
            StudentAccount.objects.filter(phone="0903333333").exists()
        )
        # Account có link giữ nguyên.
        self.assertTrue(
            StudentAccount.objects.filter(phone="0901234567").exists()
        )
        self.assertIn("Đã xóa", out.getvalue())
