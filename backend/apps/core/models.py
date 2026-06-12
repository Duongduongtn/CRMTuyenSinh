"""
App `core` — chứa 3 model chính:

- `SiteSettings` (singleton): toàn bộ brand info cho phép admin chỉnh trên CRM
  thay cho việc hard-code (tên trung tâm, logo, hotline, địa chỉ, social, SEO meta).
- `SystemSetting` (key-value): config kỹ thuật (Casso webhook secret, version flag, etc.)
  có thể cần đổi mà không cần redeploy.
- `AuditLog`: ghi nhận thao tác quan trọng (tạo/sửa/xóa, xem dữ liệu nhạy cảm).
"""
from django.db import models
from django.utils.translation import gettext_lazy as _

from solo.models import SingletonModel


class SiteSettings(SingletonModel):
    """Brand info hiển thị trên FE public + PWA + CRM, chỉnh trong admin."""

    # Tên thương hiệu
    brand_name = models.CharField(
        _("Tên trung tâm"),
        max_length=200,
        default="Trung tâm Đào tạo Lái xe",
        help_text=_("Tên đầy đủ, hiển thị trên header, footer, email, hóa đơn."),
    )
    brand_short_name = models.CharField(
        _("Tên viết tắt"),
        max_length=20,
        default="ĐA",
        help_text=_("2-3 ký tự, dùng cho logo text khi chưa có ảnh logo. VD: ĐA, ABC."),
    )
    slogan = models.CharField(
        _("Slogan"),
        max_length=255,
        blank=True,
        default="Học lái xe an toàn, đúng lộ trình.",
    )
    description = models.TextField(
        _("Mô tả ngắn"),
        blank=True,
        help_text=_("2-3 câu mô tả trung tâm, dùng cho meta description mặc định."),
    )

    # Hình ảnh
    logo = models.ImageField(
        _("Logo"),
        upload_to="brand/",
        blank=True,
        null=True,
        help_text=_("PNG/SVG, transparent bg, kích thước tối thiểu 512x512."),
    )
    favicon = models.ImageField(
        _("Favicon"),
        upload_to="brand/",
        blank=True,
        null=True,
        help_text=_("ICO/PNG 32x32 hoặc 64x64."),
    )
    og_image = models.ImageField(
        _("Ảnh chia sẻ mạng xã hội"),
        upload_to="brand/",
        blank=True,
        null=True,
        help_text=_("1200x630, dùng cho Open Graph khi share Facebook/Zalo."),
    )

    # Liên hệ
    hotline = models.CharField(
        _("Hotline"),
        max_length=20,
        default="0900000000",
        help_text=_("Định dạng máy: 0903456789 (không dấu chấm, không khoảng trắng)."),
    )
    hotline_display = models.CharField(
        _("Hotline hiển thị"),
        max_length=30,
        default="0900.000.000",
        help_text=_("Định dạng đẹp cho UI: 0903.456.789"),
    )
    email = models.EmailField(_("Email"), default="info@example.vn")

    # Địa chỉ
    address_line = models.CharField(
        _("Địa chỉ"),
        max_length=255,
        default="Đồng Xoài, Bình Phước",
    )
    ward = models.CharField(_("Phường/Xã"), max_length=100, blank=True)
    district = models.CharField(_("Quận/Huyện"), max_length=100, blank=True)
    city = models.CharField(_("Tỉnh/Thành phố"), max_length=100, blank=True, default="Bình Phước")
    map_lat = models.DecimalField(_("Vĩ độ"), max_digits=10, decimal_places=7, null=True, blank=True)
    map_lng = models.DecimalField(_("Kinh độ"), max_digits=10, decimal_places=7, null=True, blank=True)
    map_embed_url = models.URLField(
        _("Google Map embed URL"),
        max_length=500,
        blank=True,
        help_text=_("Vào Google Maps → Share → Embed a map → copy src của iframe vào đây."),
    )

    # Giờ làm việc
    working_hours_text = models.CharField(
        _("Giờ làm việc"),
        max_length=255,
        default="T2 đến T7: 7:30 đến 18:00. Chủ nhật: 8:00 đến 12:00",
    )

    # Social
    facebook_url = models.URLField(_("Facebook"), blank=True)
    zalo_oa_id = models.CharField(_("Zalo OA ID"), max_length=100, blank=True)
    zalo_url = models.URLField(_("Zalo OA URL"), blank=True)
    youtube_url = models.URLField(_("YouTube"), blank=True)
    tiktok_url = models.URLField(_("TikTok"), blank=True)

    # Ngân hàng nhận đặt cọc (dùng cho VietQR generator)
    bank_code = models.CharField(
        _("Mã ngân hàng (VietQR)"),
        max_length=20,
        blank=True,
        default="BIDV",
        help_text=_("Mã chuẩn NAPAS: BIDV, VCB, TCB, VPB, MB, ACB... Xem napas.com.vn."),
    )
    bank_account_number = models.CharField(
        _("Số tài khoản nhận"),
        max_length=30,
        blank=True,
        default="",
        help_text=_("TK liên kết với Casso để nhận chuyển khoản đặt cọc."),
    )
    bank_account_name = models.CharField(
        _("Tên chủ TK"),
        max_length=200,
        blank=True,
        default="",
        help_text=_("Viết hoa không dấu, đúng tên trên CMND chủ tài khoản."),
    )

    # Pháp lý
    license_info = models.CharField(
        _("Giấy phép"),
        max_length=255,
        blank=True,
        default="Giấy phép số ABC/SGTVT do Sở GTVT cấp",
    )
    company_full_name = models.CharField(
        _("Tên đầy đủ pháp nhân"),
        max_length=255,
        blank=True,
        help_text=_("Tên ghi trên hóa đơn, hợp đồng. Có thể khác Tên trung tâm."),
    )
    tax_code = models.CharField(_("Mã số thuế"), max_length=20, blank=True)

    # SEO mặc định
    meta_title_default = models.CharField(
        _("Tiêu đề SEO mặc định"),
        max_length=70,
        blank=True,
    )
    meta_description_default = models.CharField(
        _("Mô tả SEO mặc định"),
        max_length=170,
        blank=True,
    )

    # Stats hiển thị FE (cấu hình tay, không tự đếm)
    stat_students_count = models.PositiveIntegerField(
        _("Số học viên đã đỗ (hiển thị)"),
        default=10000,
        help_text=_("Hiển thị ở trust strip. Cập nhật định kỳ thủ công."),
    )
    stat_pass_rate_percent = models.PositiveSmallIntegerField(
        _("Tỉ lệ đỗ lần đầu (%)"),
        default=89,
    )
    stat_years_experience = models.PositiveSmallIntegerField(
        _("Số năm kinh nghiệm"),
        default=12,
    )
    stat_practice_area_m2 = models.PositiveIntegerField(
        _("Sân tập (m²)"),
        default=8000,
    )

    class Meta:
        verbose_name = _("Thông tin trung tâm")
        verbose_name_plural = _("Thông tin trung tâm")

    def __str__(self) -> str:
        return self.brand_name


