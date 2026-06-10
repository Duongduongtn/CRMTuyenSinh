"""
App `students` — học viên đăng nhập PWA bằng SĐT + OTP (passwordless).

Theo memory [[person-enrollment-model]]: 3 tầng riêng biệt
- ``StudentAccount`` (SĐT): tài khoản đăng nhập, 1 SĐT 1 account.
- ``Person`` (CCCD): người thật theo CCCD, độc lập với SĐT.
- ``AccountPersonLink``: bảng nối N-N. 1 SĐT có thể đăng ký N người (mẹ đăng ký
  hộ 2 con); 1 người có thể được nhiều SĐT khác nhau đăng ký theo thời gian.

Auto-provision: khi sale chốt đơn (Enrollment created), nếu SĐT chưa có account
thì tạo ``StudentAccount`` mới, không cần học viên thao tác.

Quick view: link JWT 24h trong Zalo ZNS cho học viên xem công nợ không cần OTP.
Xem [[student-auth-flow]].
"""
from __future__ import annotations

import re
import secrets
from datetime import timedelta

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


def normalize_phone(raw: str) -> str:
    """Chuẩn hóa SĐT VN về dạng ``0xxxxxxxxx`` (10 số).

    - Bỏ khoảng trắng, dấu cách, dấu chấm, dấu gạch.
    - ``+84xxx`` → ``0xxx``.
    - ``84xxx`` (12 số) → ``0xxx``.
    - Giữ nguyên ``0xxxxxxxxx``.
    """
    if not raw:
        return ""
    cleaned = re.sub(r"[\s.\-()]", "", raw)
    if cleaned.startswith("+84"):
        cleaned = "0" + cleaned[3:]
    elif cleaned.startswith("84") and len(cleaned) == 11:
        cleaned = "0" + cleaned[2:]
    return cleaned


