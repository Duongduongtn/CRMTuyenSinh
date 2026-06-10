"""DRF serializers cho app courses — public FE Nuxt."""
from rest_framework import serializers

from .models import Course


class CourseListSerializer(serializers.ModelSerializer):
    """List courses cho FE — gọn, dùng cho card."""

    vehicle_group_display = serializers.CharField(
        source="get_vehicle_group_display", read_only=True
    )
    vehicle_class_display = serializers.CharField(
        source="get_vehicle_class_display", read_only=True
    )
    cover_image_url = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            "id",
            "slug",
            "title",
            "vehicle_class",
            "vehicle_class_display",
            "vehicle_group",
            "vehicle_group_display",
            "short_description",
            "tuition_fee",
            "deposit_amount",
            "duration_display",
            "duration_days",
            "cover_image_url",
            "is_featured",
            "sort_order",
        ]

    def get_cover_image_url(self, obj: Course) -> str:
        if not obj.cover_image:
            return ""
        request = self.context.get("request")
        url = obj.cover_image.url
        if request is not None:
            return request.build_absolute_uri(url)
        return url


class CourseDetailSerializer(CourseListSerializer):
    """Detail cho trang /khoa-hoc/[slug] — thêm description_md + SEO meta + OG."""

    og_image_url = serializers.SerializerMethodField()

    class Meta(CourseListSerializer.Meta):
        fields = CourseListSerializer.Meta.fields + [
            "description_md",
            "meta_title",
            "meta_description",
            "og_image_url",
            "total_slots",
            "available_slots",
            "updated_at",
        ]

    def get_og_image_url(self, obj: Course) -> str:
        if not obj.og_image:
            return ""
        request = self.context.get("request")
        url = obj.og_image.url
        if request is not None:
            return request.build_absolute_uri(url)
        return url
