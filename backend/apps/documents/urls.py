"""URL routing app documents."""
from django.urls import path

from .views import (
    DocumentFileServeView,
    DocumentTypeListView,
    EnrollmentDocumentListUploadView,
    PersonDocumentListUploadView,
)

urlpatterns = [
    path(
        "student/documents/types",
        DocumentTypeListView.as_view(),
        name="document-types",
    ),
    path(
        "student/persons/<int:person_id>/documents",
        PersonDocumentListUploadView.as_view(),
        name="person-documents",
    ),
    path(
        "student/enrollments/<int:enrollment_id>/documents",
        EnrollmentDocumentListUploadView.as_view(),
        name="enrollment-documents",
    ),
    # Serve byte stream file — JWT auth + IDOR + force-download.
    # KHÔNG bao giờ trả file qua /media/ trực tiếp.
    path(
        "student/documents/<str:kind>/<int:doc_id>/file",
        DocumentFileServeView.as_view(),
        name="document-file",
    ),
]
