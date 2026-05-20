"""URLs raiz: landing HTML, admin Django e API em /api/ (studio.urls)."""

from django.conf import settings

from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from .views import root

urlpatterns = [
    path("", root),
    path("admin/", admin.site.urls),
    path("api/", include("studio.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
