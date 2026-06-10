"""Tests cho auth endpoints CRM Vue SPA.

Cover:
1. /api/auth/csrf set cookie csrftoken
2. /api/auth/login pass → 200 + user payload + session cookie
3. /api/auth/login sai pass → 401
4. /api/auth/login user không thuộc group nội bộ → 403 (chống học viên login CRM)
5. /api/auth/me chưa login → 401
6. /api/auth/me sau khi login → trả user + groups
7. /api/auth/logout → xoá session

Chạy: `python manage.py test apps.users`.
"""
from django.contrib.auth.models import Group
from django.test import TestCase
from rest_framework.test import APIClient

from .models import User


class AuthEndpointsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.sale_group, _ = Group.objects.get_or_create(name="sale")
        cls.admin_group, _ = Group.objects.get_or_create(name="admin")

        cls.sale_user = User.objects.create_user(
            username="sale1",
            password="StrongPass123!",
            full_name="Nguyễn Văn Sale",
            email="sale1@example.com",
        )
        cls.sale_user.groups.add(cls.sale_group)

        # User không group nội bộ → không được login CRM
        cls.outsider = User.objects.create_user(
            username="outsider",
            password="StrongPass123!",
            full_name="Người ngoài",
        )

    def setUp(self):
        self.client = APIClient(enforce_csrf_checks=False)

    def test_csrf_endpoint_returns_token(self):
        resp = self.client.get("/api/auth/csrf")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("csrfToken", resp.json())
        self.assertIn("csrftoken", resp.cookies)

    def test_login_success_returns_user_with_groups(self):
        resp = self.client.post(
            "/api/auth/login",
            {"username": "sale1", "password": "StrongPass123!"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["username"], "sale1")
        self.assertEqual(data["display_name"], "Nguyễn Văn Sale")
        self.assertIn("sale", data["groups"])
        self.assertIn("Tư vấn viên", data["role_labels"])

    def test_login_wrong_password_returns_401(self):
        resp = self.client.post(
            "/api/auth/login",
            {"username": "sale1", "password": "wrong"},
            format="json",
        )
        self.assertEqual(resp.status_code, 401)

    def test_login_username_case_insensitive(self):
        resp = self.client.post(
            "/api/auth/login",
            {"username": "SALE1", "password": "StrongPass123!"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)

    def test_outsider_cannot_login_crm(self):
        """User active nhưng không thuộc group nội bộ → 403."""
        resp = self.client.post(
            "/api/auth/login",
            {"username": "outsider", "password": "StrongPass123!"},
            format="json",
        )
        self.assertEqual(resp.status_code, 403)

    def test_me_requires_auth(self):
        """DRF SessionAuth + IsAuthenticated trả 403 khi chưa login (không 401)
        vì không có WWW-Authenticate challenge. FE axios interceptor xử lý cả
        401 lẫn 403 → redirect login."""
        resp = self.client.get("/api/auth/me")
        self.assertEqual(resp.status_code, 403)

    def test_me_after_login_returns_user(self):
        self.client.post(
            "/api/auth/login",
            {"username": "sale1", "password": "StrongPass123!"},
            format="json",
        )
        resp = self.client.get("/api/auth/me")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["username"], "sale1")

    def test_logout_clears_session(self):
        self.client.post(
            "/api/auth/login",
            {"username": "sale1", "password": "StrongPass123!"},
            format="json",
        )
        self.client.post("/api/auth/logout")
        resp = self.client.get("/api/auth/me")
        self.assertEqual(resp.status_code, 403)  # DRF SessionAuth không challenge → 403
