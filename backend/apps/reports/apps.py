from django.apps import AppConfig


class ReportsConfig(AppConfig):
    """App `reports`: báo cáo doanh thu/conversion cho admin + kế toán.

    Sprint 3 Tuần 6 deliverable (xem [[03-phase1-plan]] line 271):
    "Báo cáo cơ bản: doanh thu theo ngày, conversion lead → enrollment → paid.
     Export Excel đúng định dạng VN (dấu phân cách `.`, `,`)."
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.reports"
    verbose_name = "Báo cáo"
