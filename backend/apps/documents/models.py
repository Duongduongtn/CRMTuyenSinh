"""
App `documents` — hồ sơ học viên.

2 loại tài liệu (theo memory [[person-enrollment-model]]):
- ``PersonDocument``: CCCD 2 mặt, ảnh chân dung, giấy khám sức khỏe — gắn với
  Person (dùng chung cho nhiều Enrollment nếu HV đăng ký nhiều khóa).
- ``EnrollmentDocument``: sơ yếu lý lịch, đơn xin học, hợp đồng — gắn với
  Enrollment cụ thể.

Auto-purge CCCD sau 90 ngày kể từ ngày hoàn thành khóa (NĐ 13/2023 về BVDLCN).
Xem [[apps.documents.tasks]].
"""
from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _


MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5 MB

ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "application/pdf",
}

# Magic bytes (file signature) — chống upload .exe đổi đuôi .jpg
MAGIC_BYTES = {
    "image/jpeg": [b"\xff\xd8\xff"],
    "image/png": [b"\x89PNG\r\n\x1a\n"],
    "image/webp": [b"RIFF"],  # check thêm "WEBP" ở byte 8-12
    "application/pdf": [b"%PDF-"],
}


def validate_upload(file_obj, *, max_size: int = MAX_UPLOAD_SIZE) -> str:
    """Validate file upload: size + magic bytes.

    Return MIME type detect được. Raise ``ValidationError`` nếu invalid.

    Đọc 12 byte đầu để check magic. Reset pointer sau khi đọc — caller có
    thể tiếp tục đọc/save bình thường.
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
                if mime == "image/webp":
                    # WebP: "RIFF" + 4 byte size + "WEBP"
                    if len(head) >= 12 and head[8:12] == b"WEBP":
                        detected = mime
                        break
                else:
                    detected = mime
                    break
        if detected:
            break

    if not detected:
        raise ValidationError(
            "File không hợp lệ. Chỉ chấp nhận ảnh JPG, PNG, WEBP hoặc PDF."
        )
    return detected


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
        upload_to="documents/%Y/%m/",
        max_length=500,
        help_text=_("Tối đa 5MB. JPG/PNG/WEBP/PDF."),
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
