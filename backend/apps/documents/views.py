"""API hồ sơ cho HV PWA.

Endpoints:
- ``GET /api/student/documents/types`` — danh sách loại tài liệu cần upload.
- ``GET /api/student/persons/<id>/documents`` — list tài liệu của 1 person.
- ``POST /api/student/persons/<id>/documents`` — upload tài liệu cá nhân.
- ``GET /api/student/enrollments/<id>/documents`` — list tài liệu theo đơn.
- ``POST /api/student/enrollments/<id>/documents`` — upload tài liệu theo đơn.

Tất cả endpoint đều check IDOR:
- Person chỉ truy cập được nếu account đã link qua ``AccountPersonLink``.
- Enrollment chỉ truy cập được nếu ``student_phone == account.phone``.
"""
from __future__ import annotations

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.orders.models import Enrollment
from apps.students.authentication import StudentJWTAuthentication
from apps.students.models import AccountPersonLink, Person

from .models import (
    DocumentStatus,
    DocumentType,
    EnrollmentDocument,
    PersonDocument,
)
from .serializers import (
    DocumentTypeShortSerializer,
    EnrollmentDocumentSerializer,
    EnrollmentDocumentUploadSerializer,
    PersonDocumentSerializer,
    PersonDocumentUploadSerializer,
)


class StudentAuthMixin:
    authentication_classes = [StudentJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]


def _check_person_access(account, person_id: int) -> Person:
    """Trả Person nếu account có quyền, raise 404 nếu không (KHÔNG 403 để khỏi leak)."""
    person_ids = AccountPersonLink.objects.filter(account=account).values_list(
        "person_id", flat=True
    )
    return get_object_or_404(Person, pk=person_id, pk__in=list(person_ids))


def _check_enrollment_access(account, enrollment_id: int) -> Enrollment:
    return get_object_or_404(
        Enrollment, pk=enrollment_id, student_phone=account.phone
    )


class DocumentTypeListView(StudentAuthMixin, generics.ListAPIView):
    """List loại tài liệu — filter scope qua query ``?scope=person|enrollment``."""

    serializer_class = DocumentTypeShortSerializer

    def get_queryset(self):
        qs = DocumentType.objects.filter(is_active=True)
        scope = self.request.GET.get("scope")
        if scope in {"person", "enrollment"}:
            qs = qs.filter(scope=scope)
        return qs.order_by("scope", "sort_order", "name")


class PersonDocumentListUploadView(StudentAuthMixin, APIView):
    """GET list + POST upload cho 1 Person."""

    parser_classes = [MultiPartParser, FormParser]

    def get(self, request, person_id: int):
        person = _check_person_access(request.user.account, person_id)
        docs = (
            PersonDocument.objects
            .filter(person=person)
            .select_related("document_type", "reviewed_by")
            .order_by("-created_at")
        )
        return Response(
            PersonDocumentSerializer(docs, many=True, context={"request": request}).data
        )

    def post(self, request, person_id: int):
        person = _check_person_access(request.user.account, person_id)

        data = dict(request.data)
        data["person_id"] = person_id
        ser = PersonDocumentUploadSerializer(data={
            "person_id": person_id,
            "document_type_id": request.data.get("document_type_id"),
            "file": request.data.get("file"),
        })
        ser.is_valid(raise_exception=True)
        doc_type = get_object_or_404(
            DocumentType, pk=ser.validated_data["document_type_id"], is_active=True
        )
        if doc_type.scope != DocumentType.Scope.PERSON:
            return Response(
                {"detail": "Loại tài liệu này không thuộc phạm vi cá nhân."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        f = ser.validated_data["file"]
        mime = ser.validated_data["_detected_mime"]

        with transaction.atomic():
            # Vô hiệu các bản đang chờ duyệt trước đó cùng loại — chống stale
            PersonDocument.objects.filter(
                person=person,
                document_type=doc_type,
                status=DocumentStatus.PENDING_REVIEW,
            ).update(status=DocumentStatus.EXPIRED)

            doc = PersonDocument.objects.create(
                person=person,
                document_type=doc_type,
                file=f,
                mime_type=mime,
                file_size=f.size,
                uploaded_by_account=request.user.account,
            )
        return Response(
            PersonDocumentSerializer(doc, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class EnrollmentDocumentListUploadView(StudentAuthMixin, APIView):
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request, enrollment_id: int):
        enrollment = _check_enrollment_access(request.user.account, enrollment_id)
        docs = (
            EnrollmentDocument.objects
            .filter(enrollment=enrollment)
            .select_related("document_type", "reviewed_by")
            .order_by("-created_at")
        )
        return Response(
            EnrollmentDocumentSerializer(docs, many=True, context={"request": request}).data
        )

    def post(self, request, enrollment_id: int):
        enrollment = _check_enrollment_access(request.user.account, enrollment_id)

        ser = EnrollmentDocumentUploadSerializer(data={
            "enrollment_id": enrollment_id,
            "document_type_id": request.data.get("document_type_id"),
            "file": request.data.get("file"),
        })
        ser.is_valid(raise_exception=True)
        doc_type = get_object_or_404(
            DocumentType, pk=ser.validated_data["document_type_id"], is_active=True
        )
        if doc_type.scope != DocumentType.Scope.ENROLLMENT:
            return Response(
                {"detail": "Loại tài liệu này không thuộc phạm vi đơn ghi danh."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        f = ser.validated_data["file"]
        mime = ser.validated_data["_detected_mime"]

        with transaction.atomic():
            EnrollmentDocument.objects.filter(
                enrollment=enrollment,
                document_type=doc_type,
                status=DocumentStatus.PENDING_REVIEW,
            ).update(status=DocumentStatus.EXPIRED)

            doc = EnrollmentDocument.objects.create(
                enrollment=enrollment,
                document_type=doc_type,
                file=f,
                mime_type=mime,
                file_size=f.size,
                uploaded_by_account=request.user.account,
            )
        return Response(
            EnrollmentDocumentSerializer(doc, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )
