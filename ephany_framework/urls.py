from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken.views import obtain_auth_token
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

# --- Views ---
from access.views import (
    CustomAuthToken)

from assets.views import (
    AssetViewSet,
    AssetCategoryViewSet,
    AssetFileViewSet,
    ManufacturerViewSet,
    AssetAttributeViewSet,
    AssetAttributeChoiceViewSet,
    VendorViewSet,
    VendorProductViewSet,
)

from projects.views import (
    ProjectViewSet,
    SiteViewSet,
    SnapshotViewSet,
    AssetInstanceViewSet
)

from users.views import UserViewSet

# --- Router Config ---
router = DefaultRouter()

# Assets
router.register(r'assets', AssetViewSet)
router.register(r'categories', AssetCategoryViewSet)
router.register(r'manufacturers', ManufacturerViewSet)
router.register(r'attributes', AssetAttributeViewSet)
router.register(r'attribute-choices', AssetAttributeChoiceViewSet)  # New
router.register(r'files', AssetFileViewSet)
router.register(r'vendors', VendorViewSet)
router.register(r'vendor-products', VendorProductViewSet)

# Projects
router.register(r'sites', SiteViewSet)
router.register(r'projects', ProjectViewSet)
router.register(r'snapshots', SnapshotViewSet)
router.register(r'instances', AssetInstanceViewSet)

# Users
router.register(r'users', UserViewSet)

urlpatterns = [
    path('', RedirectView.as_view(url='admin/', permanent=False), name='index'),
    path('admin/', admin.site.urls),

    # API Routes
    path('api/', include(router.urls)),

    # OpenAPI 3 schema and browsable documentation.
    # The raw spec is also committed at the repo root as openapi.yaml.
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path(
        'api/docs/',
        SpectacularSwaggerView.as_view(url_name='schema'),
        name='swagger-ui',
    ),
    path(
        'api/redoc/',
        SpectacularRedocView.as_view(url_name='schema'),
        name='redoc',
    ),

    # Auth Endpoint: POST username/password to receive a Token
    path('api/login/', CustomAuthToken.as_view(), name='api_token_auth'),
]

# --- Admin Customization ---
admin.site.site_header = "Ephany Admin"
admin.site.site_title = "Ephany Portal"
admin.site.index_title = "Welcome to Ephany Asset Manager"

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)