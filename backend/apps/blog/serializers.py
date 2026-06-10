"""Serializers public cho blog FE Nuxt."""
from rest_framework import serializers

from .models import BlogCategory, BlogPost


class BlogCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = BlogCategory
        fields = ("id", "slug", "name", "description", "sort_order")


class BlogPostListSerializer(serializers.ModelSerializer):
    """Card item — không trả content_md để tiết kiệm payload."""

    category = BlogCategorySerializer(read_only=True)
    cover_image_url = serializers.SerializerMethodField()

    class Meta:
        model = BlogPost
        fields = (
            "id",
            "slug",
            "title",
            "excerpt",
            "category",
            "cover_image_url",
            "cover_alt",
            "published_at",
            "read_time_minutes",
            "is_featured",
            "view_count",
        )

    def get_cover_image_url(self, obj: BlogPost) -> str:
        if not obj.cover_image:
            return ""
        request = self.context.get("request")
        url = obj.cover_image.url
        return request.build_absolute_uri(url) if request else url


class BlogPostDetailSerializer(BlogPostListSerializer):
    og_image_url = serializers.SerializerMethodField()

    class Meta(BlogPostListSerializer.Meta):
        fields = BlogPostListSerializer.Meta.fields + (
            "content_md",
            "meta_title",
            "meta_description",
            "og_image_url",
            "canonical_url",
            "updated_at",
        )

    def get_og_image_url(self, obj: BlogPost) -> str:
        if not obj.og_image:
            return ""
        request = self.context.get("request")
        url = obj.og_image.url
        return request.build_absolute_uri(url) if request else url
