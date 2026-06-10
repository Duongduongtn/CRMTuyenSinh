from django.apps import AppConfig


class StudentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.students"
    verbose_name = "Học viên"

    def ready(self):
        from . import signals  # noqa
