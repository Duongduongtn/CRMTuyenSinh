"""URL routing root."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from apps.payments.urls import webhook_urlpatterns as payments_webhooks


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("apps.core.urls")),
    path("api/", include("apps.courses.urls")),
    path("api/", include("apps.leads.urls")),
    path("api/", include("apps.orders.urls")),
    path("api/", include("apps.payments.urls")),
    path("api/", include("apps.students.urls")),
    path("api/", include("apps.documents.urls")),
    path("api/", include("apps.blog.urls")),
    # Webhook server-to-server (root path, KHÔNG nằm trong /api/)
    *payments_webhooks,
]

if settings.DEBUG:
    # CHỈ serve MEDIA_URL tĩnh cho file KHÔNG nhạy cảm (avatars, brand logo, blog cover).
    # File trong private_documents/ KHÔNG bao giờ được serve qua đây — mọi truy cập
    # đi qua /api/student/documents/<kind>/<id>/file (JWT + IDOR + audit).
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    try:
        import debug_toolbar  # noqa: F401

        urlpatterns += [path("__debug__/", include("debug_toolbar.urls"))]
    except ImportError:
        pass
