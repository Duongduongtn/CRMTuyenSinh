"""Views public cho app courses — FE Nuxt SSG gọi vào SSR build time."""
from rest_framework import viewsets
from rest_framework.permissions import AllowAny

from .models import Course
from .serializers import CourseDetailSerializer, CourseListSerializer


class PublicCourseViewSet(viewsets.ReadOnlyModelViewSet):
    """GET /api/public/courses + /api/public/courses/{slug} — public, không auth.

    Filter ``is_visible=True``. Order theo ``sort_order`` rồi ``title``.
    Phục vụ FE landing + trang chi tiết khóa. Cache-friendly (no auth, no session).
    """

    permission_classes = [AllowAny]
    lookup_field = "slug"

    def get_queryset(self):
        return Course.objects.filter(is_visible=True).order_by("sort_order", "title")

    def get_serializer_class(self):
        if self.action == "retrieve":
            return CourseDetailSerializer
        return CourseListSerializer
