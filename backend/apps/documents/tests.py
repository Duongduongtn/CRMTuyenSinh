"""Test upload magic-bytes + IDOR Person/Enrollment document."""
from decimal import Decimal
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image
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


def _valid_png(width=4, height=4) -> bytes:
    buf = BytesIO()
    Image.new("RGB", (width, height), (200, 200, 200)).save(buf, format="PNG")
    return buf.getvalue()


def _valid_jpeg(width=4, height=4) -> bytes:
    buf = BytesIO()
    Image.new("RGB", (width, height), (180, 180, 180)).save(buf, format="JPEG", quality=80)
    return buf.getvalue()


PNG_HEAD = _valid_png()
JPEG_HEAD = _valid_jpeg()
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

    def test_upload_valid_png_reencoded_to_jpeg(self):
        # Ảnh PNG được re-encode thành JPEG để strip EXIF/polyglot payload.
        resp = self._upload(PNG_HEAD, "cccd.png", "image/png")
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(PersonDocument.objects.filter(person=self.person).count(), 1)
        doc = PersonDocument.objects.first()
        self.assertEqual(doc.mime_type, "image/jpeg")
        self.assertTrue(doc.file.name.endswith(".jpg"))

    def test_upload_valid_jpeg(self):
        resp = self._upload(JPEG_HEAD, "cccd.jpg", "image/jpeg")
        self.assertEqual(resp.status_code, 201)
        doc = PersonDocument.objects.first()
        # Path UUID, không chứa tên gốc
        self.assertNotIn("cccd", doc.file.name)
        self.assertIn("private_documents/", doc.file.name)

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


class FileServeIDORTests(TestCase):
    """Serve byte stream qua endpoint /api/student/documents/<kind>/<id>/file.

    KHÔNG bao giờ trả file qua URL /media/ trực tiếp.
    """

    def setUp(self):
        self.client = APIClient()
        _make_enrollment("0903111111", "ORD-FS001")
        _make_enrollment("0903222222", "ORD-FS002")
        self.account_a = StudentAccount.objects.get(phone="0903111111")
        self.account_b = StudentAccount.objects.get(phone="0903222222")
        self.person_a = Person.objects.create(full_name="HV A", id_number="A012345678901")
        AccountPersonLink.objects.create(account=self.account_a, person=self.person_a, is_primary=True)
        self.doc_type = DocumentType.objects.create(
            code="cccd_front", name="CCCD mặt trước", scope="person", is_required=True
        )
        # Upload 1 doc cho person_a
        token = issue_access_token(self.account_a.pk, self.account_a.phone)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        f = SimpleUploadedFile("cccd.jpg", JPEG_HEAD, content_type="image/jpeg")
        resp = self.client.post(
            f"/api/student/persons/{self.person_a.pk}/documents",
            {"document_type_id": self.doc_type.pk, "file": f},
            format="multipart",
        )
        self.assertEqual(resp.status_code, 201)
        self.doc_id = resp.json()["id"]

    def test_owner_can_download_with_force_attachment_headers(self):
        resp = self.client.get(f"/api/student/documents/person/{self.doc_id}/file")
        self.assertEqual(resp.status_code, 200)
        # Force download — chống XSS qua inline render
        self.assertIn("attachment", resp["Content-Disposition"])
        self.assertEqual(resp["X-Content-Type-Options"], "nosniff")
        self.assertIn("private", resp["Cache-Control"])

    def test_other_account_cannot_download_via_serve_view(self):
        token = issue_access_token(self.account_b.pk, self.account_b.phone)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        resp = self.client.get(f"/api/student/documents/person/{self.doc_id}/file")
        self.assertEqual(resp.status_code, 404)

    def test_unauthenticated_cannot_download(self):
        self.client.credentials()  # clear auth
        resp = self.client.get(f"/api/student/documents/person/{self.doc_id}/file")
        self.assertEqual(resp.status_code, 401)


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
