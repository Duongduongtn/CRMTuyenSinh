"""
App `students` — học viên đăng nhập PWA bằng SĐT + 6 số cuối CCCD.

Theo memory [[person-enrollment-model]]: 3 tầng riêng biệt
- ``StudentAccount`` (SĐT): tài khoản đăng nhập, 1 SĐT 1 account. Có counter
  ``failed_login_count`` + ``locked_until`` để rate limit brute force.
- ``Person`` (CCCD): người thật theo CCCD, độc lập với SĐT. Xác thực login bằng
  6 số cuối ``id_number``.
- ``AccountPersonLink``: bảng nối N-N. 1 SĐT có thể đăng ký N người (mẹ đăng ký
  hộ 2 con); 1 người có thể được nhiều SĐT khác nhau đăng ký theo thời gian.

Auto-provision: khi sale chốt đơn (Enrollment created), nếu SĐT chưa có account
thì tạo ``StudentAccount`` mới, không cần học viên thao tác.

Quick view: văn thư CRM bấm "Tạo link xem nhanh" → BE gen JWT 24h, văn thư copy
link gửi tay cho HV qua Zalo/SMS/gọi điện. Xem [[student-auth-flow]] đã chốt
2026-06-11 bỏ ZNS OTP, chuyển sang SĐT + 6 số cuối CCCD.
"""
from __future__ import annotations

import re
from datetime import timedelta

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


LOCK_THRESHOLD_SHORT = 5  # fail/SĐT → khóa 15 phút
LOCK_DURATION_SHORT = timedelta(minutes=15)
LOCK_THRESHOLD_LONG = 10  # fail tổng/SĐT → khóa 24 giờ, văn thư mở tay
LOCK_DURATION_LONG = timedelta(hours=24)


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
    last_login_ip = models.GenericIPAddressField(
        _("IP đăng nhập gần nhất"),
        null=True,
        blank=True,
    )
    failed_login_count = models.PositiveSmallIntegerField(
        _("Số lần đăng nhập sai liên tiếp"),
        default=0,
        help_text=_(
            "Khóa 15 phút sau 5 lần, khóa 24 giờ sau 10 lần. Reset về 0 khi "
            "đăng nhập thành công."
        ),
    )
    locked_until = models.DateTimeField(
        _("Tạm khóa đến"),
        null=True,
        blank=True,
        help_text=_("Sau thời điểm này tài khoản có thể đăng nhập lại."),
    )
    created_at = models.DateTimeField(_("Tạo lúc"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Cập nhật"), auto_now=True)

    class Meta:
        verbose_name = _("Tài khoản học viên")
        verbose_name_plural = _("Tài khoản học viên")
        ordering = ["-created_at"]
        indexes = [
            # Hỗ trợ truy vấn admin "đang khóa" + cron unlock định kỳ.
            models.Index(fields=["locked_until"], name="sa_locked_until_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.phone}{f' · {self.display_name}' if self.display_name else ''}"

    def save(self, *args, **kwargs):
        if self.phone:
            self.phone = normalize_phone(self.phone)
        super().save(*args, **kwargs)

    def is_locked(self, now=None) -> bool:
        """True nếu ``locked_until`` còn hiệu lực."""
        if not self.locked_until:
            return False
        return (now or timezone.now()) < self.locked_until

    def lock_remaining_seconds(self, now=None) -> int:
        """Số giây còn lại của lock; 0 nếu hết hoặc chưa khóa."""
        if not self.locked_until:
            return 0
        delta = self.locked_until - (now or timezone.now())
        return max(0, int(delta.total_seconds()))

    def register_login_failure(self, *, ip: str | None = None) -> None:
        """Tăng counter + đặt lock theo mốc ngưỡng. Atomic, không phụ thuộc caller save.

        Race condition fix (reviewer 2026-06-12): trước đây đọc-sửa-ghi trong
        Python → 2 request song song cùng đọc count=4 và ghi count=5 → lọt qua
        ngưỡng. Bây giờ dùng ``F()`` expression + ``update_fields=[...]`` để DB
        tăng atomic, rồi reload state quyết định lock.

        - Sau ``LOCK_THRESHOLD_SHORT`` (5) → khóa 15 phút.
        - Sau mỗi mốc bội của 5 từ ``LOCK_THRESHOLD_LONG`` (10) → khóa 24 giờ.
        """
        from django.db.models import F

        # Atomic increment + ip update qua DB.
        StudentAccount.objects.filter(pk=self.pk).update(
            failed_login_count=F("failed_login_count") + 1,
            last_login_ip=ip,
            updated_at=timezone.now(),
        )
        # Reload counter mới nhất từ DB để đánh giá ngưỡng.
        self.refresh_from_db(fields=["failed_login_count", "last_login_ip", "locked_until"])

        now = timezone.now()
        count = self.failed_login_count
        new_lock = None
        if count >= LOCK_THRESHOLD_LONG and count % 5 == 0:
            new_lock = now + LOCK_DURATION_LONG
        elif count == LOCK_THRESHOLD_SHORT:
            new_lock = now + LOCK_DURATION_SHORT

        if new_lock is not None:
            StudentAccount.objects.filter(pk=self.pk).update(
                locked_until=new_lock,
                updated_at=timezone.now(),
            )
            self.locked_until = new_lock

    def register_login_success(self, *, ip: str | None = None) -> bool:
        """Reset counter, mở khóa, cập nhật last_login. Atomic. Caller không cần save().

        Trả ``True`` nếu trước đó tài khoản từng có ``locked_until`` (đã hết
        hạn nhưng chưa clear) — phục vụ audit ``was_locked`` flag.
        """
        was_locked = self.locked_until is not None
        StudentAccount.objects.filter(pk=self.pk).update(
            failed_login_count=0,
            locked_until=None,
            last_login_at=timezone.now(),
            last_login_ip=ip,
            updated_at=timezone.now(),
        )
        self.failed_login_count = 0
        self.locked_until = None
        self.last_login_at = timezone.now()
        self.last_login_ip = ip
        return was_locked


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
            # Mỗi account tối đa 1 primary Person. Chặn race condition khi 2
            # convert song song cùng SĐT tạo 2 primary Link (reviewer Z, P1.2).
            models.UniqueConstraint(
                fields=["account"],
                condition=models.Q(is_primary=True),
                name="uniq_primary_link_per_account",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.account.phone} → {self.person.full_name}"


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
