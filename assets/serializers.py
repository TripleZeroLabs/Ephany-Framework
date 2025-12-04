from rest_framework import serializers
from .models import Manufacturer, Asset, AssetFile

class ManufacturerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Manufacturer
        fields = ['id', 'name']


class AssetFileSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source='get_category_display', read_only=True)

    class Meta:
        model = AssetFile
        fields = ['id', 'file', 'category', 'category_display', 'uploaded_at']


class AssetSerializer(serializers.ModelSerializer):
    manufacturer_name = serializers.CharField(source='manufacturer.name', read_only=True)
    # Use AssetFileSerializer for read operations (nested representation)
    files = AssetFileSerializer(many=True, read_only=True)
    # Use PrimaryKeyRelatedField for write operations (accepts IDs)
    file_ids = serializers.PrimaryKeyRelatedField(
        queryset=AssetFile.objects.all(),
        source='files',
        many=True,
        write_only=True,
        required=False
    )

    class Meta:
        model = Asset
        fields = [
            'id',
            'unique_id',
            'manufacturer',
            'manufacturer_name',
            'model',
            'description',
            'url',
            'files',
            'file_ids']
