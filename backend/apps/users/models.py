"""
Người dùng CRM = nhân viên trung tâm (admin/sale/kế toán/văn thư).

KHÔNG dùng `User` cho học viên. Học viên là `StudentAccount` riêng (app `students`),
định danh qua SĐT, không cần password.

Phân quyền theo `Group` (Django built-in). Xem [[crm-roles-flexible]] trong memory.
"""
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    """Cho phép create_user và create_superuser bằng username + password (chuẩn Django)."""

    def create_user(self, username: str, password: str | None = None, **extra_fields):
        if not username:
            raise ValueError("Username là bắt buộc.")
        username = username.lower().strip()
        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser phải có is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser phải có is_superuser=True.")
        return self.create_user(username, password, **extra_fields)


class User(AbstractUser):
    """Nhân viên trung tâm.

    - `username`: dùng đăng nhập admin CRM.
    - `phone`: số liên hệ nội bộ, có thể null lúc tạo, có thể đổi sau.
    - `full_name`: tên đầy đủ hiển thị (thay first/last name vốn không phù hợp tiếng Việt).
    """

    phone = models.CharField(
        _("Số điện thoại"),
        max_length=15,
        blank=True,
        default="",
        help_text=_("Định dạng: 0903456789"),
    )
    full_name = models.CharField(
        _("Họ và tên"),
        max_length=200,
        blank=True,
        default="",
    )
    job_title = models.CharField(
        _("Chức danh"),
        max_length=100,
        blank=True,
        default="",
        help_text=_("Ví dụ: Sale chính, Kế toán trưởng, Văn thư hồ sơ."),
    )
    avatar = models.ImageField(
        _("Ảnh đại diện"),
        upload_to="avatars/",
        blank=True,
        null=True,
    )
    is_active_in_pipeline = models.BooleanField(
        _("Đang phụ trách"),
        default=True,
        help_text=_(
            "Tắt khi nhân viên nghỉ phép dài hoặc đã nghỉ việc. "
            "Sale tắt sẽ không được phân lead tự động."
        ),
    )

    objects = UserManager()

    class Meta:
        verbose_name = _("Người dùng CRM")
        verbose_name_plural = _("Người dùng CRM")
        ordering = ["username"]

    def __str__(self) -> str:
        return self.full_name or self.username

    def get_display_name(self) -> str:
        return self.full_name or self.username

    def is_sale(self) -> bool:
        return self.groups.filter(name="sale").exists()

    def is_accountant(self) -> bool:
        return self.groups.filter(name="accountant").exists()

    def is_clerk(self) -> bool:
        return self.groups.filter(name="clerk").exists()

    def role_labels(self) -> list[str]:
        """Trả về list nhãn role tiếng Việt để hiển thị trên admin."""
        mapping = {
            "admin": "Quản trị",
            "sale": "Tư vấn viên",
            "accountant": "Kế toán",
            "clerk": "Văn thư",
        }
        return [mapping.get(g.name, g.name) for g in self.groups.all()]
