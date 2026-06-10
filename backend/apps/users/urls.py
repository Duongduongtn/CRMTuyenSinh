"""URL routing app users — auth endpoints cho CRM Vue SPA."""
from django.urls import path

from .views import CSRFView, LoginView, LogoutView, MeView


urlpatterns = [
    path("auth/csrf", CSRFView.as_view(), name="auth-csrf"),
    path("auth/login", LoginView.as_view(), name="auth-login"),
    path("auth/me", MeView.as_view(), name="auth-me"),
    path("auth/logout", LogoutView.as_view(), name="auth-logout"),
]
