from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin

from django.urls import path, include
from django.views.generic import RedirectView
from rest_framework.routers import DefaultRouter
from assets.views import AssetViewSet, AssetFileViewSet, ManufacturerViewSet
from projects.views import ProjectViewSet, SnapshotViewSet
from users.views import UserViewSet

# Create a router and register our viewsets with it.
router = DefaultRouter()
router.register(r'assets', AssetViewSet)
router.register(r'files', AssetFileViewSet)
router.register(r'manufacturers', ManufacturerViewSet)
router.register(r'projects', ProjectViewSet)
router.register(r'snapshots', SnapshotViewSet)
router.register(r'users', UserViewSet)


urlpatterns = [
    path('', RedirectView.as_view(url='admin/', permanent=False), name='index'),
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
]

# --- Admin Customization ---
admin.site.site_header = "Ephany Admin"
admin.site.site_title = "Ephany Portal"
admin.site.index_title = "Welcome to Ephany Asset Manager"

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)