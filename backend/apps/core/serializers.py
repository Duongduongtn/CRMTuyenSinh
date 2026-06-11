"""DRF serializers cho app core, SiteSettings public cho FE."""
from django.conf import settings as django_settings
from rest_framework import serializers

from .models import SiteSettings


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
