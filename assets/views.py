from rest_framework import viewsets
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from .models import Manufacturer, Asset, AssetCategory, AssetFile
from .serializers import ManufacturerSerializer, AssetSerializer, AssetFileSerializer, AssetCategorySerializer


class ManufacturerViewSet(viewsets.ModelViewSet):
    queryset = Manufacturer.objects.all()
    serializer_class = ManufacturerSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = {
        'name': ['exact', 'iexact', 'icontains']
    }


class AssetCategoryViewSet(viewsets.ModelViewSet):
    queryset = AssetCategory.objects.all()
    serializer_class = AssetCategorySerializer


class AssetFileViewSet(viewsets.ModelViewSet):
    queryset = AssetFile.objects.all()
    serializer_class = AssetFileSerializer


class AssetViewSet(viewsets.ModelViewSet):
    queryset = Asset.objects.all()
    serializer_class = AssetSerializer

    # Enable BOTH:
    # - django-filter fielded filters (?model__icontains=..., etc.)
    # - DRF keyword search (?search=...)
    filter_backends = [DjangoFilterBackend, SearchFilter]

    # Fielded filtering (AND logic across provided fields)
    filterset_fields = {
        "type_id": ["exact", "iexact"],
        "manufacturer__name": ["exact", "iexact", "icontains"],
        "model": ["exact", "iexact", "icontains"],
        "name": ["icontains", "exact"],
        "description": ["icontains", "exact"],
    }

    # Keyword search (OR-ish behavior across these fields)
    # NOTE: use the real model field path for manufacturer name
    search_fields = [
        "name",
        "description",
        "model",
        "manufacturer__name",
    ]
