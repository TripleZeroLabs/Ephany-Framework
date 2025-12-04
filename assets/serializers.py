from rest_framework import serializers
from .models import Asset, Manufacturer

class ManufacturerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Manufacturer
        fields = '__all__'

class AssetSerializer(serializers.ModelSerializer):
    # If you want to see the manufacturer name instead of just the ID
    manufacturer_name = serializers.ReadOnlyField(source='manufacturer.name')

    class Meta:
        model = Asset
        fields = ['id', 'unique_id', 'manufacturer', 'manufacturer_name', 'model', 'description']
