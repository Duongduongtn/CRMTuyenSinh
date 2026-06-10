"""Admin cho app payments (django-unfold)."""
from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin

from .models import CassoTransaction, Payment, PaymentStatus


@admin.register(Payment)
class PaymentAdmin(ModelAdmin):
    list_display = (
        "created_at",
        "enrollment",
        "amount_fmt",
        "method",
        "status_badge",
        "bank_tx_id",
        "created_by",
        "confirmed_by",
    )
    list_filter = ("status", "method")
    search_fields = (
        "enrollment__code",
        "enrollment__student_name",
        "bank_tx_id",
        "reference_code",
    )
    date_hierarchy = "created_at"
    autocomplete_fields = ("enrollment", "casso_transaction", "created_by", "confirmed_by")
    readonly_fields = ("casso_transaction", "created_at", "confirmed_at")

    @admin.display(description="Số tiền", ordering="amount")
    def amount_fmt(self, obj: Payment) -> str:
        return f"{int(obj.amount):,}".replace(",", ".") + " đ"

    @admin.display(description="Trạng thái", ordering="status")
    def status_badge(self, obj: Payment) -> str:
        colors = {
            PaymentStatus.PENDING: ("#F59E0B", "Chờ"),
            PaymentStatus.CONFIRMED: ("#15803D", "Đã xác nhận"),
            PaymentStatus.FAILED: ("#B91C1C", "Thất bại"),
            PaymentStatus.REFUNDED: ("#7C3AED", "Đã hoàn"),
        }
        color, label = colors.get(obj.status, ("#000", obj.status))
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;'
            'border-radius:4px;font-size:11px;font-weight:600;">{}</span>',
            color,
            label,
        )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("enrollment", "created_by", "confirmed_by")
        )


@admin.register(CassoTransaction)
class CassoTransactionAdmin(ModelAdmin):
    list_display = (
        "received_at",
        "tid",
        "amount_fmt",
        "bank_brand_name",
        "matched_code",
        "matched_enrollment",
    )
    list_filter = ("bank_brand_name",)
    search_fields = ("tid", "description", "matched_code")
    date_hierarchy = "received_at"
    autocomplete_fields = ("matched_enrollment",)
    readonly_fields = (
        "tid",
        "casso_id",
        "description",
        "amount",
        "bank_brand_name",
        "bank_sub_acc_id",
        "when",
        "matched_code",
        "matched_at",
        "payload",
        "received_at",
    )

    @admin.display(description="Số tiền", ordering="amount")
    def amount_fmt(self, obj: CassoTransaction) -> str:
        sign = "+" if obj.amount >= 0 else ""
        return f"{sign}{int(obj.amount):,}".replace(",", ".") + " đ"

    def has_add_permission(self, request):
        return False  # chỉ tạo từ webhook

    def has_delete_permission(self, request, obj=None):
        return False  # giữ log
