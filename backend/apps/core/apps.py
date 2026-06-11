from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    verbose_name = "Lõi hệ thống"

    def ready(self):
        # Đăng ký signal handlers ghi AuditLog. Xem apps/core/signals.py.
        from . import signals  # noqa: F401