class StudentAccount(models.Model):
    """Tài khoản đăng nhập PWA — chỉ SĐT, không password."""

    phone = models.CharField(
        _("Số điện thoại"),
        max_length=15,
        unique=True,
        db_index=True,
        help_text=_("Định dạng chuẩn: 0xxxxxxxxx (10 số)."),
    )
    display_name = models.CharField(
        _("Tên hiển thị"),
        max_length=200,
        blank=True,
        default="",
        help_text=_("Hiển thị trên PWA. Lấy từ Person liên kết hoặc nhập tay."),
    )
    is_active = models.BooleanField(
        _("Đang hoạt động"),
        default=True,
        help_text=_("Tắt để cấm đăng nhập (vd HV vi phạm)."),
    )
    last_login_at = models.DateTimeField(
        _("Lần đăng nhập gần nhất"),
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(_("Tạo lúc"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Cập nhật"), auto_now=True)

    class Meta:
        verbose_name = _("Tài khoản học viên")
        verbose_name_plural = _("Tài khoản học viên")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.phone}{f' · {self.display_name}' if self.display_name else ''}"

    def save(self, *args, **kwargs):
        if self.phone:
            self.phone = normalize_phone(self.phone)
        super().save(*args, **kwargs)


class Person(models.Model):
    """Người thật theo CCCD — định danh độc lập với SĐT.

    1 Person có thể được nhiều ``StudentAccount`` đăng ký (mẹ đăng ký hộ con,
    đổi số điện thoại). Tài liệu chung (CCCD, ảnh chân dung, giấy khám SK)
    gắn vào Person; tài liệu riêng theo đơn (sơ yếu, đơn xin học) gắn vào
    ``Enrollment``.
    """

    full_name = models.CharField(_("Họ và tên"), max_length=200)
    id_number = models.CharField(
        _("Số CCCD/CMND"),
        max_length=20,
        blank=True,
        default="",
        db_index=True,
        help_text=_("12 số (CCCD) hoặc 9 số (CMND cũ). Để trống nếu chưa cấp."),
    )
    date_of_birth = models.DateField(
        _("Ngày sinh"),
        null=True,
        blank=True,
    )

    class Gender(models.TextChoices):
        MALE = "male", _("Nam")
        FEMALE = "female", _("Nữ")
        OTHER = "other", _("Khác")

    gender = models.CharField(
        _("Giới tính"),
        max_length=10,
        choices=Gender.choices,
        blank=True,
        default="",
    )
    permanent_address = models.CharField(
        _("Địa chỉ thường trú"),
        max_length=500,
        blank=True,
        default="",
    )
    current_address = models.CharField(
        _("Địa chỉ hiện tại"),
        max_length=500,
        blank=True,
        default="",
    )
    notes = models.TextField(_("Ghi chú nội bộ"), blank=True, default="")

    created_at = models.DateTimeField(_("Tạo lúc"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Cập nhật"), auto_now=True)

    class Meta:
        verbose_name = _("Người học")
        verbose_name_plural = _("Người học")
        ordering = ["full_name"]
        indexes = [
            models.Index(fields=["id_number"]),
            models.Index(fields=["full_name"]),
        ]

    def __str__(self) -> str:
        return self.full_name


class AccountPersonLink(models.Model):
    """Liên kết N-N giữa ``StudentAccount`` (SĐT) và ``Person`` (CCCD)."""

    class Relation(models.TextChoices):
        SELF = "self", _("Chính chủ")
        PARENT = "parent", _("Phụ huynh")
        CHILD = "child", _("Con")
        SPOUSE = "spouse", _("Vợ/chồng")
        OTHER = "other", _("Khác")

    account = models.ForeignKey(
        StudentAccount,
        on_delete=models.CASCADE,
        related_name="person_links",
        verbose_name=_("Tài khoản"),
    )
    person = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="account_links",
        verbose_name=_("Người học"),
    )
    relation = models.CharField(
        _("Quan hệ"),
        max_length=20,
        choices=Relation.choices,
        default=Relation.SELF,
    )
    is_primary = models.BooleanField(
        _("Bản thân"),
        default=False,
        help_text=_(
            "Bật cho chính chủ tài khoản. Mỗi account chỉ có tối đa 1 primary "
            "(nhưng có thể đăng ký hộ N người khác)."
        ),
    )
    created_at = models.DateTimeField(_("Tạo lúc"), auto_now_add=True)

    class Meta:
        verbose_name = _("Liên kết tài khoản - người học")
        verbose_name_plural = _("Liên kết tài khoản - người học")
        constraints = [
            models.UniqueConstraint(
                fields=["account", "person"],
                name="uniq_account_person",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.account.phone} → {self.person.full_name}"


class OTPRequest(models.Model):
    """Yêu cầu OTP cho login PWA.

    - Code 6 số, lifetime 5 phút.
    - Rate limit ở view: 5 request/giờ/SĐT (xem [[apps.students.views]]).
    - Lưu hashed code để tránh dump DB lộ code.
    """

    class Purpose(models.TextChoices):
        LOGIN = "login", _("Đăng nhập")
        VERIFY_PHONE = "verify_phone", _("Xác minh SĐT")

    class Status(models.TextChoices):
        PENDING = "pending", _("Chờ xác thực")
        VERIFIED = "verified", _("Đã xác thực")
        EXPIRED = "expired", _("Hết hạn")
        CONSUMED = "consumed", _("Đã dùng")

    phone = models.CharField(_("Số điện thoại"), max_length=15, db_index=True)
    code_hash = models.CharField(
        _("Hash mã OTP"),
        max_length=128,
        help_text=_("SHA-256 hex của mã OTP gốc."),
    )
    purpose = models.CharField(
        _("Mục đích"),
        max_length=20,
        choices=Purpose.choices,
        default=Purpose.LOGIN,
    )
    status = models.CharField(
        _("Trạng thái"),
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    attempts = models.PositiveSmallIntegerField(
        _("Số lần thử"),
        default=0,
        help_text=_("Khóa sau 5 lần nhập sai."),
    )
    ip_address = models.GenericIPAddressField(_("IP"), null=True, blank=True)
    user_agent = models.CharField(_("User agent"), max_length=255, blank=True, default="")
    expires_at = models.DateTimeField(_("Hết hạn lúc"))
    consumed_at = models.DateTimeField(_("Đã dùng lúc"), null=True, blank=True)
    sent_via = models.CharField(
        _("Gửi qua"),
        max_length=20,
        blank=True,
        default="",
        help_text=_("Ví dụ: zalo_zns, sms_fallback, mock_dev."),
    )
    sent_meta = models.JSONField(
        _("Metadata gửi"),
        blank=True,
        null=True,
        help_text=_("Payload từ provider (Zalo ZNS response, error code)."),
    )

    created_at = models.DateTimeField(_("Tạo lúc"), auto_now_add=True)

    class Meta:
        verbose_name = _("Yêu cầu OTP")
        verbose_name_plural = _("Yêu cầu OTP")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["phone", "-created_at"]),
            models.Index(fields=["status", "expires_at"]),
        ]

    def __str__(self) -> str:
        return f"OTP {self.phone} · {self.get_status_display()}"

    @staticmethod
    def generate_code() -> str:
        """Sinh OTP 6 số ngẫu nhiên (000000 đến 999999)."""
        return f"{secrets.randbelow(1_000_000):06d}"

    @staticmethod
    def hash_code(code: str) -> str:
        """SHA-256 hex của code thuần."""
        import hashlib

        return hashlib.sha256(code.encode("utf-8")).hexdigest()

    @classmethod
    def create_for_phone(
        cls,
        phone: str,
        *,
        purpose: str = Purpose.LOGIN,
        ttl_minutes: int = 5,
        ip_address: str | None = None,
        user_agent: str = "",
    ) -> tuple["OTPRequest", str]:
        """Tạo OTP mới và trả về (instance, plain_code).

        Plain code chỉ tồn tại trong response và log gửi — không lưu DB.
        """
        plain = cls.generate_code()
        obj = cls.objects.create(
            phone=normalize_phone(phone),
            code_hash=cls.hash_code(plain),
            purpose=purpose,
            expires_at=timezone.now() + timedelta(minutes=ttl_minutes),
            ip_address=ip_address,
            user_agent=user_agent[:255],
        )
        return obj, plain

    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at

    def verify(self, code: str) -> bool:
        """Verify code, tăng attempts, mark consumed nếu đúng.

        Return ``True`` nếu match + còn hạn + chưa dùng + attempts < 5.
        Caller phải save().
        """
        if self.status != self.Status.PENDING:
            return False
        if self.is_expired():
            self.status = self.Status.EXPIRED
            return False
        if self.attempts >= 5:
            self.status = self.Status.EXPIRED
            return False
        self.attempts += 1
        if self.hash_code(code) != self.code_hash:
            return False
        self.status = self.Status.CONSUMED
        self.consumed_at = timezone.now()
        return True


class StudentDeleteRequest(models.Model):
    """Học viên gửi yêu cầu xóa dữ liệu theo NĐ 13/2023/NĐ-CP Điều 9.

    KHÔNG tự xóa dữ liệu ở backend. Văn thư/admin sẽ xử lý thủ công trong CRM
    (xem hồ sơ, đối chiếu công nợ, phê duyệt hoặc từ chối có lý do). Lý do:
    HV còn nợ học phí, đang trong khóa học, hoặc hồ sơ đã nộp Sở GTVT thì cần
    người ra quyết định, không thể auto-delete.
    """

    class Status(models.TextChoices):
        RECEIVED = "received", _("Đã tiếp nhận")
        IN_REVIEW = "in_review", _("Đang xử lý")
        APPROVED = "approved", _("Đã chấp thuận")
        REJECTED = "rejected", _("Từ chối")
        COMPLETED = "completed", _("Đã xóa dữ liệu")

    account = models.ForeignKey(
        StudentAccount,
        on_delete=models.CASCADE,
        related_name="delete_requests",
        verbose_name=_("Tài khoản học viên"),
    )
    reason = models.TextField(
        _("Lý do yêu cầu"),
        blank=True,
        default="",
        help_text=_("HV nhập tự do. KHÔNG bắt buộc theo NĐ 13/2023."),
    )
    status = models.CharField(
        _("Trạng thái"),
        max_length=20,
        choices=Status.choices,
        default=Status.RECEIVED,
    )
    handler_note = models.TextField(
        _("Ghi chú xử lý"),
        blank=True,
        default="",
        help_text=_("Nội bộ — lý do duyệt/từ chối, các bước đã thực hiện."),
    )
    ip_address = models.GenericIPAddressField(_("IP"), null=True, blank=True)
    user_agent = models.CharField(_("User agent"), max_length=255, blank=True, default="")
    telegram_sent_at = models.DateTimeField(_("Đã gửi Telegram lúc"), null=True, blank=True)
    handled_at = models.DateTimeField(_("Xử lý xong lúc"), null=True, blank=True)
    handled_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="handled_delete_requests",
        verbose_name=_("Người xử lý"),
    )

    created_at = models.DateTimeField(_("Tạo lúc"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Cập nhật"), auto_now=True)

    class Meta:
        verbose_name = _("Yêu cầu xóa dữ liệu (NĐ 13/2023)")
        verbose_name_plural = _("Yêu cầu xóa dữ liệu (NĐ 13/2023)")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["account", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"Yêu cầu xóa #{self.pk} · {self.account.phone}"
