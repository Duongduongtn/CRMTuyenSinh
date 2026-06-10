"""
Khóa học theo 9 hạng GPLX của Luật Trật tự An toàn giao thông 2024 (áp dụng 2025).

KHÔNG dùng hệ cũ A1/A2/B1/B2/C/D/E. Xem [[vehicle-classes-2025]] memory.
"""
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


class VehicleClass(models.TextChoices):
    """9 hạng GPLX theo Luật 2025."""

    # Mô tô (3 hạng)
    A1 = "A1", "A1 - Mô tô phổ thông dưới 175cc"
    A = "A", "A - Mô tô phân khối lớn trên 175cc"
    B1 = "B1", "B1 - Mô tô 3 bánh, xe điện công suất lớn"

    # Ô tô (6 hạng)
    B_AT = "B_AT", "B số tự động - Ô tô con dưới 9 chỗ, số tự động"
    B_MT = "B_MT", "B số sàn - Ô tô con dưới 9 chỗ"
    C1 = "C1", "C1 - Xe tải dưới 7,5 tấn"
    C = "C", "C - Xe tải trên 7,5 tấn"
    D1 = "D1", "D1 - Xe khách đến 16 chỗ"
    D2 = "D2", "D2 - Xe khách trên 16 chỗ"


class VehicleGroup(models.TextChoices):
    """Nhóm hạng để filter/SEO."""

    MOTORCYCLE = "motorcycle", "Mô tô"
    CAR = "car", "Ô tô con"
    TRUCK = "truck", "Xe tải"
    BUS = "bus", "Xe khách"
    UPGRADE = "upgrade", "Nâng hạng"


# Map hạng → nhóm để auto-fill
VEHICLE_CLASS_TO_GROUP: dict[str, str] = {
    VehicleClass.A1: VehicleGroup.MOTORCYCLE,
    VehicleClass.A: VehicleGroup.MOTORCYCLE,
    VehicleClass.B1: VehicleGroup.MOTORCYCLE,
    VehicleClass.B_AT: VehicleGroup.CAR,
    VehicleClass.B_MT: VehicleGroup.CAR,
    VehicleClass.C1: VehicleGroup.TRUCK,
    VehicleClass.C: VehicleGroup.TRUCK,
    VehicleClass.D1: VehicleGroup.BUS,
    VehicleClass.D2: VehicleGroup.BUS,
}


