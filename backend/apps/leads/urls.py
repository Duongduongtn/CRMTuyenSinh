"""URL routing cho app leads."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import LeadCaptureView, LeadReasonViewSet, LeadViewSet

router = DefaultRouter()
router.register("admin/leads", LeadViewSet, basename="admin-lead")
router.register("admin/lead-reasons", LeadReasonViewSet, basename="lead-reason")
router.register("leads", LeadCaptureView, basename="lead-capture")

urlpatterns = [
    path("", include(router.urls)),
]
