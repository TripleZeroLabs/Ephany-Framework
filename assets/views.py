# assets/views.py

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter
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
    # ... (content remains the same)
    queryset = Manufacturer.objects.all()
    serializer_class = ManufacturerSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = {
        'name': ['exact', 'iexact', 'icontains']
    }


class AssetCategoryViewSet(viewsets.ModelViewSet):
    # ... (content remains the same)
    queryset = AssetCategory.objects.all()
    serializer_class = AssetCategorySerializer


class AssetFileViewSet(viewsets.ModelViewSet):
    # ... (content remains the same)
    queryset = AssetFile.objects.all()
    serializer_class = AssetFileSerializer


class AssetViewSet(viewsets.ModelViewSet):
    queryset = Asset.objects.all()
    serializer_class = AssetSerializer

    # Configuration for filtering and searching
    filter_backends = [DjangoFilterBackend, SearchFilter]

    # Fielded filtering (allows exact/partial matches on specific fields)
    filterset_fields = {
        "type_id": ["exact", "iexact"],
        "manufacturer__name": ["exact", "iexact", "icontains"],
        "model": ["exact", "iexact", "icontains"],
        "name": ["icontains", "exact"],
        "description": ["icontains", "exact"],
        # --- NEW: Enable filtering by the category name string ---
        "category__name": ["exact"],
        # --------------------------------------------------------
    }

    # Keyword search (allows searching across these fields simultaneously)
    search_fields = [
        "name",
        "description",
        "model",
        "manufacturer__name",
    ]

    @action(detail=False, methods=['get'])
    def all_categories(self, request):
        """
        Custom action to return a non-paginated, complete list of unique
        asset categories for filter dropdowns in the frontend.
        """
        # Retrieve all categories and order them alphabetically.
        categories = AssetCategory.objects.all().order_by('name')

        # Serialize the list using a dedicated serializer (CategoryListSerializer)
        serializer = CategoryListSerializer(categories, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)