class SystemSetting(models.Model):
    """Key-value cho config kỹ thuật không thuộc brand (toggle feature, flag, version)."""

    key = models.SlugField(_("Khóa"), max_length=100, unique=True)
    value = models.JSONField(_("Giá trị"), blank=True, null=True)
    description = models.CharField(_("Mô tả"), max_length=255, blank=True)
    is_active = models.BooleanField(_("Đang dùng"), default=True)
    created_at = models.DateTimeField(_("Tạo lúc"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Cập nhật"), auto_now=True)

    class Meta:
        verbose_name = _("Cấu hình hệ thống")
        verbose_name_plural = _("Cấu hình hệ thống")
        ordering = ["key"]

    def __str__(self) -> str:
        return self.key


class IntegrationCredential(models.Model):
    """Lưu credential tích hợp ngoài (Casso + FB Lead Ads) mã hóa Fernet.

    User paste key qua UI CRM SPA `/admin/integrations`, KHÔNG cần SSH `nano
    .env.prod`. Backend đọc qua `apps.core.integrations.get_credential()` với
    cache 60s. Fallback `settings.<NAME>` nếu DB chưa có (boot đầu, hoặc rỗng).

    Provider + key tổ hợp duy nhất. Khoá Fernet ở `settings.FERNET_SECRET`.

    Scope chốt 2026-06-11 (gói A) — bỏ ZNS Zalo + SMTP khỏi MVP, choices còn
    Casso + FB. Cụm B (2026-06-12) chính thức loại Provider.ZNS/Provider.SMTP
    khỏi enum + xóa orphan record qua management command
    ``cleanup_deprecated_integrations`` (xem [[integration-keys-ui]]).
    """

    class Provider(models.TextChoices):
        CASSO = "casso", _("Casso (đối soát QR)")
        FB = "fb", _("Facebook Lead Ads")

    provider = models.CharField(
        _("Tích hợp"),
        max_length=20,
        choices=Provider.choices,
    )
    key = models.CharField(
        _("Khóa"),
        max_length=80,
        help_text=_("Tên khóa: webhook_secret, api_key, access_token, ..."),
    )
    value_encrypted = models.BinaryField(
        _("Giá trị (mã hóa Fernet)"),
        blank=True,
        default=b"",
        help_text=_("KHÔNG đọc trực tiếp — dùng .get_value()."),
    )
    description = models.CharField(
        _("Ghi chú"),
        max_length=255,
        blank=True,
    )
    updated_at = models.DateTimeField(_("Cập nhật lúc"), auto_now=True)
    updated_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("Cập nhật bởi"),
    )

    class Meta:
        verbose_name = _("Khóa tích hợp")
        verbose_name_plural = _("Khóa tích hợp")
        ordering = ["provider", "key"]
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "key"],
                name="integration_credential_provider_key_unique",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.get_provider_display()} · {self.key}"

    def set_value(self, plaintext: str) -> None:
        """Encrypt + lưu. Empty → xóa value (không re-encrypt)."""
        from .crypto import encrypt_str

        self.value_encrypted = encrypt_str(plaintext or "")

    def get_value(self) -> str:
        """Decrypt → plaintext. Empty hoặc decrypt fail → "" (caller fallback)."""
        from .crypto import decrypt_to_str

        return decrypt_to_str(bytes(self.value_encrypted) if self.value_encrypted else b"")

    @property
    def masked(self) -> str:
        """Hiển thị an toàn cho UI: '****abcd' (4 ký tự cuối). Empty → ''."""
        v = self.get_value()
        if not v:
            return ""
        if len(v) <= 4:
            return "****"
        return "****" + v[-4:]


