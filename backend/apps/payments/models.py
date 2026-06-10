"""
App `payments` — 2 model:

- `Payment`: 1 record = 1 lần học viên đóng tiền (cọc hoặc đóng tiếp). DecimalField cho tiền.
- `CassoTransaction`: log raw giao dịch ngân hàng từ webhook Casso. `tid` unique
  làm idempotent key — webhook re-send không tạo Payment trùng.

Xem thêm:
- VietQR generator: ``apps.payments.vietqr``
- Webhook handler: ``apps.payments.webhooks.casso_webhook``
"""
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


class PaymentMethod(models.TextChoices):
    BANK_TRANSFER = "bank_transfer", _("Chuyển khoản")
    CASH = "cash", _("Tiền mặt")
    CASSO = "casso", _("Casso (tự động)")
    MANUAL = "manual", _("Xác nhận thủ công")


class PaymentStatus(models.TextChoices):
    PENDING = "pending", _("Chờ xác nhận")
    CONFIRMED = "confirmed", _("Đã xác nhận")
    FAILED = "failed", _("Thất bại")
    REFUNDED = "refunded", _("Đã hoàn")


class CassoTransaction(models.Model):
    """Raw giao dịch từ webhook Casso. Lưu để truy vết + reconcile."""

    tid = models.CharField(
        _("Mã GD ngân hàng (tid)"),
        max_length=64,
        unique=True,
        db_index=True,
        help_text=_("Idempotent key. Webhook re-send với cùng tid → bỏ qua."),
    )
    casso_id = models.CharField(
        _("Casso ID"),
        max_length=64,
        blank=True,
        default="",
        help_text=_("ID nội bộ của Casso, khác với tid của ngân hàng."),
    )
    description = models.TextField(
        _("Nội dung CK"),
        help_text=_("Raw description từ ngân hàng. Webhook regex tìm ORD-XXXXXX trong này."),
    )
    amount = models.DecimalField(
        _("Số tiền"),
        max_digits=14,
        decimal_places=0,
        help_text=_("Dương = tiền vào, âm = tiền ra. Chỉ quan tâm dương khi match."),
    )
    bank_brand_name = models.CharField(_("Ngân hàng"), max_length=100, blank=True, default="")
    bank_sub_acc_id = models.CharField(_("Số TK nhận"), max_length=50, blank=True, default="")
    when = models.DateTimeField(
        _("Thời điểm GD"),
        null=True,
        blank=True,
        help_text=_("Theo timezone Casso gửi, parse sang UTC để lưu."),
    )

    # Đối soát
    matched_enrollment = models.ForeignKey(
        "orders.Enrollment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="casso_transactions",
        verbose_name=_("Đơn được match"),
    )
    matched_at = models.DateTimeField(_("Match lúc"), null=True, blank=True)
    matched_code = models.CharField(
        _("Mã đơn match (regex)"),
        max_length=20,
        blank=True,
        default="",
        help_text=_("Mã ORD-XXXXXX trích từ description bằng regex."),
    )

    payload = models.JSONField(_("Payload raw"), blank=True, null=True)
    received_at = models.DateTimeField(_("Webhook nhận lúc"), auto_now_add=True)

    class Meta:
        verbose_name = _("Giao dịch Casso")
        verbose_name_plural = _("Giao dịch Casso")
        ordering = ["-received_at"]
        indexes = [
            models.Index(fields=["-received_at"]),
            models.Index(fields=["matched_enrollment", "-received_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.tid} · {self.amount}"


class Payment(models.Model):
    """1 lần học viên đóng tiền cho enrollment. DecimalField — KHÔNG Float."""

    enrollment = models.ForeignKey(
        "orders.Enrollment",
        on_delete=models.PROTECT,
        related_name="payments",
        verbose_name=_("Đơn"),
    )
    amount = models.DecimalField(
        _("Số tiền"),
        max_digits=12,
        decimal_places=0,
        validators=[MinValueValidator(0)],
    )
    method = models.CharField(
        _("Hình thức"),
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.CASSO,
    )
    status = models.CharField(
        _("Trạng thái"),
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.CONFIRMED,
        help_text=_("Casso/cash mặc định confirmed. Manual cần kế toán duyệt."),
    )

    # Idempotent key cho Casso (1 Casso tx chỉ tạo tối đa 1 Payment)
    casso_transaction = models.OneToOneField(
        CassoTransaction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payment",
        verbose_name=_("Giao dịch Casso"),
    )
    bank_tx_id = models.CharField(
        _("Mã GD ngân hàng"),
        max_length=64,
        blank=True,
        default="",
        help_text=_("Lặp lại từ Casso tid để dễ tìm. Không unique vì cash/manual không có."),
    )
    reference_code = models.CharField(
        _("Mã đơn ghi trong nội dung CK"),
        max_length=20,
        blank=True,
        default="",
    )

    notes = models.TextField(_("Ghi chú"), blank=True, default="")

    # Người tạo (Casso webhook → null; manual → kế toán)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_payments",
        verbose_name=_("Người tạo"),
    )
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="confirmed_payments",
        verbose_name=_("Người xác nhận"),
    )
    confirmed_at = models.DateTimeField(_("Xác nhận lúc"), null=True, blank=True)
    created_at = models.DateTimeField(_("Tạo lúc"), auto_now_add=True)

    class Meta:
        verbose_name = _("Khoản thanh toán")
        verbose_name_plural = _("Khoản thanh toán")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["enrollment", "-created_at"]),
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["bank_tx_id"]),
        ]

    def __str__(self) -> str:
        return f"{self.enrollment.code} · {int(self.amount):,}".replace(",", ".") + " đ"
