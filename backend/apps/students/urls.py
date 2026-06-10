"""URL routing app students — prefix `/api/student/`."""
from django.urls import path

from .views import (
    DeleteRequestView,
    EnrollmentDetailView,
    EnrollmentListView,
    MeView,
    PersonUpdateView,
    QuickEnrollmentView,
    refresh_token,
    request_otp,
    verify_otp,
)

urlpatterns = [
    path("student/auth/request-otp", request_otp, name="student-request-otp"),
    path("student/auth/verify-otp", verify_otp, name="student-verify-otp"),
    path("student/auth/refresh", refresh_token, name="student-refresh"),
    path("student/me", MeView.as_view(), name="student-me"),
    path("student/me/delete-request", DeleteRequestView.as_view(), name="student-delete-request"),
    path("student/enrollments", EnrollmentListView.as_view(), name="student-enrollment-list"),
    path("student/enrollments/<int:pk>", EnrollmentDetailView.as_view(), name="student-enrollment-detail"),
    path("student/persons/<int:pk>", PersonUpdateView.as_view(), name="student-person-update"),
    path("student/quick/<str:token>", QuickEnrollmentView.as_view(), name="student-quick-view"),
]
