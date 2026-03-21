from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter  # <-- Added OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

from .models import (
    Manufacturer,
    Asset,
    AssetAttribute,
    AssetAttributeChoice,
    AssetCategory,
    AssetFile,
    Vendor,
    VendorProduct
)
from .serializers import (
    ManufacturerSerializer,
    AssetSerializer,
    AssetFileSerializer,
    AssetCategorySerializer,
    AssetAttributeSerializer,
    AssetAttributeChoiceSerializer,
    CategoryListSerializer,
    VendorSerializer,
    VendorProductSerializer,
)


class ManufacturerViewSet(viewsets.ModelViewSet):
    """
    ViewSet for viewing and editing manufacturers.
    Supports search by name and ordering.
    """
    queryset = Manufacturer.objects.all()
    serializer_class = ManufacturerSerializer

    # Add SearchFilter and OrderingFilter
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]

    # Fields for 'DjangoFilterBackend' (exact matches)
    filterset_fields = {
        'name': ['exact', 'iexact', 'icontains']
    }

    # Fields for 'SearchFilter' (?search=...)
    search_fields = ['name']

    # Default ordering and allowed ordering fields
    ordering_fields = ['name']
    ordering = ['name']


class AssetAttributeViewSet(viewsets.ModelViewSet):
    """
    Full CRUD endpoint for asset custom attribute definitions.
    Choices are nested inline for read. Manage choices via /api/attribute-choices/.
    """
    queryset = AssetAttribute.objects.prefetch_related('choices').all().order_by('name')
    serializer_class = AssetAttributeSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name', 'scope', 'data_type']


class AssetAttributeChoiceViewSet(viewsets.ModelViewSet):
    """
    Full CRUD endpoint for picklist choices belonging to a 'choice'-type AssetAttribute.
    Supports filtering by attribute id: /api/attribute-choices/?attribute=<id>
    Supports filtering by attribute name: /api/attribute-choices/?attribute__name=<name>
    """
    queryset = AssetAttributeChoice.objects.select_related('attribute').all()
    serializer_class = AssetAttributeChoiceSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = {
        'attribute': ['exact'],
        'attribute__name': ['exact', 'icontains'],
    }
    ordering_fields = ['attribute__name', 'order', 'value']
    ordering = ['attribute__name', 'order']

    def get_serializer_context(self):
        context = super().get_serializer_context()
        # Inject the attribute object into serializer context on create
        # so validate() can check its data_type before the instance is saved.
        if self.request.method == 'POST':
            attribute_id = self.request.data.get('attribute')
            if attribute_id:
                try:
                    context['attribute'] = AssetAttribute.objects.get(pk=attribute_id)
                except AssetAttribute.DoesNotExist:
                    pass  # Let DRF's standard FK validation handle the missing object error
        return context


class AssetCategoryViewSet(viewsets.ModelViewSet):
    queryset = AssetCategory.objects.all()
    serializer_class = AssetCategorySerializer


class AssetFileViewSet(viewsets.ModelViewSet):
    queryset = AssetFile.objects.all()
    serializer_class = AssetFileSerializer


class AssetViewSet(viewsets.ModelViewSet):
    queryset = Asset.objects.all()
    serializer_class = AssetSerializer

    # Enable file uploads
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    # Configuration for filtering, searching, and sorting
    # Added OrderingFilter here to enable the ?ordering parameter
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]

    # Fielded filtering (allows exact/partial matches on specific fields)
    filterset_fields = {
        "type_id": ["exact", "iexact"],
        "manufacturer__name": ["exact", "iexact", "icontains"],
        "model": ["exact", "iexact", "icontains"],
        "name": ["icontains", "exact"],
        "description": ["icontains", "exact"],
        "category__name": ["exact"],
    }

    # Keyword search (allows searching across these fields simultaneously)
    search_fields = [
        "name",
        "description",
        "model",
        "manufacturer__name",
    ]

    # NEW: Define which fields are allowed to be sorted
    ordering_fields = [
        'type_id',
        'name',
        'manufacturer__name', # Allows sorting by manufacturer name
        'model',
        'category__name',     # Allows sorting by category name
        'created_at',
        'updated_at'
    ]

    def update(self, request, *args, **kwargs):
        print("DEBUG FILES:", request.FILES)  # <--- Check console. Is this empty?
        return super().update(request, *args, **kwargs)

    @action(detail=False, methods=['get'])
    def all_categories(self, request):
        """
        Custom action to return a non-paginated, complete list of unique
        asset categories for filter dropdowns in the frontend.
        Endpoint: /api/assets/all_categories/
        """
        categories = AssetCategory.objects.all().order_by('name')
        serializer = CategoryListSerializer(categories, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def all_manufacturers(self, request):
        """
        Returns a non-paginated list of all manufacturers for filter dropdowns.
        Endpoint: /api/assets/all_manufacturers/
        """
        manufacturers = Manufacturer.objects.all().order_by('name')
        serializer = ManufacturerSerializer(manufacturers, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class VendorViewSet(viewsets.ModelViewSet):
    queryset = Vendor.objects.all().order_by('name')
    serializer_class = VendorSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name']


class VendorProductViewSet(viewsets.ModelViewSet):
    queryset = VendorProduct.objects.select_related('asset', 'vendor').all()
    serializer_class = VendorProductSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['vendor', 'asset']
    search_fields = ['asset__name', 'vendor__name', 'sku']
    ordering_fields = ['vendor__name', 'asset__name', 'cost']