class AuditLog(models.Model):
    """Ghi nhận action quan trọng để truy vết. Nhẹ, không thay thế logging."""

    class Action(models.TextChoices):
        CREATE = "create", _("Tạo")
        UPDATE = "update", _("Cập nhật")
        DELETE = "delete", _("Xóa")
        VIEW_SENSITIVE = "view_sensitive", _("Xem dữ liệu nhạy cảm")
        LOGIN = "login", _("Đăng nhập")
        LOGIN_FAILED = "login_failed", _("Đăng nhập thất bại")
        LOGOUT = "logout", _("Đăng xuất")
        PERMISSION_CHANGE = "permission_change", _("Đổi quyền")
        SUSPICIOUS_FIELD = "suspicious_field", _("Trường khả nghi bị từ chối")

    user = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
        verbose_name=_("Người thực hiện"),
    )
    action = models.CharField(_("Hành động"), max_length=30, choices=Action.choices)
    target_model = models.CharField(_("Model"), max_length=100, blank=True)
    target_id = models.CharField(_("ID đối tượng"), max_length=100, blank=True)
    changes = models.JSONField(_("Thay đổi"), blank=True, null=True)
    ip_address = models.GenericIPAddressField(_("IP"), null=True, blank=True)
    user_agent = models.CharField(_("User agent"), max_length=255, blank=True)
    created_at = models.DateTimeField(_("Lúc"), auto_now_add=True)

    class Meta:
        verbose_name = _("Audit log")
        verbose_name_plural = _("Audit log")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["-created_at"]),
            models.Index(fields=["target_model", "target_id"]),
            models.Index(fields=["user", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.get_action_display()} · {self.target_model}#{self.target_id} · {self.created_at:%d/%m/%Y %H:%M}"
