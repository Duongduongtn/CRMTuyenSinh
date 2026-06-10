"""URL public blog."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import PublicBlogCategoryViewSet, PublicBlogPostViewSet

router = DefaultRouter()
router.register("public/blog/categories", PublicBlogCategoryViewSet, basename="public-blog-category")
router.register("public/blog/posts", PublicBlogPostViewSet, basename="public-blog-post")

urlpatterns = [
    path("", include(router.urls)),
]
