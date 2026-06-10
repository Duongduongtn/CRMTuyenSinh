"""DRF serializers cho app payments."""
from rest_framework import serializers

from .models import CassoTransaction, Payment


class PaymentSerializer(serializers.ModelSerializer):
    method_display = serializers.CharField(source="get_method_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    enrollment_code = serializers.CharField(source="enrollment.code", read_only=True)
    student_name = serializers.CharField(source="enrollment.student_name", read_only=True)

    class Meta:
        model = Payment
        fields = [
            "id",
            "enrollment",
            "enrollment_code",
            "student_name",
            "amount",
            "method",
            "method_display",
            "status",
            "status_display",
            "bank_tx_id",
            "reference_code",
            "casso_transaction",
            "notes",
            "created_by",
            "confirmed_by",
            "confirmed_at",
            "created_at",
        ]
        read_only_fields = [
            "casso_transaction",
            "created_by",
            "confirmed_by",
            "confirmed_at",
            "created_at",
        ]


class CassoTransactionSerializer(serializers.ModelSerializer):
    matched_code_display = serializers.CharField(source="matched_code", read_only=True)
    matched_enrollment_code = serializers.CharField(
        source="matched_enrollment.code", read_only=True, default=""
    )

    class Meta:
        model = CassoTransaction
        fields = [
            "id",
            "tid",
            "casso_id",
            "description",
            "amount",
            "bank_brand_name",
            "bank_sub_acc_id",
            "when",
            "matched_code",
            "matched_code_display",
            "matched_enrollment",
            "matched_enrollment_code",
            "matched_at",
            "received_at",
        ]


class DepositQRSerializer(serializers.Serializer):
    """Output cho endpoint sinh QR đặt cọc."""

    qr_url = serializers.URLField()
    bank_code = serializers.CharField()
    account_number = serializers.CharField()
    account_name = serializers.CharField()
    amount = serializers.IntegerField()
    add_info = serializers.CharField()
