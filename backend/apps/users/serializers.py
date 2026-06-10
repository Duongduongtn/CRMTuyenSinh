"""Serializer cho user CRM — dùng cho endpoint /api/auth/me."""
from rest_framework import serializers

from .models import User


class UserMeSerializer(serializers.ModelSerializer):
    """Trả về thông tin user đang đăng nhập + groups (slug) + role labels VN.

    FE Vue SPA dùng để render top bar, gate menu theo group, hiển thị tên.
    """

    display_name = serializers.CharField(source="get_display_name", read_only=True)
    avatar_url = serializers.SerializerMethodField()
    groups = serializers.SerializerMethodField()
    role_labels = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "full_name",
            "display_name",
            "email",
            "phone",
            "job_title",
            "avatar_url",
            "is_superuser",
            "is_staff",
            "groups",
            "role_labels",
            "permissions",
        ]

    def get_avatar_url(self, obj: User) -> str | None:
        if not obj.avatar:
            return None
        request = self.context.get("request")
        url = obj.avatar.url
        return request.build_absolute_uri(url) if request else url

    def get_groups(self, obj: User) -> list[str]:
        return list(obj.groups.values_list("name", flat=True))

    def get_role_labels(self, obj: User) -> list[str]:
        return obj.role_labels()

    def get_permissions(self, obj: User) -> list[str]:
        # Superuser: trả lại all_perms để FE đơn giản hoá UI gate
        if obj.is_superuser:
            return ["*"]
        # Trả về set permission codenames dạng app_label.codename
        return sorted(obj.get_all_permissions())


class LoginSerializer(serializers.Serializer):
    """Validate input login. KHÔNG dùng ModelSerializer để tránh leak password."""

    username = serializers.CharField(max_length=150, trim_whitespace=True)
    password = serializers.CharField(max_length=200, write_only=True, trim_whitespace=False)

    def validate_username(self, value: str) -> str:
        return value.lower().strip()
