from rest_framework import viewsets
from django_filters.rest_framework import DjangoFilterBackend
from .models import Manufacturer, Asset, AssetFile
from .serializers import ManufacturerSerializer, AssetSerializer, AssetFileSerializer


class ManufacturerViewSet(viewsets.ModelViewSet):
    queryset = Manufacturer.objects.all()
    serializer_class = ManufacturerSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = {
        'name': ['exact', 'iexact', 'icontains']
    }


class AssetFileViewSet(viewsets.ModelViewSet):
    queryset = AssetFile.objects.all()
    serializer_class = AssetFileSerializer


class AssetViewSet(viewsets.ModelViewSet):
    queryset = Asset.objects.all()
    serializer_class = AssetSerializer
    filter_backends = [DjangoFilterBackend]
    # This automatically enables ?unique_id=...&manufacturer=...&model=...
    filterset_fields = {
        'unique_id': ['exact', 'iexact'],
        'manufacturer__name': ['exact', 'iexact', 'icontains'],
        'model': ['exact', 'iexact', 'icontains'],
    }