class Course(models.Model):
    """Khóa học cho 1 hạng GPLX cụ thể."""

    slug = models.SlugField(
        _("Slug SEO"),
        max_length=200,
        unique=True,
        help_text=_("Phần URL trên FE public: /khoa-hoc/{slug}. Ví dụ: b-so-san."),
    )
    title = models.CharField(_("Tên khóa"), max_length=200)
    vehicle_class = models.CharField(
        _("Hạng GPLX"),
        max_length=10,
        choices=VehicleClass.choices,
    )
    vehicle_group = models.CharField(
        _("Nhóm"),
        max_length=20,
        choices=VehicleGroup.choices,
        help_text=_("Tự động điền theo hạng. Đổi sang 'Nâng hạng' nếu là khóa nâng."),
    )

    # Tóm tắt
    short_description = models.CharField(
        _("Mô tả ngắn"),
        max_length=255,
        blank=True,
        help_text=_("1 câu, hiển thị trên card khóa học."),
    )
    description_md = models.TextField(
        _("Mô tả chi tiết (Markdown)"),
        blank=True,
        help_text=_("Hỗ trợ Markdown. Render trên trang chi tiết khóa."),
    )

    # Học phí và cọc
    tuition_fee = models.DecimalField(
        _("Học phí"),
        max_digits=12,
        decimal_places=0,
        validators=[MinValueValidator(0)],
    )
    deposit_amount = models.DecimalField(
        _("Đặt cọc giữ chỗ"),
        max_digits=12,
        decimal_places=0,
        default=200_000,
        validators=[MinValueValidator(0)],
    )

    # Thời lượng
    duration_days = models.PositiveIntegerField(
        _("Thời gian (ngày)"),
        default=120,
        help_text=_("Số ngày từ khai giảng đến thi sát hạch."),
    )
    duration_display = models.CharField(
        _("Thời gian hiển thị"),
        max_length=50,
        blank=True,
        help_text=_("Hiển thị FE. Ví dụ: '4 tháng', '2 tuần'."),
    )

    # Slot
    total_slots = models.PositiveIntegerField(_("Tổng số suất"), default=30)
    available_slots = models.PositiveIntegerField(
        _("Còn lại"),
        default=30,
        help_text=_("Trừ tự động khi convert lead → order."),
    )

    # Image + SEO
    cover_image = models.ImageField(
        _("Ảnh đại diện"),
        upload_to="courses/",
        blank=True,
        null=True,
    )
    meta_title = models.CharField(_("Meta title"), max_length=70, blank=True)
    meta_description = models.CharField(_("Meta description"), max_length=170, blank=True)
    og_image = models.ImageField(
        _("OG image"),
        upload_to="courses/",
        blank=True,
        null=True,
    )

    # Visibility
    is_visible = models.BooleanField(
        _("Hiển thị trên FE"),
        default=True,
        help_text=_("Tắt khi ngừng tuyển sinh khóa này. Đơn cũ vẫn xem được trong CRM."),
    )
    is_featured = models.BooleanField(
        _("Nổi bật"),
        default=False,
        help_text=_("Card sẽ có badge 'Phổ biến' và viền nổi bật trên FE."),
    )
    sort_order = models.PositiveSmallIntegerField(_("Thứ tự hiển thị"), default=100)

    created_at = models.DateTimeField(_("Tạo lúc"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Cập nhật"), auto_now=True)

    class Meta:
        verbose_name = _("Khóa học")
        verbose_name_plural = _("Khóa học")
        ordering = ["sort_order", "title"]
        indexes = [
            models.Index(fields=["is_visible", "sort_order"]),
            models.Index(fields=["vehicle_group", "vehicle_class"]),
        ]

    def __str__(self) -> str:
        return self.title

    def save(self, *args, **kwargs):
        # Auto-fill vehicle_group từ vehicle_class nếu chưa set
        if not self.vehicle_group and self.vehicle_class:
            self.vehicle_group = VEHICLE_CLASS_TO_GROUP.get(
                self.vehicle_class, VehicleGroup.UPGRADE
            )
        super().save(*args, **kwargs)


class CourseSchedule(models.Model):
    """Lịch khai giảng cho 1 khóa. 1 Course có thể có nhiều Schedule."""

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="schedules",
        verbose_name=_("Khóa học"),
    )
    start_date = models.DateField(_("Ngày khai giảng"))
    end_date = models.DateField(_("Ngày dự kiến thi"), null=True, blank=True)
    instructor_name = models.CharField(
        _("Huấn luyện viên chính"),
        max_length=100,
        blank=True,
    )
    max_students = models.PositiveIntegerField(_("Sĩ số tối đa"), default=30)
    enrolled_count = models.PositiveIntegerField(_("Đã đăng ký"), default=0)
    is_open = models.BooleanField(
        _("Đang mở"),
        default=True,
        help_text=_("Tắt khi đã đầy slot hoặc đến giờ chốt."),
    )
    note = models.CharField(_("Ghi chú"), max_length=255, blank=True)

    created_at = models.DateTimeField(_("Tạo lúc"), auto_now_add=True)

    class Meta:
        verbose_name = _("Lịch khai giảng")
        verbose_name_plural = _("Lịch khai giảng")
        ordering = ["start_date"]
        indexes = [
            models.Index(fields=["course", "is_open", "start_date"]),
        ]

    def __str__(self) -> str:
        return f"{self.course.title} · {self.start_date:%d/%m/%Y}"

    @property
    def remaining_slots(self) -> int:
        return max(0, self.max_students - self.enrolled_count)
