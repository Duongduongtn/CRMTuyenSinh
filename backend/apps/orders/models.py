"""
App `orders` — đơn ghi danh học viên (Enrollment = Order trong domain language).

1 Enrollment = 1 học viên đăng ký 1 khóa cụ thể. Tiền cọc và học phí gắn vào đây.
Theo memory [[person-enrollment-model]]: Enrollment là tầng giữa Person (CCCD) và Course.
Hiện tại Sprint 1 chưa có app `students` nên student info được denormalize tại chỗ
(name + phone + email + vehicle_class). Sprint 2 sẽ link sang Person/StudentAccount.
"""
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.courses.models import VehicleClass


class EnrollmentStatus(models.TextChoices):
    PENDING = "pending", _("Chờ cọc")
    DEPOSITED = "deposited", _("Đã cọc")
    PARTIAL = "partial", _("Đã đóng một phần")
    COMPLETED = "completed", _("Đã đóng đủ")
    CANCELLED = "cancelled", _("Đã hủy")
    REFUNDED = "refunded", _("Đã hoàn tiền")


class Enrollment(models.Model):
    """Đơn ghi danh học viên cho 1 khóa học cụ thể.

    Mã đơn `code` định dạng ORD-XXXXXX (6 ký tự hex viết hoa), unique toàn hệ thống.
    Được dùng làm `addInfo` khi học viên chuyển khoản đặt cọc — webhook Casso match
    regex `\\bORD-[A-F0-9]{6}\\b` (xem [[apps.payments.webhooks]]).
    """

    # Định danh
    code = models.CharField(
        _("Mã đơn"),
        max_length=20,
        unique=True,
        db_index=True,
        help_text=_("Định dạng ORD-XXXXXX. Dùng làm nội dung chuyển khoản đặt cọc."),
    )

    # Nguồn
    lead = models.OneToOneField(
        "leads.Lead",
        on_delete=models.PROTECT,
        related_name="enrollment",
        null=True,
        blank=True,
        verbose_name=_("Lead gốc"),
        help_text=_("OneToOne — mỗi lead chuyển thành tối đa 1 enrollment để đảm bảo idempotent."),
    )
    course = models.ForeignKey(
        "courses.Course",
        on_delete=models.PROTECT,
        related_name="enrollments",
        verbose_name=_("Khóa học"),
    )

    # Thông tin học viên (denormalized tại thời điểm convert)
    student_name = models.CharField(_("Họ tên học viên"), max_length=200)
    student_phone = models.CharField(_("SĐT học viên"), max_length=15, db_index=True)
    student_email = models.EmailField(_("Email học viên"), blank=True, default="")
    vehicle_class = models.CharField(
        _("Hạng GPLX"),
        max_length=10,
        choices=VehicleClass.choices,
        help_text=_("Snapshot từ course tại thời điểm convert."),
    )

    # Tài chính (snapshot từ course để khóa giá tại thời điểm chốt đơn)
    tuition_fee = models.DecimalField(
        _("Học phí"),
        max_digits=12,
        decimal_places=0,
        validators=[MinValueValidator(0)],
    )
    deposit_amount = models.DecimalField(
        _("Cọc cần đóng"),
        max_digits=12,
        decimal_places=0,
        validators=[MinValueValidator(0)],
        help_text=_("Số tiền cọc tối thiểu để giữ chỗ."),
    )
    paid_amount = models.DecimalField(
        _("Đã đóng"),
        max_digits=12,
        decimal_places=0,
        default=Decimal("0"),
        validators=[MinValueValidator(0)],
        help_text=_("Tổng cộng các Payment đã confirm. Cập nhật từ webhook Casso."),
    )

    # Trạng thái
    status = models.CharField(
        _("Trạng thái"),
        max_length=20,
        choices=EnrollmentStatus.choices,
        default=EnrollmentStatus.PENDING,
    )
    notes = models.TextField(_("Ghi chú nội bộ"), blank=True, default="")

    # Phân công
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_enrollments",
        verbose_name=_("Người tạo đơn"),
    )

    # Public access (FE trang đặt cọc /dh/[code] không cần login)
    deposit_link_token = models.UUIDField(
        _("Token trang đặt cọc"),
        unique=True,
        editable=False,
        help_text=_("Token random để chia sẻ link đặt cọc cho HV qua Zalo ZNS."),
    )

    created_at = models.DateTimeField(_("Tạo lúc"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Cập nhật"), auto_now=True)
    deposit_paid_at = models.DateTimeField(_("Đóng cọc lúc"), null=True, blank=True)
    completed_at = models.DateTimeField(_("Đóng đủ lúc"), null=True, blank=True)

    class Meta:
        verbose_name = _("Đơn ghi danh")
        verbose_name_plural = _("Đơn ghi danh")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["student_phone"]),
            models.Index(fields=["course", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.code} · {self.student_name}"

    def save(self, *args, **kwargs):
        # Sinh token public nếu chưa có
        if not self.deposit_link_token:
            import uuid

            self.deposit_link_token = uuid.uuid4()
        super().save(*args, **kwargs)

    # --- Domain helpers ---

    @property
    def remaining_amount(self) -> Decimal:
        return max(Decimal("0"), self.tuition_fee - self.paid_amount)

    @property
    def is_deposit_paid(self) -> bool:
        return self.paid_amount >= self.deposit_amount

    def recompute_status_from_paid(self) -> str:
        """Cập nhật status dựa trên paid_amount vs tuition_fee và deposit_amount.

        KHÔNG save — caller tự save với update_fields phù hợp.
        Không downgrade status nếu đã cancelled/refunded.
        """
        from django.utils import timezone as tz

        if self.status in (EnrollmentStatus.CANCELLED, EnrollmentStatus.REFUNDED):
            return self.status
        if self.paid_amount <= 0:
            self.status = EnrollmentStatus.PENDING
            return self.status
        if self.paid_amount >= self.tuition_fee:
            self.status = EnrollmentStatus.COMPLETED
            if not self.completed_at:
                self.completed_at = tz.now()
            return self.status
        if self.paid_amount >= self.deposit_amount:
            # Đủ cọc nhưng chưa đủ học phí
            if not self.deposit_paid_at:
                self.deposit_paid_at = tz.now()
            # Phân biệt deposited (chỉ vừa đủ cọc) vs partial (đóng thêm sau cọc)
            self.status = (
                EnrollmentStatus.DEPOSITED
                if self.paid_amount == self.deposit_amount
                else EnrollmentStatus.PARTIAL
            )
            return self.status
        # Có tiền nhưng chưa đủ cọc → partial
        self.status = EnrollmentStatus.PARTIAL
        return self.status

    @staticmethod
    def generate_code() -> str:
        """Sinh mã ORD-XXXXXX 6 ký tự hex viết hoa.

        Caller phải check unique và retry trong transaction nếu collision (xác suất
        cực thấp với 16^6 ~ 16,7 triệu mã).
        """
        import secrets

        return f"ORD-{secrets.token_hex(3).upper()}"
