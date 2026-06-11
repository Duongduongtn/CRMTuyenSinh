"""Thread-local context cho audit signals.

Django signals (post_save, post_delete) không nhận `request`, nên ta phải
push request hiện tại vào thread-local ở middleware, signal sẽ đọc ra.
Phải cleanup ngay sau response để tránh leak giữa các request (thread reuse).
"""
import threading

_local = threading.local()


def get_current_request():
    """Trả request hiện tại hoặc None (background task, management command, test sync)."""
    return getattr(_local, "request", None)


class AuditContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _local.request = request
        try:
            return self.get_response(request)
        finally:
            _local.request = None


# ---------------------------------------------------------------------------
# CSP middleware (Sprint 3 Tuần 6 deliverable: security headers pass Mozilla A).
# ---------------------------------------------------------------------------

DEFAULT_CSP_DIRECTIVES = {
    "default-src": "'self'",
    # Django admin + DRF browsable cần inline style + cssnano runtime.
    "style-src": "'self' 'unsafe-inline'",
    # Django admin có 1 vài inline script nhỏ; chấp nhận để không phá admin.
    # Khi rời admin sang SPA riêng có thể strict hơn.
    "script-src": "'self' 'unsafe-inline'",
    "img-src": "'self' data: blob: https:",
    "font-src": "'self' data:",
    "connect-src": "'self'",
    "frame-src": "'none'",
    "object-src": "'none'",
    "base-uri": "'self'",
    "form-action": "'self'",
    "frame-ancestors": "'none'",
    "upgrade-insecure-requests": "",
}


def _build_csp_header(directives: dict) -> str:
    parts = []
    for k, v in directives.items():
        if v:
            parts.append(f"{k} {v}")
        else:
            parts.append(k)
    return "; ".join(parts)


class SimpleCSPMiddleware:
    """Đặt header Content-Security-Policy (hoặc Report-Only) dựa trên settings.

    Bật/tắt qua `CSP_ENABLED` (default True). Report-only qua `CSP_REPORT_ONLY`.
    Custom directives qua `CSP_DIRECTIVES` (dict).

    Relaxed policy cho 1 số path prefix (`CSP_RELAXED_PATH_PREFIXES`):
    Django admin có inline script không tránh được — nới `script-src` riêng cho
    `/admin/` thay vì áp 'unsafe-inline' toàn site (xem reviewer P0 Sprint 3 Tuần 6).
    """

    def __init__(self, get_response):
        from django.conf import settings

        self.get_response = get_response
        self.enabled = bool(getattr(settings, "CSP_ENABLED", True))
        self.report_only = bool(getattr(settings, "CSP_REPORT_ONLY", False))

        directives = dict(DEFAULT_CSP_DIRECTIVES)
        directives.update(getattr(settings, "CSP_DIRECTIVES", {}) or {})
        self.strict_value = _build_csp_header(directives)

        relaxed_directives = getattr(settings, "CSP_DIRECTIVES_RELAXED", None)
        if relaxed_directives:
            self.relaxed_value = _build_csp_header({**directives, **relaxed_directives})
        else:
            self.relaxed_value = None

        self.relaxed_prefixes = tuple(getattr(settings, "CSP_RELAXED_PATH_PREFIXES", ()) or ())
        self.header_name = (
            "Content-Security-Policy-Report-Only" if self.report_only else "Content-Security-Policy"
        )

    def _value_for(self, path: str) -> str:
        if self.relaxed_value and path.startswith(self.relaxed_prefixes):
            return self.relaxed_value
        return self.strict_value

    def __call__(self, request):
        response = self.get_response(request)
        if self.enabled and self.header_name not in response:
            response[self.header_name] = self._value_for(request.path)
        return response
