from rest_framework import serializers
from .models import Manufacturer, Asset, AssetFile, AssetAttribute
from ephany_framework.utils import UnitConverter

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
    files = AssetFileSerializer(many=True, read_only=True)
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
            'overall_height',
            'overall_width',
            'overall_depth',
            'custom_fields',
            'files',
            'file_ids'
        ]

    def _get_user_units(self):
        """Helper to get all user unit preferences"""
        defaults = {'length': 'mm', 'area': 'sq_m', 'volume': 'cu_m', 'mass': 'kg'}
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            if hasattr(request.user, 'settings'):
                s = request.user.settings
                return {
                    'length': s.length_unit,
                    'area': s.area_unit,
                    'volume': s.volume_unit,
                    'mass': s.mass_unit
                }
        return defaults

    def _get_spec_category(self, spec_type):
        """Map Revit SpecType to internal category"""
        # Ideally this map lives in constants or utils
        SPECS = {
            'autodesk.spec.aec:length-2.0.0': 'length',
            'autodesk.spec.aec:distance-1.0.0': 'length',
            'autodesk.spec.aec:area-2.0.0': 'area',
            'autodesk.spec.aec:volume-2.0.0': 'volume',
            'autodesk.spec.aec:mass-2.0.0': 'mass',
            'autodesk.spec.aec:massDensity-2.0.0': 'mass' # Note: we treat density as mass for simple scaling if needed, or skip
        }
        return SPECS.get(spec_type)

    def update(self, instance, validated_data):
        # ... (Merge logic unchanged) ...
        new_custom_fields = validated_data.pop('custom_fields', None)
        instance = super().update(instance, validated_data)
        
        if new_custom_fields is not None:
            existing_data = instance.custom_fields or {}
            existing_data.update(new_custom_fields)
            instance.custom_fields = existing_data
            instance.save()
            
        return instance

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        user_units = self._get_user_units()
        
        # 1. Convert Standard Fields (Length)
        for field in ['overall_height', 'overall_width', 'overall_depth']:
            if field in ret and ret[field] is not None:
                ret[field] = UnitConverter.from_storage(ret[field], user_units['length'], 'length')

        # 2. Convert Custom Fields (All Types)
        if instance.custom_fields:
            attributes = AssetAttribute.objects.filter(name__in=instance.custom_fields.keys())
            attr_map = {attr.name: attr.unit_type for attr in attributes}
            
            new_custom_fields = instance.custom_fields.copy()
            
            for key, value in new_custom_fields.items():
                spec_type = attr_map.get(key)
                category = self._get_spec_category(spec_type)
                
                if category and isinstance(value, (int, float)):
                    # Convert based on category (Length/Area/Volume/Mass)
                    target_unit = user_units.get(category)
                    if target_unit:
                        new_custom_fields[key] = UnitConverter.from_storage(value, target_unit, category)
            
            ret['custom_fields'] = new_custom_fields

        ret['_display_units'] = user_units
        return ret

    def to_internal_value(self, data):
        mutable_data = data.copy()
        user_units = self._get_user_units()

        # 1. Convert Standard Fields (Length)
        for field in ['overall_height', 'overall_width', 'overall_depth']:
            if field in mutable_data and mutable_data[field] is not None:
                try:
                    mutable_data[field] = UnitConverter.to_storage(mutable_data[field], user_units['length'], 'length')
                except (ValueError, TypeError):
                    pass 

        # 2. Convert Custom Fields (All Types)
        if 'custom_fields' in mutable_data and isinstance(mutable_data['custom_fields'], dict):
            custom_fields = mutable_data['custom_fields']
            attributes = AssetAttribute.objects.filter(name__in=custom_fields.keys())
            attr_map = {attr.name: attr.unit_type for attr in attributes}

            for key, value in custom_fields.items():
                spec_type = attr_map.get(key)
                category = self._get_spec_category(spec_type)

                if category and value is not None:
                    try:
                        source_unit = user_units.get(category)
                        if source_unit:
                             custom_fields[key] = UnitConverter.to_storage(value, source_unit, category)
                    except (ValueError, TypeError):
                         pass

            mutable_data['custom_fields'] = custom_fields

        return super().to_internal_value(mutable_data)
