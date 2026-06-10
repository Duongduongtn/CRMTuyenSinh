"""URL routing cho app courses (public FE)."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import PublicCourseViewSet

router = DefaultRouter()
router.register("public/courses", PublicCourseViewSet, basename="public-course")

urlpatterns = [
    path("", include(router.urls)),
]
