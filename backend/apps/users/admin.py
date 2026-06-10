"""Admin CRM cho người dùng nội bộ. Tận dụng UserAdmin sẵn có, thêm trường tùy biến."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from unfold.admin import ModelAdmin
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm

    list_display = (
        "username",
        "full_name",
        "phone",
        "job_title",
        "groups_display",
        "is_active",
        "is_active_in_pipeline",
    )
    list_filter = ("is_active", "is_active_in_pipeline", "groups", "is_superuser")
    search_fields = ("username", "full_name", "phone", "email")

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (
            "Thông tin cá nhân",
            {"fields": ("full_name", "phone", "email", "job_title", "avatar")},
        ),
        (
            "Quyền hạn",
            {
                "fields": (
                    "is_active",
                    "is_active_in_pipeline",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
                "description": (
                    "Một người dùng có thể thuộc nhiều nhóm. Ví dụ: vừa Sale vừa Kế toán. "
                    "Nhóm chuẩn: sale (tư vấn), accountant (kế toán), clerk (văn thư), admin (quản trị)."
                ),
            },
        ),
        ("Mốc thời gian", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "full_name",
                    "phone",
                    "email",
                    "password1",
                    "password2",
                    "groups",
                ),
            },
        ),
    )

    def groups_display(self, obj: User) -> str:
        return ", ".join(obj.role_labels()) or "(chưa gán)"

    groups_display.short_description = "Vai trò"
