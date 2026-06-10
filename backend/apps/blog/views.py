"""Public API blog cho FE Nuxt."""
from django.db.models import F
from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import BlogCategory, BlogPost, BlogPostStatus
from .serializers import (
    BlogCategorySerializer,
    BlogPostDetailSerializer,
    BlogPostListSerializer,
)


class PublicBlogCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    serializer_class = BlogCategorySerializer
    lookup_field = "slug"

    def get_queryset(self):
        return BlogCategory.objects.filter(is_active=True).order_by("sort_order", "name")


class PublicBlogPostViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    lookup_field = "slug"
    filterset_fields = ["category__slug", "is_featured"]
    search_fields = ["title", "excerpt"]
    ordering_fields = ["published_at", "view_count"]
    ordering = ["-published_at"]

    def get_queryset(self):
        return (
            BlogPost.objects
            .filter(status=BlogPostStatus.PUBLISHED)
            .select_related("category", "author")
            .order_by("-published_at")
        )

    def get_serializer_class(self):
        return BlogPostDetailSerializer if self.action == "retrieve" else BlogPostListSerializer

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        BlogPost.objects.filter(pk=instance.pk).update(view_count=F("view_count") + 1)
        return Response(self.get_serializer(instance).data)
