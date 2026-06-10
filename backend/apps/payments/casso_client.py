"""Casso API client tối thiểu cho reconcile fallback.

Spec: https://docs.casso.vn/ — endpoint ``GET /v2/transactions``.

Chỉ dùng cho reconcile task khi webhook bị miss. KHÔNG dùng cho luồng chính
(luồng chính: webhook → process → confirm < 2 phút).

Auth: header ``Authorization: Apikey {CASSO_API_KEY}``.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Iterable

import requests
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger("apps.payments")

CASSO_BASE_URL = "https://oauth.casso.vn/v2"
DEFAULT_PAGE_SIZE = 100
DEFAULT_TIMEOUT = 15  # seconds


class CassoAPIError(Exception):
    """Lỗi từ Casso API — không retry trong task, log để admin xem."""


def fetch_recent_transactions(
    *,
    since: datetime | None = None,
    page_size: int = DEFAULT_PAGE_SIZE,
    api_key: str | None = None,
) -> list[dict]:
    """Lấy danh sách giao dịch gần đây từ Casso.

    Args:
        since: lấy giao dịch từ thời điểm này về sau. None = 24 giờ gần đây.
        page_size: số tx trên 1 trang. Casso cho phép tối đa 100.
        api_key: override settings.CASSO_API_KEY (cho test).

    Returns:
        List dict raw từ Casso, mỗi item là 1 transaction. Trả [] nếu API key trống.
    """
    api_key = (api_key or settings.CASSO_API_KEY or "").strip()
    if not api_key:
        logger.info("CASSO_API_KEY rỗng — bỏ qua reconcile pull.")
        return []

    if since is None:
        since = timezone.now() - timedelta(hours=24)

    params = {
        "fromDate": since.strftime("%Y-%m-%d"),
        "page": 1,
        "pageSize": page_size,
        "sort": "DESC",
    }
    headers = {
        "Authorization": f"Apikey {api_key}",
        "Accept": "application/json",
    }
    try:
        resp = requests.get(
            f"{CASSO_BASE_URL}/transactions",
            params=params,
            headers=headers,
            timeout=DEFAULT_TIMEOUT,
        )
    except requests.RequestException as exc:
        logger.warning("Casso API request lỗi: %s", exc)
        raise CassoAPIError(str(exc)) from exc

    if resp.status_code >= 400:
        logger.warning(
            "Casso API trả status %s: %s", resp.status_code, resp.text[:300]
        )
        raise CassoAPIError(f"HTTP {resp.status_code}")

    try:
        body = resp.json()
    except ValueError as exc:
        raise CassoAPIError(f"Casso trả JSON không hợp lệ: {exc}") from exc

    if body.get("error", -1) != 0:
        raise CassoAPIError(
            f"Casso trả error={body.get('error')}: {body.get('message', '')}"
        )

    records = (body.get("data") or {}).get("records") or []
    if not isinstance(records, list):
        return []
    return [r for r in records if isinstance(r, dict)]


def iter_recent_transactions(
    *, since: datetime | None = None
) -> Iterable[dict]:
    """Generator wrapper — để task không phải xử lý exception chi tiết."""
    try:
        yield from fetch_recent_transactions(since=since)
    except CassoAPIError as exc:
        logger.error("Reconcile pull Casso lỗi: %s", exc)
        return
