"""DRF serializers cho app core: SiteSettings public + admin + IntegrationCredential admin."""
from django.conf import settings as django_settings
from rest_framework import serializers

from .integrations import INTEGRATION_SCHEMA
from .models import IntegrationCredential, SiteSettings

# Field text/number admin có thể PATCH qua API JSON. ẢNH (logo/favicon/og_image)
# chỉnh trong Django admin tới khi build upload UI → không cho PATCH ở đây để
# tránh phải hỗ trợ multipart. Read-only trả URL để FE hiển thị thumbnail.
SITE_SETTINGS_ADMIN_EDITABLE_FIELDS = (
    # Thương hiệu
    "brand_name",
    "brand_short_name",
    "slogan",
    "description",
    # Liên hệ
    "hotline",
    "hotline_display",
    "email",
    "address_line",
    "ward",
    "district",
    "city",
    "map_lat",
    "map_lng",
    "map_embed_url",
    "working_hours_text",
    # Mạng xã hội
    "facebook_url",
    "zalo_oa_id",
    "zalo_url",
    "youtube_url",
    "tiktok_url",
    # Ngân hàng nhận đặt cọc
    "bank_code",
    "bank_account_number",
    "bank_account_name",
    # Pháp lý
    "license_info",
    "company_full_name",
    "tax_code",
    # SEO mặc định
    "meta_title_default",
    "meta_description_default",
    # Stats hiển thị
    "stat_students_count",
    "stat_pass_rate_percent",
    "stat_years_experience",
    "stat_practice_area_m2",
)


class SiteSettingsPublicSerializer(serializers.ModelSerializer):
    """Brand + contact + SEO mặc định cho FE Nuxt + FE CRM + PWA học viên.

    KHÔNG expose: bank info, casso webhook, tax code, license nội bộ.
    """

    logo_url = serializers.SerializerMethodField()
    favicon_url = serializers.SerializerMethodField()
    og_image_url = serializers.SerializerMethodField()
    address_full = serializers.SerializerMethodField()
    student_url = serializers.SerializerMethodField()

    class Meta:
        model = SiteSettings
        fields = [
            "brand_name",
            "brand_short_name",
            "slogan",
            "description",
            "logo_url",
            "favicon_url",
            "og_image_url",
            "hotline",
            "hotline_display",
            "email",
            "address_line",
            "ward",
            "district",
            "city",
            "address_full",
            "map_embed_url",
            "map_lat",
            "map_lng",
            "working_hours_text",
            "facebook_url",
            "zalo_oa_id",
            "zalo_url",
            "youtube_url",
            "tiktok_url",
            "license_info",
            "meta_title_default",
            "meta_description_default",
            "stat_students_count",
            "stat_pass_rate_percent",
            "stat_years_experience",
            "stat_practice_area_m2",
            "student_url",
        ]

    def _absolute(self, field) -> str:
        if not field:
            return ""
        request = self.context.get("request")
        url = field.url
        if request is not None:
            return request.build_absolute_uri(url)
        return url

    def get_logo_url(self, obj):
        return self._absolute(obj.logo)

    def get_favicon_url(self, obj):
        return self._absolute(obj.favicon)

    def get_og_image_url(self, obj):
        return self._absolute(obj.og_image)

    def get_address_full(self, obj) -> str:
        parts = [obj.address_line, obj.ward, obj.district, obj.city]
        return ", ".join(p for p in parts if p)

    def get_student_url(self, _obj) -> str:
        # FE cần URL trỏ PWA học viên. Đọc từ env SITE_STUDENT_URL để không hardcode subdomain.
        return getattr(django_settings, "SITE_STUDENT_URL", "")


