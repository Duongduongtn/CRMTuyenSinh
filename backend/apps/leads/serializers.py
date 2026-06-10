"""DRF serializers cho lead."""
from rest_framework import serializers

from apps.courses.models import VehicleClass

from .models import Lead, LeadContact, LeadReason


class LeadCaptureSerializer(serializers.ModelSerializer):
    """Public endpoint capture lead từ FE form. Chỉ field user nhập + honeypot."""

    # Honeypot — bot sẽ điền, người thật sẽ để trống
    website = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Lead
        fields = [
            "name",
            "phone",
            "email",
            "district",
            "vehicle_class",
            "notes",
            # tracking (FE tự gửi)
            "source",
            "source_page",
            "source_title",
            "utm_source",
            "utm_medium",
            "utm_campaign",
            "utm_content",
            "utm_term",
            "device_type",
            "device_os",
            "device_browser",
            "screen_size",
            # honeypot
            "website",
        ]
        extra_kwargs = {
            "email": {"required": False, "allow_blank": True},
            "district": {"required": False, "allow_blank": True},
            "vehicle_class": {"required": False, "allow_blank": True},
            "notes": {"required": False, "allow_blank": True},
            "source": {"required": False},
            "source_page": {"required": False, "allow_blank": True},
            "source_title": {"required": False, "allow_blank": True},
            "utm_source": {"required": False, "allow_blank": True},
            "utm_medium": {"required": False, "allow_blank": True},
            "utm_campaign": {"required": False, "allow_blank": True},
            "utm_content": {"required": False, "allow_blank": True},
            "utm_term": {"required": False, "allow_blank": True},
            "device_type": {"required": False, "allow_blank": True},
            "device_os": {"required": False, "allow_blank": True},
            "device_browser": {"required": False, "allow_blank": True},
            "screen_size": {"required": False, "allow_blank": True},
        }

    def validate_phone(self, value: str) -> str:
        # Strip ký tự không phải số
        cleaned = "".join(c for c in value if c.isdigit())
        if not cleaned.startswith("0") or len(cleaned) != 10:
            raise serializers.ValidationError(
                "Số điện thoại không hợp lệ. Định dạng đúng: 0xxxxxxxxx (10 số)."
            )
        return cleaned

    def validate_name(self, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise serializers.ValidationError("Họ tên quá ngắn.")
        return value

    def validate_vehicle_class(self, value: str) -> str:
        if value and value not in VehicleClass.values:
            raise serializers.ValidationError(f"Hạng GPLX không hợp lệ. Phải thuộc {VehicleClass.values}.")
        return value

    def validate_website(self, value: str) -> str:
        # Honeypot: nếu có nội dung → spam bot
        if value:
            raise serializers.ValidationError("Spam detected.")
        return value

    def create(self, validated_data):
        validated_data.pop("website", None)  # remove honeypot
        # IP và user-agent set từ view qua context
        request = self.context.get("request")
        if request:
            validated_data["ip_address"] = self._get_client_ip(request)
            validated_data["user_agent"] = request.META.get("HTTP_USER_AGENT", "")[:500]
        return super().create(validated_data)

    @staticmethod
    def _get_client_ip(request) -> str | None:
        # Xét X-Forwarded-For nếu có (sau Cloudflare/nginx)
        xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if xff:
            return xff.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")


class LeadReasonSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeadReason
        fields = ["id", "name", "status_scope", "sort_order"]


class LeadContactSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.get_display_name", read_only=True)
    reason_name = serializers.CharField(source="reason.name", read_only=True, default="")

    class Meta:
        model = LeadContact
        fields = [
            "id",
            "lead",
            "user",
            "user_name",
            "contact_type",
            "status_before",
            "status_after",
            "priority_after",
            "reason",
            "reason_name",
            "reason_text",
            "note",
            "next_contact_date",
            "created_at",
        ]
        read_only_fields = ["status_before", "user", "created_at"]


class LeadListSerializer(serializers.ModelSerializer):
    """List view: gọn, không có history."""

    assigned_to_name = serializers.CharField(source="assigned_to.get_display_name", read_only=True, default="")

    class Meta:
        model = Lead
        fields = [
            "id",
            "name",
            "phone",
            "vehicle_class",
            "status",
            "priority",
            "assigned_to",
            "assigned_to_name",
            "contact_count",
            "last_contact_at",
            "next_contact_date",
            "source",
            "created_at",
        ]


class LeadDetailSerializer(serializers.ModelSerializer):
    """Detail view: đầy đủ."""

    assigned_to_name = serializers.CharField(source="assigned_to.get_display_name", read_only=True, default="")
    reason_name = serializers.CharField(source="reason.name", read_only=True, default="")
    contacts = LeadContactSerializer(many=True, read_only=True)

    class Meta:
        model = Lead
        fields = "__all__"
