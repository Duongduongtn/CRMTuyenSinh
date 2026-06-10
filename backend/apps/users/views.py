"""Auth endpoints cho CRM Vue SPA.

Stack: cookie session (Django built-in) + CSRF token. SPA gọi:
1. `GET /api/auth/csrf` — set cookie `csrftoken` để các POST sau gửi kèm header `X-CSRFToken`.
2. `POST /api/auth/login` — body `{username, password}` → set session cookie + trả user.
3. `GET /api/auth/me` — kiểm tra session + trả user hiện tại.
4. `POST /api/auth/logout` — xóa session.

KHÔNG dùng JWT vì session cookie + CSRF an toàn hơn cho SPA cùng subdomain,
và tận dụng được toàn bộ permission/group built-in của Django.
"""
from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from .serializers import LoginSerializer, UserMeSerializer


class LoginThrottle(AnonRateThrottle):
    """5 lần login fail/giờ/IP — chống brute force."""

    scope = "anon"
    rate = "20/hour"


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CSRFView(APIView):
    """`GET /api/auth/csrf` — set cookie csrftoken, trả token để FE lưu vào header.

    FE Vue SPA dùng axios `withCredentials: true`. Sau khi gọi endpoint này,
    cookie `csrftoken` sẽ có trong browser, axios interceptor đọc và gửi qua
    header `X-CSRFToken` ở mọi POST/PUT/PATCH/DELETE.
    """

    permission_classes = [AllowAny]
    throttle_classes = []

    def get(self, request):
        token = get_token(request)
        return Response({"csrfToken": token})


class LoginView(APIView):
    """`POST /api/auth/login` — username + password → session cookie.

    Throttle 20 lần/giờ/IP. Không tiết lộ lý do fail (user not exist vs sai pass)
    để chống enum.
    """

    permission_classes = [AllowAny]
    throttle_classes = [LoginThrottle]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        username = serializer.validated_data["username"]
        password = serializer.validated_data["password"]

        user = authenticate(request, username=username, password=password)
        if user is None:
            return Response(
                {"detail": "Tên đăng nhập hoặc mật khẩu không đúng."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        if not user.is_active:
            return Response(
                {"detail": "Tài khoản đã bị khoá. Liên hệ quản trị viên."},
                status=status.HTTP_403_FORBIDDEN,
            )
        # KHÔNG cho học viên login vào CRM (StudentAccount riêng).
        # Yêu cầu phải là staff hoặc thuộc 1 trong 4 group nội bộ.
        if not (user.is_staff or user.groups.filter(name__in=["admin", "sale", "accountant", "clerk"]).exists()):
            return Response(
                {"detail": "Tài khoản không có quyền truy cập CRM."},
                status=status.HTTP_403_FORBIDDEN,
            )

        login(request, user)
        return Response(UserMeSerializer(user, context={"request": request}).data)


class MeView(APIView):
    """`GET /api/auth/me` — trả user hiện tại. 401 nếu chưa login.

    FE dùng để khởi tạo Pinia store auth lúc app boot.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserMeSerializer(request.user, context={"request": request}).data)


class LogoutView(APIView):
    """`POST /api/auth/logout` — xoá session cookie."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response({"detail": "Đã đăng xuất."})
