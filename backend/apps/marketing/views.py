"""Views app marketing.

- ``fb_leadgen_webhook`` (GET + POST) — Facebook Lead Ads webhook.

GET: Facebook verify khi setup webhook URL. Trả ``hub.challenge`` nếu
``hub.verify_token`` khớp ``FB_LEAD_VERIFY_TOKEN``.

POST: nhận payload changes, validate signature ``X-Hub-Signature-256``, dispatch
sang :func:`apps.marketing.services.process_fb_leadgen`.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging

from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from apps.core.integrations import get_credential

from .services import FBLeadProcessError, process_fb_leadgen

logger = logging.getLogger("apps.marketing")


def _verify_signature(raw_body: bytes, signature_header: str) -> bool:
    """Verify ``X-Hub-Signature-256: sha256=<hex>`` từ Facebook.

    App secret là ``FB_APP_SECRET`` trong settings. Nếu chưa cấu hình → reject.
    Riêng dev có flag ``FB_ALLOW_INSECURE_DEV`` (bool) để bypass khi vẫn chưa
    có secret từ FB Business Manager. KHÔNG dùng cờ DEBUG vì admin có thể bật
    DEBUG tạm ở prod để debug rồi quên tắt → đủ điều kiện bypass attacker.
    """
    # Ưu tiên DB IntegrationCredential (UI paste), fallback ENV settings.FB_APP_SECRET.
    app_secret = get_credential("fb", "app_secret") or ""
    if not app_secret:
        if getattr(settings, "FB_ALLOW_INSECURE_DEV", False):
            logger.warning(
                "FB_APP_SECRET trống + FB_ALLOW_INSECURE_DEV=True — skip verify (dev only)."
            )
            return True
        return False
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    received_sig = signature_header.split("=", 1)[1].strip()
    expected_sig = hmac.new(
        app_secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected_sig, received_sig)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def fb_leadgen_webhook(request):
    """Endpoint webhook Facebook Lead Ads.

    GET (Facebook verify): trả challenge nếu verify_token khớp.
    POST: parse changes, dispatch tới service tạo Lead.

    KHÔNG trả thông tin lỗi chi tiết cho client (chống fingerprint endpoint).
    Lỗi đã log ở backend.
    """
    if request.method == "GET":
        mode = request.GET.get("hub.mode")
        token = request.GET.get("hub.verify_token")
        challenge = request.GET.get("hub.challenge")
        expected = get_credential("fb", "lead_verify_token") or ""
        if not expected:
            logger.error("FB_LEAD_VERIFY_TOKEN chưa cấu hình.")
            return HttpResponse("forbidden", status=403)
        if mode == "subscribe" and token and hmac.compare_digest(token, expected):
            return HttpResponse(challenge or "", content_type="text/plain")
        return HttpResponse("forbidden", status=403)

    # POST
    raw_body = request.body or b""
    signature = request.headers.get("X-Hub-Signature-256", "")
    if not _verify_signature(raw_body, signature):
        logger.warning("FB webhook signature không hợp lệ.")
        return HttpResponse("invalid signature", status=403)

    try:
        body = json.loads(raw_body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        logger.warning("FB webhook body không phải JSON.")
        return HttpResponse("invalid body", status=400)

    entries = body.get("entry") or []
    processed = 0
    for entry in entries:
        for change in entry.get("changes") or []:
            if change.get("field") != "leadgen":
                continue
            value = change.get("value") or {}
            try:
                process_fb_leadgen(value)
                processed += 1
            except FBLeadProcessError as exc:
                logger.warning("FB lead invalid: %s", exc)
            except Exception:
                # Không retry tự động — Facebook sẽ retry webhook nếu trả non-200.
                # Nhưng nếu lỗi liên tục, log để cảnh báo. Trả 200 OK để FB không
                # retry ngập log với bad payload.
                logger.exception("Lỗi xử lý FB leadgen, payload=%s", value)

    return HttpResponse(
        json.dumps({"received": True, "processed": processed}),
        content_type="application/json",
    )
