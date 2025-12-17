from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

from .models import Manufacturer, Asset, AssetCategory, AssetFile
from .serializers import (
    ManufacturerSerializer,
    AssetSerializer,
    AssetFileSerializer,
    AssetCategorySerializer,
    CategoryListSerializer
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

    # Configuration for filtering and searching
    filter_backends = [DjangoFilterBackend, SearchFilter]

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