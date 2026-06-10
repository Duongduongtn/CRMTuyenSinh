"""URL routing cho app orders."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import EnrollmentPublicView, EnrollmentViewSet, LeadConvertView

router = DefaultRouter()
router.register("admin/enrollments", EnrollmentViewSet, basename="admin-enrollment")

urlpatterns = [
    path("", include(router.urls)),
    path(
        "admin/leads/<int:lead_id>/convert",
        LeadConvertView.as_view(),
        name="lead-convert",
    ),
    path(
        "public/enrollments/by-token/<uuid:token>",
        EnrollmentPublicView.as_view(),
        name="enrollment-public",
    ),
]
