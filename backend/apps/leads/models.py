"""
App `leads` — quản lý khách hàng tiềm năng.

4 models:
- `Lead`: thông tin khách + tracking + status
- `LeadReason`: danh sách lý do "đang theo dõi" / "thất bại" (quản lý qua admin)
- `LeadContact`: mỗi lần liên hệ là 1 record (audit trail tư vấn)
- `LeadNote`: ghi chú nội bộ của nhân viên về lead

Pattern kế thừa từ website_thanhdat (production-grade).
"""
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.courses.models import VehicleClass


class LeadStatus(models.TextChoices):
    NEW = "new", _("Chưa liên hệ")
    FOLLOWING = "following", _("Đang theo dõi")
    SUCCESS = "success", _("Thành công")
    FAILED = "failed", _("Thất bại")


class LeadPriority(models.TextChoices):
    HOT = "hot", _("Nóng")
    WARM = "warm", _("Ấm")
    COLD = "cold", _("Lạnh")


class LeadSource(models.TextChoices):
    WEBSITE = "website", _("Website / form đăng ký")
    LANDING = "landing", _("Landing page chiến dịch")
    HOTLINE = "hotline", _("Gọi hotline")
    ZALO = "zalo", _("Zalo OA")
    FB_ADS = "fb_ads", _("Facebook Lead Ads")
    PHONE = "phone", _("Gọi điện trực tiếp")
    REFERRAL = "referral", _("Giới thiệu")
    IMPORT = "import", _("Import Excel")
    OTHER = "other", _("Khác")


class LeadReason(models.Model):
    """Lý do quản lý: sale chọn dropdown khi chuyển status thành following hoặc failed."""

    class StatusScope(models.TextChoices):
        FOLLOWING = "following", _("Đang theo dõi")
        FAILED = "failed", _("Thất bại")

    name = models.CharField(_("Lý do"), max_length=200)
    status_scope = models.CharField(
        _("Áp dụng cho trạng thái"),
        max_length=20,
        choices=StatusScope.choices,
    )
    sort_order = models.PositiveSmallIntegerField(_("Thứ tự"), default=100)
    is_active = models.BooleanField(_("Đang dùng"), default=True)
    created_at = models.DateTimeField(_("Tạo lúc"), auto_now_add=True)

    class Meta:
        verbose_name = _("Lý do (lead)")
        verbose_name_plural = _("Danh sách lý do (lead)")
        ordering = ["status_scope", "sort_order", "name"]
        indexes = [models.Index(fields=["status_scope", "is_active", "sort_order"])]

    def __str__(self) -> str:
        return f"{self.get_status_scope_display()}: {self.name}"


