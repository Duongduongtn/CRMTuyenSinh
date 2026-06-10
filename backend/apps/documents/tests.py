"""Test upload magic-bytes + IDOR Person/Enrollment document."""
from decimal import Decimal
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.courses.models import Course, VehicleClass, VehicleGroup
from apps.orders.models import Enrollment, EnrollmentStatus
from apps.students.auth import issue_access_token
from apps.students.models import (
    AccountPersonLink,
    Person,
    StudentAccount,
)

from .models import DocumentType, PersonDocument


# Magic bytes
PNG_HEAD = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
JPEG_HEAD = b"\xff\xd8\xff" + b"\x00" * 100
PDF_HEAD = b"%PDF-1.4\n" + b"\x00" * 100
EXE_HEAD = b"MZ\x90\x00" + b"\x00" * 100  # PE/Windows EXE


def _make_course():
    return Course.objects.create(
        slug="b-mt",
        title="B số sàn",
        vehicle_class=VehicleClass.B_MT,
        vehicle_group=VehicleGroup.CAR,
        tuition_fee=Decimal("17500000"),
        deposit_amount=Decimal("500000"),
    )


def _make_enrollment(phone: str, code: str):
    return Enrollment.objects.create(
        code=code,
        course=_make_course() if not Course.objects.exists() else Course.objects.first(),
        student_name="HV Test",
        student_phone=phone,
        vehicle_class=VehicleClass.B_MT,
        tuition_fee=Decimal("17500000"),
        deposit_amount=Decimal("500000"),
        status=EnrollmentStatus.PENDING,
    )


@override_settings(MEDIA_ROOT="/tmp/crm_test_media")
class UploadMagicBytesTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.enr = _make_enrollment("0903111111", "ORD-DOC001")
        self.account = StudentAccount.objects.get(phone="0903111111")
        self.person = Person.objects.create(full_name="HV Test", id_number="012345678901")
        AccountPersonLink.objects.create(
            account=self.account, person=self.person, is_primary=True
        )
        self.doc_type = DocumentType.objects.create(
            code="cccd_front", name="CCCD mặt trước", scope="person", is_required=True
        )
        token = issue_access_token(self.account.pk, self.account.phone)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def _upload(self, content: bytes, name: str, content_type: str):
        f = SimpleUploadedFile(name, content, content_type=content_type)
        return self.client.post(
            f"/api/student/persons/{self.person.pk}/documents",
            {"document_type_id": self.doc_type.pk, "file": f},
            format="multipart",
        )

    def test_upload_valid_png(self):
        resp = self._upload(PNG_HEAD, "cccd.png", "image/png")
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(PersonDocument.objects.filter(person=self.person).count(), 1)
        doc = PersonDocument.objects.first()
        self.assertEqual(doc.mime_type, "image/png")

    def test_upload_valid_jpeg(self):
        resp = self._upload(JPEG_HEAD, "cccd.jpg", "image/jpeg")
        self.assertEqual(resp.status_code, 201)

    def test_upload_valid_pdf(self):
        resp = self._upload(PDF_HEAD, "cccd.pdf", "application/pdf")
        self.assertEqual(resp.status_code, 201)

    def test_reject_exe_disguised_as_png(self):
        # File .png nhưng nội dung là EXE — magic bytes check phải chặn
        resp = self._upload(EXE_HEAD, "cccd.png", "image/png")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(PersonDocument.objects.count(), 0)

    def test_reject_oversize_file(self):
        big = JPEG_HEAD + b"\x00" * (6 * 1024 * 1024)
        resp = self._upload(big, "big.jpg", "image/jpeg")
        self.assertEqual(resp.status_code, 400)

    def test_reject_empty_file(self):
        resp = self._upload(b"", "empty.jpg", "image/jpeg")
        self.assertEqual(resp.status_code, 400)


class PersonDocumentIDORTests(TestCase):
    """HV A KHÔNG được upload vào Person của HV B."""

    def setUp(self):
        self.client = APIClient()
        _make_enrollment("0903111111", "ORD-IDOR01")
        _make_enrollment("0903222222", "ORD-IDOR02")
        self.account_a = StudentAccount.objects.get(phone="0903111111")
        self.account_b = StudentAccount.objects.get(phone="0903222222")
        self.person_b = Person.objects.create(full_name="HV B", id_number="012345678902")
        AccountPersonLink.objects.create(
            account=self.account_b, person=self.person_b, is_primary=True
        )
        self.doc_type = DocumentType.objects.create(
            code="cccd_front", name="CCCD mặt trước", scope="person", is_required=True
        )

    def test_student_a_cannot_upload_to_person_b(self):
        token = issue_access_token(self.account_a.pk, self.account_a.phone)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        f = SimpleUploadedFile("malicious.png", PNG_HEAD, content_type="image/png")
        resp = self.client.post(
            f"/api/student/persons/{self.person_b.pk}/documents",
            {"document_type_id": self.doc_type.pk, "file": f},
            format="multipart",
        )
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(PersonDocument.objects.filter(person=self.person_b).count(), 0)

    def test_student_a_cannot_list_person_b_docs(self):
        token = issue_access_token(self.account_a.pk, self.account_a.phone)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        resp = self.client.get(f"/api/student/persons/{self.person_b.pk}/documents")
        self.assertEqual(resp.status_code, 404)
