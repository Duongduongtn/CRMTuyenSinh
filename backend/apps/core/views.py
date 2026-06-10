"""Views public cho app core — SiteSettings cho FE."""
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import SiteSettings
from .serializers import SiteSettingsPublicSerializer


class SiteSettingsPublicView(APIView):
    """GET /api/site-settings — brand, contact, SEO mặc định cho FE Nuxt.

    Public, không cần auth. FE Nuxt SSG gọi vào lúc build time + 1 lần khi hydrate.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        site = SiteSettings.get_solo()
        return Response(
            SiteSettingsPublicSerializer(site, context={"request": request}).data
        )