class SiteSettingsAdminSerializer(serializers.ModelSerializer):
    """Full SiteSettings dùng cho UI admin SPA `/admin/settings`.

    GET trả toàn bộ field text/number + URL ảnh (read-only). PATCH hỗ trợ partial
    update cho các field text/number trong `SITE_SETTINGS_ADMIN_EDITABLE_FIELDS`.
    Ảnh (logo/favicon/og_image) chỉ chỉnh qua Django admin tới khi build UI upload.
    """

    logo_url = serializers.SerializerMethodField()
    favicon_url = serializers.SerializerMethodField()
    og_image_url = serializers.SerializerMethodField()

    class Meta:
        model = SiteSettings
        fields = (
            *SITE_SETTINGS_ADMIN_EDITABLE_FIELDS,
            "logo_url",
            "favicon_url",
            "og_image_url",
        )

    def _absolute(self, field) -> str:
        if not field:
            return ""
        request = self.context.get("request")
        url = field.url
        if request is not None:
            return request.build_absolute_uri(url)
        return url

    def get_logo_url(self, obj) -> str:
        return self._absolute(obj.logo)

    def get_favicon_url(self, obj) -> str:
        return self._absolute(obj.favicon)

    def get_og_image_url(self, obj) -> str:
        return self._absolute(obj.og_image)

    def validate_map_embed_url(self, value: str) -> str:
        """Chỉ chấp nhận URL từ Google Maps để chống superuser bị compromise
        paste URL phishing vào iframe map của FE public.

        Empty OK (cho phép xóa URL). Khác Google domain → 400.
        """
        if not value:
            return value
        from urllib.parse import urlparse

        try:
            parsed = urlparse(value)
        except ValueError as exc:
            raise serializers.ValidationError(
                "URL không hợp lệ."
            ) from exc

        allowed_hosts = {
            "www.google.com",
            "maps.google.com",
            "google.com",
        }
        if parsed.scheme != "https" or parsed.hostname not in allowed_hosts:
            raise serializers.ValidationError(
                "Chỉ chấp nhận URL embed từ Google Maps (https://www.google.com/maps/embed/...)."
            )
        if not parsed.path.startswith("/maps/embed"):
            raise serializers.ValidationError(
                "Phải là đường dẫn /maps/embed của Google Maps."
            )
        return value


class IntegrationCredentialItemSerializer(serializers.Serializer):
    """1 entry cho UI: schema metadata + value masked + updated_at.

    Dùng cho `GET /api/admin/integrations/`. Read-only, không expose plaintext.
    """

    key = serializers.CharField()
    label = serializers.CharField()
    sensitive = serializers.BooleanField()
    help_text = serializers.CharField()
    masked = serializers.CharField(allow_blank=True)
    has_value = serializers.BooleanField()
    source = serializers.CharField(help_text="db | env | empty")
    updated_at = serializers.DateTimeField(allow_null=True)
    updated_by_username = serializers.CharField(allow_blank=True)


class IntegrationProviderUpdateSerializer(serializers.Serializer):
    """Validate body PUT `/api/admin/integrations/{provider}/`.

    Accept dict {key: plaintext_value}. Chỉ key thuộc schema được xử lý.
    Value rỗng = clear credential (xóa khỏi DB, fallback ENV).
    """

    def __init__(self, *args, provider: str = "", **kwargs):
        self._provider = provider
        super().__init__(*args, **kwargs)

    def validate(self, attrs):
        schema = INTEGRATION_SCHEMA.get(self._provider)
        if not schema:
            raise serializers.ValidationError(f"Provider không hợp lệ: {self._provider}")

        raw = self.initial_data
        if not isinstance(raw, dict):
            raise serializers.ValidationError("Body phải là JSON object.")

        # Chỉ giữ key thuộc schema, bỏ qua key lạ (không raise để FE gửi extra field
        # cũng không vỡ).
        cleaned: dict[str, str] = {}
        for key, value in raw.items():
            if key not in schema:
                continue
            if value is None:
                value = ""
            if not isinstance(value, (str, int)):
                raise serializers.ValidationError({key: "Giá trị phải là chuỗi."})
            cleaned[key] = str(value).strip()

        if not cleaned:
            raise serializers.ValidationError("Không có key nào hợp lệ trong body.")

        attrs["_cleaned"] = cleaned
        return attrs


class IntegrationCredentialAdminListSerializer(serializers.ModelSerializer):
    """Django admin / debug — KHÔNG dùng cho FE SPA (FE dùng item serializer)."""

    masked = serializers.CharField(read_only=True)

    class Meta:
        model = IntegrationCredential
        fields = ["id", "provider", "key", "masked", "description", "updated_at", "updated_by"]
        read_only_fields = fields
