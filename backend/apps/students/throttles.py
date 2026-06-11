"""Rate limit cho login học viên (SĐT + 6 số cuối CCCD).

Theo memory [[student-auth-flow]] chốt 2026-06-11:

- Mỗi SĐT: 10 lần thử/giờ, 30 lần thử/ngày.
- Mỗi IP: 60 lần thử/giờ (chống brute-force scan SĐT).
- Bổ sung lock cứng ở model ``StudentAccount`` (5 fail → 15ph, 10 fail → 24h).

Throttle ở DRF layer chặn flood trước khi chạm DB. Lock ở model là layer 2,
chặn cả attacker đổi IP liên tục.

Cache key hash phone qua SHA1 ngắn để tránh ký tự đặc biệt (dấu cộng từ E.164,
khoảng trắng đầu vào chưa normalize) phá memcached.
"""
import hashlib

from django.conf import settings
from rest_framework.throttling import SimpleRateThrottle

from .models import normalize_phone


def _phone_digest(request) -> str | None:
    # Login chỉ POST với body JSON — không đọc GET fallback (chống attacker
    # phụt rate limit bằng query string đè khi server cấu hình GET hỗ trợ).
    raw = request.data.get("phone") if hasattr(request, "data") else None
    phone = normalize_phone(str(raw or ""))
    if not phone:
        return None
    return hashlib.sha1(phone.encode("utf-8")).hexdigest()[:16]


def _real_ip(request) -> str:
    """IP thật của client.

    Khi ``TRUST_X_FORWARDED_FOR=True`` (đứng sau nginx/Cloudflare đáng tin) lấy
    IP đầu tiên trong header XFF; ngược lại lấy REMOTE_ADDR để client không tự
    forge IP bypass throttle.
    """
    if getattr(settings, "TRUST_X_FORWARDED_FOR", False):
        xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if xff:
            return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "") or "unknown"


class StudentLoginPhoneHourThrottle(SimpleRateThrottle):
    """10 lần/giờ/SĐT — chặn brute force 6 số cuối CCCD theo SĐT."""

    scope = "student_login_phone_hour"

    def get_cache_key(self, request, view):
        digest = _phone_digest(request)
        if not digest:
            return None
        return f"throttle_student_login_phone_hour_{digest}"


class StudentLoginPhoneDayThrottle(SimpleRateThrottle):
    """30 lần/ngày/SĐT — chống brute force kéo dài."""

    scope = "student_login_phone_day"

    def get_cache_key(self, request, view):
        digest = _phone_digest(request)
        if not digest:
            return None
        return f"throttle_student_login_phone_day_{digest}"


class StudentLoginIPThrottle(SimpleRateThrottle):
    """60 lần/giờ/IP — chống scan nhiều SĐT từ cùng 1 IP/botnet."""

    scope = "student_login_ip"

    def get_cache_key(self, request, view):
        # Dùng IP thật (qua XFF khi trust proxy) thay vì ``self.get_ident`` —
        # tránh khóa nhầm chính học viên thật khi tất cả request đến cùng IP
        # nginx/Cloudflare ở prod.
        return f"throttle_student_login_ip_{_real_ip(request)}"


class DeleteRequestThrottle(SimpleRateThrottle):
    """Chống spam yêu cầu xóa dữ liệu (NĐ 13/2023) — 5 lần/giờ/account.

    Idempotent check trong view đã trả 200 cho lần thứ 2, nhưng vẫn cần throttle
    để chống attacker với JWT hợp lệ spam request làm tăng audit log.
    """

    scope = "delete_request"
    rate = "5/hour"

    def get_cache_key(self, request, view):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return None
        account_id = getattr(user, "account_id", None) or getattr(user, "pk", None)
        if not account_id:
            return None
        return f"throttle_delete_request_{account_id}"
