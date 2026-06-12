"""Tests cho healthz endpoint dùng cho CI deploy + monitoring."""
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient


class HealthzViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_healthz_returns_200_ok_without_auth(self):
        resp = self.client.get(reverse("healthz"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"ok": True})

    def test_healthz_url_path_matches_deploy_yml_expectation(self):
        """Workflow `.github/workflows/deploy.yml` Step 7 curl
        `http://127.0.0.1:8003/healthz/` — path phải trùng exact."""
        from django.urls import reverse

        self.assertEqual(reverse("healthz"), "/healthz/")
