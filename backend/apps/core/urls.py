"""URL routing cho app core."""
from django.urls import path

from .views import (
    IntegrationListView,
    IntegrationProviderUpdateView,
    SiteSettingsAdminView,
    SiteSettingsBrandImageView,
    SiteSettingsPublicView,
)

urlpatterns = [
    path("site-settings", SiteSettingsPublicView.as_view(), name="site-settings"),
    # Admin: chỉnh full SiteSettings (superuser only).
    path(
        "admin/site-settings/",
        SiteSettingsAdminView.as_view(),
        name="admin-site-settings",
    ),
    path(
        "admin/site-settings/upload-image/",
        SiteSettingsBrandImageView.as_view(),
        name="admin-site-settings-upload-image",
    ),
    # Admin: quản lý credential các nhóm tích hợp (superuser only).
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
