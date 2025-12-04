from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from assets.views import AssetViewSet, ManufacturerViewSet
from projects.views import ProjectViewSet, SnapshotViewSet

# Create a router and register our viewsets with it.
router = DefaultRouter()
router.register(r'assets', AssetViewSet)
router.register(r'manufacturers', ManufacturerViewSet)
router.register(r'projects', ProjectViewSet)
router.register(r'snapshots', SnapshotViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    # This includes all the API routes automatically
    path('api/', include(router.urls)),
]