class Lead(models.Model):
    """Khách hàng tiềm năng."""

    # Thông tin khách
    name = models.CharField(_("Họ và tên"), max_length=200)
    phone = models.CharField(_("Số điện thoại"), max_length=15, db_index=True)
    email = models.EmailField(_("Email"), blank=True, default="")
    district = models.CharField(_("Khu vực"), max_length=100, blank=True, default="")
    address = models.CharField(_("Địa chỉ"), max_length=255, blank=True, default="")
    notes = models.TextField(
        _("Ghi chú từ khách"),
        blank=True,
        default="",
        help_text=_("Nội dung khách nhập trong form (yêu cầu, câu hỏi)."),
    )

    # Hạng quan tâm
    vehicle_class = models.CharField(
        _("Hạng xe quan tâm"),
        max_length=10,
        choices=VehicleClass.choices,
        blank=True,
        default="",
    )

    # Trạng thái
    status = models.CharField(
        _("Trạng thái"),
        max_length=20,
        choices=LeadStatus.choices,
        default=LeadStatus.NEW,
    )
    priority = models.CharField(
        _("Độ nóng"),
        max_length=10,
        choices=LeadPriority.choices,
        blank=True,
        default="",
        help_text=_("Set khi status=following."),
    )
    reason = models.ForeignKey(
        LeadReason,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="leads",
        verbose_name=_("Lý do hiện tại"),
    )
    reason_text = models.CharField(
        _("Lý do (text khác)"),
        max_length=255,
        blank=True,
        default="",
        help_text=_("Nếu lý do không có sẵn trong dropdown."),
    )

    # Phân công
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_leads",
        verbose_name=_("Người phụ trách"),
    )

    # Tracking liên hệ
    contact_count = models.PositiveSmallIntegerField(_("Số lần liên hệ"), default=0)
    last_contact_at = models.DateTimeField(_("Lần liên hệ gần nhất"), null=True, blank=True)
    last_contact_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="last_contact_leads",
        verbose_name=_("Người liên hệ cuối"),
    )
    next_contact_date = models.DateField(
        _("Hẹn liên hệ tiếp"),
        null=True,
        blank=True,
        help_text=_("Hệ thống nhắc khi tới ngày."),
    )

    # Nguồn
    source = models.CharField(
        _("Nguồn"),
        max_length=20,
        choices=LeadSource.choices,
        default=LeadSource.WEBSITE,
    )
    source_page = models.CharField(
        _("Trang nguồn"),
        max_length=255,
        blank=True,
        default="",
        help_text=_("URL trang khách submit từ. Ví dụ: /khoa-hoc/b-so-san"),
    )
    source_title = models.CharField(_("Tiêu đề trang nguồn"), max_length=200, blank=True, default="")

    # UTM tracking
    utm_source = models.CharField(_("UTM source"), max_length=100, blank=True, default="")
    utm_medium = models.CharField(_("UTM medium"), max_length=100, blank=True, default="")
    utm_campaign = models.CharField(_("UTM campaign"), max_length=100, blank=True, default="")
    utm_content = models.CharField(_("UTM content"), max_length=100, blank=True, default="")
    utm_term = models.CharField(_("UTM term"), max_length=100, blank=True, default="")

    # Device info
    device_type = models.CharField(_("Loại thiết bị"), max_length=20, blank=True, default="")
    device_os = models.CharField(_("Hệ điều hành"), max_length=50, blank=True, default="")
    device_browser = models.CharField(_("Trình duyệt"), max_length=50, blank=True, default="")
    screen_size = models.CharField(_("Kích thước màn hình"), max_length=20, blank=True, default="")
    ip_address = models.GenericIPAddressField(_("IP"), null=True, blank=True)
    user_agent = models.CharField(_("User agent"), max_length=500, blank=True, default="")

    # Chuyển đổi
    converted_to_order = models.BooleanField(_("Đã chuyển thành đơn"), default=False)
    order_code = models.CharField(
        _("Mã đơn"),
        max_length=30,
        blank=True,
        default="",
        help_text=_("Liên kết với Enrollment.code sau khi convert. Sẽ chuyển thành FK ở Sprint 1 Tuần 3."),
    )
    converted_at = models.DateTimeField(_("Chuyển lúc"), null=True, blank=True)

    created_at = models.DateTimeField(_("Tạo lúc"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Cập nhật"), auto_now=True)

    class Meta:
        verbose_name = _("Lead")
        verbose_name_plural = _("Lead (khách quan tâm)")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["assigned_to", "status"]),
            models.Index(fields=["phone"]),
            models.Index(fields=["next_contact_date"]),
            models.Index(fields=["source", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} · {self.phone}"

    def record_contact(self, *, user, contact_type, status_after, **kwargs):
        """Helper tạo LeadContact đồng thời cập nhật counter trên Lead."""
        from django.utils import timezone as tz

        status_before = self.status
        contact = LeadContact.objects.create(
            lead=self,
            user=user,
            contact_type=contact_type,
            status_before=status_before,
            status_after=status_after,
            priority_after=kwargs.get("priority_after", ""),
            reason=kwargs.get("reason"),
            reason_text=kwargs.get("reason_text", ""),
            note=kwargs.get("note", ""),
            next_contact_date=kwargs.get("next_contact_date"),
        )
        self.status = status_after
        if kwargs.get("priority_after"):
            self.priority = kwargs["priority_after"]
        if kwargs.get("reason"):
            self.reason = kwargs["reason"]
        if kwargs.get("next_contact_date"):
            self.next_contact_date = kwargs["next_contact_date"]
        self.contact_count = (self.contact_count or 0) + 1
        self.last_contact_at = tz.now()
        self.last_contact_by = user
        self.save(
            update_fields=[
                "status",
                "priority",
                "reason",
                "next_contact_date",
                "contact_count",
                "last_contact_at",
                "last_contact_by",
                "updated_at",
            ]
        )
        return contact


class LeadContact(models.Model):
    """Mỗi lần liên hệ là 1 record. Audit trail tư vấn."""

    class ContactType(models.TextChoices):
        CALL = "call", _("Gọi điện")
        ZALO = "zalo", _("Zalo")
        SMS = "sms", _("SMS")
        EMAIL = "email", _("Email")
        OTHER = "other", _("Khác")

    lead = models.ForeignKey(
        Lead,
        on_delete=models.CASCADE,
        related_name="contacts",
        verbose_name=_("Lead"),
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="lead_contacts",
        verbose_name=_("Nhân viên thực hiện"),
    )
    contact_type = models.CharField(
        _("Hình thức"),
        max_length=20,
        choices=ContactType.choices,
        default=ContactType.CALL,
    )

    # Snapshot trạng thái trước/sau để truy vết
    status_before = models.CharField(_("Trạng thái cũ"), max_length=20, choices=LeadStatus.choices)
    status_after = models.CharField(_("Trạng thái mới"), max_length=20, choices=LeadStatus.choices)
    priority_after = models.CharField(
        _("Độ nóng (sau khi cập nhật)"),
        max_length=10,
        choices=LeadPriority.choices,
        blank=True,
        default="",
    )

    reason = models.ForeignKey(
        LeadReason,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contacts",
        verbose_name=_("Lý do"),
    )
    reason_text = models.CharField(_("Lý do (text khác)"), max_length=255, blank=True, default="")
    note = models.TextField(_("Ghi chú nhân viên"), blank=True, default="")
    next_contact_date = models.DateField(_("Hẹn liên hệ tiếp"), null=True, blank=True)

    created_at = models.DateTimeField(_("Lúc"), auto_now_add=True)

    class Meta:
        verbose_name = _("Lần liên hệ")
        verbose_name_plural = _("Lịch sử liên hệ")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["lead", "-created_at"]),
            models.Index(fields=["user", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.lead.name} · {self.created_at:%d/%m/%Y %H:%M}"


class LeadNote(models.Model):
    """Ghi chú nội bộ về lead (không phải nội dung khách yêu cầu)."""

    lead = models.ForeignKey(
        Lead,
        on_delete=models.CASCADE,
        related_name="staff_notes",
        verbose_name=_("Lead"),
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="lead_notes",
        verbose_name=_("Nhân viên"),
    )
    content = models.TextField(_("Nội dung"))
    created_at = models.DateTimeField(_("Lúc"), auto_now_add=True)

    class Meta:
        verbose_name = _("Ghi chú nội bộ")
        verbose_name_plural = _("Ghi chú nội bộ")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.lead.name} · {self.user_id} · {self.created_at:%d/%m/%Y %H:%M}"
