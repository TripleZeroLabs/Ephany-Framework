from django.shortcuts import render
from rest_framework import viewsets
from .models import Asset, Manufacturer
from .serializers import AssetSerializer, ManufacturerSerializer

class ManufacturerViewSet(viewsets.ModelViewSet):
    queryset = Manufacturer.objects.all()
    serializer_class = ManufacturerSerializer

class AssetViewSet(viewsets.ModelViewSet):
    queryset = Asset.objects.all()
    serializer_class = AssetSerializer