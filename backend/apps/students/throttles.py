"""Rate limit cho OTP & login.

- ``OTPRequestThrottle``: 5 lần/giờ/SĐT (theo memory [[student-auth-flow]]).
- ``OTPVerifyThrottle``: 30 lần/giờ/IP — chống brute-force OTP.

Sử dụng SimpleRateThrottle với cache backend. Cache key hash phone qua SHA1
ngắn để tránh ký tự đặc biệt (khoảng trắng, dấu cộng từ E.164) phá memcached.
"""
import hashlib

from rest_framework.throttling import SimpleRateThrottle

from .models import normalize_phone


class OTPRequestThrottle(SimpleRateThrottle):
    scope = "otp_request"
    rate = "5/hour"

    def get_cache_key(self, request, view):
        phone_raw = (
            request.data.get("phone") if hasattr(request, "data") else None
        ) or request.GET.get("phone", "")
        phone = normalize_phone(str(phone_raw or ""))
        if not phone:
            return None
        digest = hashlib.sha1(phone.encode("utf-8")).hexdigest()[:16]
        return f"throttle_otp_request_{digest}"


class OTPVerifyThrottle(SimpleRateThrottle):
    scope = "otp_verify"
    rate = "30/hour"

    def get_cache_key(self, request, view):
        ident = self.get_ident(request)
        return f"throttle_otp_verify_{ident}"
