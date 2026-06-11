"""Tests cho SimpleCSPMiddleware (Sprint 3 Tuần 6 harden)."""
from django.test import RequestFactory, TestCase, override_settings

from apps.core.middleware import SimpleCSPMiddleware


def _make_app(get_response=None):
    return SimpleCSPMiddleware(get_response or (lambda r: _StubResponse()))


class _StubResponse(dict):
    """Đủ giống HttpResponse cho middleware (chỉ cần `__contains__` + `__setitem__`)."""

    pass


class SimpleCSPMiddlewareTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_csp_header_added_when_enabled(self):
        with override_settings(CSP_ENABLED=True, CSP_REPORT_ONLY=False):
            mw = _make_app()
            resp = mw(self.factory.get("/api/site-settings"))
        self.assertIn("Content-Security-Policy", resp)
        self.assertIn("default-src 'self'", resp["Content-Security-Policy"])
        self.assertIn("frame-ancestors 'none'", resp["Content-Security-Policy"])

    def test_csp_report_only_uses_report_only_header(self):
        with override_settings(CSP_ENABLED=True, CSP_REPORT_ONLY=True):
            mw = _make_app()
            resp = mw(self.factory.get("/"))
        self.assertIn("Content-Security-Policy-Report-Only", resp)
        self.assertNotIn("Content-Security-Policy", resp)

    def test_csp_disabled_no_header(self):
        with override_settings(CSP_ENABLED=False):
            mw = _make_app()
            resp = mw(self.factory.get("/"))
        self.assertNotIn("Content-Security-Policy", resp)
        self.assertNotIn("Content-Security-Policy-Report-Only", resp)

    def test_csp_directives_override_merges(self):
        with override_settings(
            CSP_ENABLED=True,
            CSP_REPORT_ONLY=False,
            CSP_DIRECTIVES={"connect-src": "'self' https://api.vietqr.io"},
        ):
            mw = _make_app()
            resp = mw(self.factory.get("/"))
        self.assertIn(
            "connect-src 'self' https://api.vietqr.io",
            resp["Content-Security-Policy"],
        )
        # Directive khác giữ nguyên default
        self.assertIn("default-src 'self'", resp["Content-Security-Policy"])
