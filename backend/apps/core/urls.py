"""URL routing cho app core."""
from django.urls import path

from .views import SiteSettingsPublicView

urlpatterns = [
    path("site-settings", SiteSettingsPublicView.as_view(), name="site-settings"),
]
