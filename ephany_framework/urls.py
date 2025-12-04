from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
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
    path('', RedirectView.as_view(url='admin/', permanent=False), name='index'),
    path('admin/', admin.site.urls),
    # This includes all the API routes automatically
    path('api/', include(router.urls)),
]