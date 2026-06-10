"""DRF serializers cho upload + dashboard hồ sơ."""
from __future__ import annotations

from rest_framework import serializers

from .models import (
    MAX_UPLOAD_SIZE,
    DocumentType,
    EnrollmentDocument,
    PersonDocument,
    validate_upload,
)


class DocumentTypeShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentType
        fields = ("id", "code", "name", "scope", "is_required", "description")


class PersonDocumentSerializer(serializers.ModelSerializer):
    document_type = DocumentTypeShortSerializer(read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = PersonDocument
        fields = (
            "id",
            "document_type",
            "file_url",
            "mime_type",
            "file_size",
            "status",
            "status_display",
            "review_note",
            "reviewed_at",
            "created_at",
            "expires_at",
        )
        read_only_fields = fields

    def get_file_url(self, obj: PersonDocument) -> str:
        if not obj.file:
            return ""
        request = self.context.get("request")
        url = obj.file.url
        return request.build_absolute_uri(url) if request else url


class EnrollmentDocumentSerializer(PersonDocumentSerializer):
    class Meta(PersonDocumentSerializer.Meta):
        model = EnrollmentDocument


class PersonDocumentUploadSerializer(serializers.Serializer):
    """Upload từ PWA."""

    person_id = serializers.IntegerField()
    document_type_id = serializers.IntegerField()
    file = serializers.FileField(max_length=500)

    def validate(self, attrs):
        f = attrs["file"]
        mime = validate_upload(f, max_size=MAX_UPLOAD_SIZE)
        attrs["_detected_mime"] = mime
        return attrs


class EnrollmentDocumentUploadSerializer(serializers.Serializer):
    enrollment_id = serializers.IntegerField()
    document_type_id = serializers.IntegerField()
    file = serializers.FileField(max_length=500)

    def validate(self, attrs):
        f = attrs["file"]
        mime = validate_upload(f, max_size=MAX_UPLOAD_SIZE)
        attrs["_detected_mime"] = mime
        return attrs
