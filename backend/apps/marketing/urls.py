"""URL routing app marketing.

Webhook endpoint nằm ở ROOT (không phải /api/) để FB không phải hit qua API
router. Reuse pattern app payments.
"""
from django.urls import path

from .views import fb_leadgen_webhook

webhook_urlpatterns = [
    path("webhook/fb-leadgen", fb_leadgen_webhook, name="fb-leadgen-webhook"),
]
