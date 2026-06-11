"""Permission cho báo cáo: admin (group `admin` hoặc superuser) + kế toán (group `accountant`)."""
from rest_framework.permissions import BasePermission


class IsAdminOrAccountant(BasePermission):
    """Chỉ admin + kế toán xem được báo cáo doanh thu."""

    message = "Chỉ admin/kế toán được xem báo cáo."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        return user.groups.filter(name__in=("admin", "accountant")).exists()
