"""
App `documents` — hồ sơ học viên.

2 loại tài liệu (theo memory [[person-enrollment-model]]):
- ``PersonDocument``: CCCD 2 mặt, ảnh chân dung, giấy khám sức khỏe — gắn với
  Person (dùng chung cho nhiều Enrollment nếu HV đăng ký nhiều khóa).
- ``EnrollmentDocument``: sơ yếu lý lịch, đơn xin học, hợp đồng — gắn với
  Enrollment cụ thể.

Bảo mật:
- File lưu vào ``private_documents/`` (KHÔNG serve qua nginx tĩnh).
- Tên file UUID, KHÔNG dùng tên gốc của HV (chống path traversal + đoán URL).
- Truy cập file BẮT BUỘC qua endpoint ``/api/student/documents/<id>/file``
  có JWT auth + IDOR check + audit log (Sprint 3).

Auto-purge CCCD sau 90 ngày kể từ ngày hoàn thành khóa (NĐ 13/2023 về BVDLCN).
Xem [[apps.documents.tasks]].
"""
from __future__ import annotations

import io

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db import models
from django.utils.translation import gettext_lazy as _


MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5 MB

ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "application/pdf",
}

# Magic bytes (file signature) — chống upload .exe đổi đuôi .jpg.
# v1 thu hẹp về JPG/PNG/PDF: WebP có thể embed script container, loại bỏ
# để giảm bề mặt tấn công. Khi cần WebP, FE convert sang JPG trước upload.
MAGIC_BYTES = {
    "image/jpeg": [b"\xff\xd8\xff"],
    "image/png": [b"\x89PNG\r\n\x1a\n"],
    "application/pdf": [b"%PDF-"],
}


def validate_upload(file_obj, *, max_size: int = MAX_UPLOAD_SIZE) -> str:
    """Validate file upload: size + magic bytes + Pillow verify.

    Return MIME type detect được. Raise ``ValidationError`` nếu invalid.

    Ảnh JPG/PNG sẽ được re-encode qua Pillow để strip EXIF (lộ GPS) + chống
    polyglot XSS (file đúng magic nhưng có payload HTML/JS phía sau). Caller
    nên dùng file_obj đã được normalize bằng cách gọi
    :func:`sanitize_image_inplace` ngay sau khi `validate_upload` pass.
    """
    if file_obj.size > max_size:
        raise ValidationError(
            f"File quá lớn ({file_obj.size / 1024 / 1024:.1f}MB). Tối đa "
            f"{max_size / 1024 / 1024:.0f}MB."
        )
    if file_obj.size == 0:
        raise ValidationError("File rỗng. Vui lòng chọn file khác.")

    file_obj.seek(0)
    head = file_obj.read(12)
    file_obj.seek(0)

    detected = None
    for mime, signatures in MAGIC_BYTES.items():
        for sig in signatures:
            if head.startswith(sig):
                detected = mime
                break
        if detected:
            break

    if not detected:
        raise ValidationError(
            "File không hợp lệ. Chỉ chấp nhận ảnh JPG, PNG hoặc PDF."
        )

    if detected.startswith("image/"):
        # Pillow verify: phát hiện corrupt + chống polyglot magic giả.
        try:
            from PIL import Image, ImageFile

            ImageFile.LOAD_TRUNCATED_IMAGES = False
            file_obj.seek(0)
            img = Image.open(file_obj)
            img.verify()
        except Exception as exc:
            raise ValidationError(
                "Ảnh không hợp lệ hoặc bị hỏng. Vui lòng chụp lại."
            ) from exc
        finally:
            file_obj.seek(0)

    return detected


def sanitize_image_inplace(file_obj, mime: str) -> tuple[InMemoryUploadedFile, str]:
    """Re-encode ảnh qua Pillow để strip EXIF + bảo đảm content chuẩn.

    Trả về file mới đã re-encode và mime cuối cùng (luôn ``image/jpeg`` sau khi
    re-encode để giảm bề mặt tấn công). Với PDF KHÔNG re-encode (chi phí cao),
    chỉ trả lại file_obj nguyên.

    Caller nên dùng file mới này khi tạo DocumentModel.
    """
    if not mime.startswith("image/"):
        return file_obj, mime

    from PIL import Image

    file_obj.seek(0)
    img = Image.open(file_obj)
    img.load()  # decode toàn bộ
    # Convert mode để chắc chắn JPEG save được (loại bỏ alpha trên PNG)
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=88, optimize=True)
    buf.seek(0)

    new_name = (file_obj.name.rsplit(".", 1)[0] if file_obj.name else "image") + ".jpg"
    new_file = InMemoryUploadedFile(
        file=buf,
        field_name=getattr(file_obj, "field_name", "file"),
        name=new_name,
        content_type="image/jpeg",
        size=buf.getbuffer().nbytes,
        charset=None,
    )
    return new_file, "image/jpeg"


