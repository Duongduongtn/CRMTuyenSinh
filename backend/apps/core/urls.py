"""URL routing cho app core."""
from django.urls import path

from .views import (
    IntegrationListView,
    IntegrationProviderUpdateView,
    SiteSettingsPublicView,
)

urlpatterns = [
    path("site-settings", SiteSettingsPublicView.as_view(), name="site-settings"),
    # Admin: quản lý credential 4 nhóm tích hợp (superuser only).
    path(
        "admin/integrations/",
        IntegrationListView.as_view(),
        name="integration-list",
    ),
    path(
        "admin/integrations/<str:provider>/",
        IntegrationProviderUpdateView.as_view(),
        name="integration-provider-update",
    ),
]
