from django.apps import AppConfig


class LeadsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.leads"
    verbose_name = "Lead (khách hàng tiềm năng)"

    def ready(self):
        from . import signals  # noqa