class DocumentType(models.Model):
    """Loại tài liệu cấu hình động — admin tạo thêm khi cần."""

    class Scope(models.TextChoices):
        PERSON = "person", _("Gắn với người học")
        ENROLLMENT = "enrollment", _("Gắn với đơn ghi danh")

    code = models.SlugField(
        _("Mã"),
        max_length=50,
        unique=True,
        help_text=_("Định danh hệ thống. VD: cccd_front, portrait, health_cert."),
    )
    name = models.CharField(_("Tên hiển thị"), max_length=200)
    scope = models.CharField(
        _("Phạm vi"),
        max_length=20,
        choices=Scope.choices,
        default=Scope.PERSON,
    )
    is_required = models.BooleanField(
        _("Bắt buộc"),
        default=True,
        help_text=_("Nếu bật, FE sẽ liệt kê là 'thiếu' khi HV chưa upload."),
    )
    description = models.CharField(
        _("Hướng dẫn"),
        max_length=500,
        blank=True,
        default="",
        help_text=_("Hiển thị cho HV khi chuẩn bị upload."),
    )
    sort_order = models.PositiveSmallIntegerField(_("Thứ tự"), default=100)
    is_active = models.BooleanField(_("Đang dùng"), default=True)

    class Meta:
        verbose_name = _("Loại tài liệu")
        verbose_name_plural = _("Loại tài liệu")
        ordering = ["scope", "sort_order", "name"]

    def __str__(self) -> str:
        return self.name


class DocumentStatus(models.TextChoices):
    PENDING_REVIEW = "pending", _("Chờ duyệt")
    APPROVED = "approved", _("Đã duyệt")
    REJECTED = "rejected", _("Từ chối")
    EXPIRED = "expired", _("Hết hạn (cần upload lại)")
    PURGED = "purged", _("Đã xóa theo NĐ 13/2023")


def _private_upload_path(instance, filename: str) -> str:
    """Path file UUID — không tiết lộ tên gốc, không đoán được URL.

    Pattern: ``private_documents/<YYYY>/<MM>/<uuid4>.<ext>``.
    """
    import uuid

    ext = ""
    if "." in filename:
        ext = "." + filename.rsplit(".", 1)[-1].lower()[:6]
    now = models_now()
    return f"private_documents/{now:%Y/%m}/{uuid.uuid4().hex}{ext}"


def models_now():
    from django.utils import timezone

    return timezone.now()


class DocumentBase(models.Model):
    """Base abstract cho Person/Enrollment document."""

    document_type = models.ForeignKey(
        DocumentType,
        on_delete=models.PROTECT,
        related_name="+",
        verbose_name=_("Loại"),
    )
    file = models.FileField(
        _("Tập tin"),
        upload_to=_private_upload_path,
        max_length=500,
        help_text=_("Tối đa 5MB. JPG/PNG/PDF."),
    )
    mime_type = models.CharField(_("MIME"), max_length=50, blank=True, default="")
    file_size = models.PositiveIntegerField(_("Kích thước (bytes)"), default=0)

    status = models.CharField(
        _("Trạng thái"),
        max_length=20,
        choices=DocumentStatus.choices,
        default=DocumentStatus.PENDING_REVIEW,
    )
    review_note = models.CharField(
        _("Ghi chú duyệt"),
        max_length=500,
        blank=True,
        default="",
        help_text=_("Lý do từ chối / hướng dẫn upload lại."),
    )

    uploaded_by_account = models.ForeignKey(
        "students.StudentAccount",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("HV upload"),
    )
    uploaded_by_staff = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("Văn thư upload hộ"),
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("Người duyệt"),
    )
    reviewed_at = models.DateTimeField(_("Duyệt lúc"), null=True, blank=True)
    expires_at = models.DateTimeField(
        _("Lịch xóa tự động"),
        null=True,
        blank=True,
        help_text=_("CCCD/khám SK xóa sau 90 ngày kể từ khi hoàn thành khóa (NĐ 13/2023)."),
    )

    created_at = models.DateTimeField(_("Upload lúc"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Cập nhật"), auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]


class PersonDocument(DocumentBase):
    """Tài liệu cá nhân — gắn vào Person."""

    person = models.ForeignKey(
        "students.Person",
        on_delete=models.CASCADE,
        related_name="documents",
        verbose_name=_("Người học"),
    )

    class Meta(DocumentBase.Meta):
        verbose_name = _("Tài liệu cá nhân")
        verbose_name_plural = _("Tài liệu cá nhân")
        indexes = [
            models.Index(fields=["person", "status"]),
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["expires_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["person", "document_type"],
                condition=models.Q(status__in=["pending", "approved"]),
                name="uniq_active_person_doc_per_type",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.person.full_name} · {self.document_type.name}"


class EnrollmentDocument(DocumentBase):
    """Tài liệu theo đơn — gắn vào Enrollment."""

    enrollment = models.ForeignKey(
        "orders.Enrollment",
        on_delete=models.CASCADE,
        related_name="documents",
        verbose_name=_("Đơn ghi danh"),
    )

    class Meta(DocumentBase.Meta):
        verbose_name = _("Tài liệu theo đơn")
        verbose_name_plural = _("Tài liệu theo đơn")
        indexes = [
            models.Index(fields=["enrollment", "status"]),
            models.Index(fields=["status", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.enrollment.code} · {self.document_type.name}"
