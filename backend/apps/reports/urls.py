from django.urls import path

from .views import ConversionReportView, RevenueExportXlsxView, RevenueReportView

urlpatterns = [
    path("admin/reports/revenue", RevenueReportView.as_view(), name="report-revenue"),
    path("admin/reports/conversion", ConversionReportView.as_view(), name="report-conversion"),
    path("admin/reports/revenue/export.xlsx", RevenueExportXlsxView.as_view(), name="report-revenue-export"),
]
