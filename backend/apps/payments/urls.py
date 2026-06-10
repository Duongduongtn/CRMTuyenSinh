"""URL routing cho app payments."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CassoTransactionViewSet, DepositQRView, PaymentViewSet
from .webhooks import casso_webhook

router = DefaultRouter()
router.register("admin/payments", PaymentViewSet, basename="admin-payment")
router.register(
    "admin/casso-transactions",
    CassoTransactionViewSet,
    basename="admin-casso-tx",
)

urlpatterns = [
    path("", include(router.urls)),
    path(
        "public/enrollments/by-token/<uuid:token>/qr",
        DepositQRView.as_view(),
        name="enrollment-qr",
    ),
]

# Webhook nằm root path (không nested trong /api/) để URL gọn cho Casso config
webhook_urlpatterns = [
    path("webhook/casso", casso_webhook, name="casso-webhook"),
]
