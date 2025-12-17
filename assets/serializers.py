from rest_framework import serializers
from .models import (
    Manufacturer,
    Asset,
    AssetFile,
    AssetAttribute,
    AssetCategory,
)
from ephany_framework.utils import UnitConverter


class ManufacturerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Manufacturer
        fields = ['id', 'name']


class AssetCategorySerializer(serializers.ModelSerializer):
    """
    Basic serializer for CRUD operations on AssetCategory records.
    """
    class Meta:
        model = AssetCategory
        fields = ['id', 'name']


class CategoryListSerializer(serializers.ModelSerializer):
    """
    Minimal serializer used by custom view actions (e.g., all_categories)
    to return a simple list of category IDs and names, ideal for frontend
    filter dropdowns.
    """
    class Meta:
        model = AssetCategory
        fields = ['id', 'name']


class AssetFileSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source='get_category_display', read_only=True)

    class Meta:
        model = AssetFile
        fields = ['id', 'file', 'category', 'category_display', 'uploaded_at']


class AssetSerializer(serializers.ModelSerializer):
    """
    Primary serializer for Asset instances, handling complex logic like
    unit conversion and custom field validation/representation.
    """
    manufacturer_name = serializers.CharField(source='manufacturer.name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    # If you want the full category object as read-only, you can optionally expose:
    # category_detail = AssetCategorySerializer(source='category', read_only=True)

    files = AssetFileSerializer(many=True, read_only=True)
    file_ids = serializers.PrimaryKeyRelatedField(
        queryset=AssetFile.objects.all(),
        source='files',
        many=True,
        write_only=True,
        required=False
    )

    # Input field to specify units for dimensional data during write operations.
    input_units = serializers.DictField(
        required=False,
        write_only=True,
        help_text="Required if providing dimensions. Example: {'length': 'ft', 'mass': 'lb'}"
    )

    class Meta:
        model = Asset
        fields = [
            'id',
            'type_id',
            'manufacturer',
            'manufacturer_name',
            'category',
            'category_name',
            # 'category_detail',
            'model',
            'name',
            'description',
            'url',
            'overall_height',
            'overall_width',
            'overall_depth',
            'custom_fields',
            'files',
            'file_ids',
            'input_units',
        ]

    def _get_user_units(self):
        """Helper to retrieve user-defined unit preferences for output representation."""
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
        """Maps an Autodesk SpecTypeId string to an internal unit category (e.g., 'length')."""
        SPECS = {
            'autodesk.spec.aec:length-2.0.0': 'length',
            'autodesk.spec.aec:distance-1.0.0': 'length',
            'autodesk.spec.aec:area-2.0.0': 'area',
            'autodesk.spec.aec:volume-2.0.0': 'volume',
            'autodesk.spec.aec:mass-2.0.0': 'mass',
            'autodesk.spec.aec:massDensity-2.0.0': 'mass',
        }
        return SPECS.get(spec_type)

    def create(self, validated_data):
        """Removes non-model fields (input_units) before creating the model instance."""
        validated_data.pop('input_units', None)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """
        Overrides update to perform a MERGE on the custom_fields JSONField
        rather than overwriting the entire dictionary.
        """
        new_custom_fields = validated_data.pop('custom_fields', None)
        validated_data.pop('input_units', None)

        instance = super().update(instance, validated_data)

        if new_custom_fields is not None:
            existing_data = instance.custom_fields or {}
            existing_data.update(new_custom_fields)
            instance.custom_fields = existing_data
            instance.save()

        return instance

    def to_representation(self, instance):
        """
        Converts stored metric data (READ) into the user's preferred display units.
        """
        ret = super().to_representation(instance)
        user_units = self._get_user_units()

        # 1. Convert Standard Fields (Length)
        for field in ['overall_height', 'overall_width', 'overall_depth']:
            if field in ret and ret[field] is not None:
                ret[field] = UnitConverter.from_storage(
                    ret[field],
                    user_units['length'],
                    'length'
                )

        # 2. Convert Custom Fields (All Types)
        if instance.custom_fields:
            attributes = AssetAttribute.objects.filter(name__in=instance.custom_fields.keys())
            attr_map = {attr.name: attr.unit_type for attr in attributes}

            new_custom_fields = instance.custom_fields.copy()

            for key, value in new_custom_fields.items():
                spec_type = attr_map.get(key)
                category = self._get_spec_category(spec_type)

                if category and isinstance(value, (int, float)):
                    target_unit = user_units.get(category)
                    if target_unit:
                        new_custom_fields[key] = UnitConverter.from_storage(
                            value,
                            target_unit,
                            category
                        )

            ret['custom_fields'] = new_custom_fields

        ret['_display_units'] = user_units
        return ret

    def to_internal_value(self, data):
        """
        Converts dimensional data from the user-specified input units (WRITE)
        into the system's metric storage format.
        """
        mutable_data = data.copy()
        input_units = mutable_data.get('input_units')

        required_categories = set()

        # 1. Identify Categories involved in Standard Fields
        for field in ['overall_height', 'overall_width', 'overall_depth']:
            if field in mutable_data and mutable_data[field] is not None:
                required_categories.add('length')

        # 2. Identify Categories involved in Custom Fields
        custom_fields = mutable_data.get('custom_fields')
        custom_attr_map = {}

        if custom_fields and isinstance(custom_fields, dict):
            attributes = AssetAttribute.objects.filter(name__in=custom_fields.keys())
            for attr in attributes:
                category = self._get_spec_category(attr.unit_type)
                if category:
                    if custom_fields.get(attr.name) is not None:
                        required_categories.add(category)
                    custom_attr_map[attr.name] = category

        # 3. Validate input_units presence and correctness
        if required_categories:
            if not input_units or not isinstance(input_units, dict):
                raise serializers.ValidationError({
                    "input_units": (
                        "This field is required because you provided dimensional data. "
                        f"Required units for: {', '.join(required_categories)}"
                    )
                })

            missing_units = [cat for cat in required_categories if cat not in input_units]
            if missing_units:
                raise serializers.ValidationError({
                    "input_units": f"Missing unit definitions for: {', '.join(missing_units)}"
                })

            for cat, unit_str in input_units.items():
                if unit_str not in UnitConverter.TO_BASE.get(cat, {}):
                    if cat in required_categories:
                        valid_opts = list(UnitConverter.TO_BASE[cat].keys())
                        raise serializers.ValidationError({
                            "input_units": (
                                f"Invalid unit '{unit_str}' for category '{cat}'. "
                                f"Valid options: {valid_opts}"
                            )
                        })

        # 4. Perform Conversion (Input Units -> Storage Units)
        if required_categories:
            # Standard fields
            for field in ['overall_height', 'overall_width', 'overall_depth']:
                if field in mutable_data and mutable_data[field] is not None:
                    mutable_data[field] = UnitConverter.to_storage(
                        mutable_data[field],
                        input_units['length'],
                        'length'
                    )

            # Custom fields
            if custom_fields:
                new_custom_fields = custom_fields.copy()
                for key, value in new_custom_fields.items():
                    category = custom_attr_map.get(key)
                    if category and value is not None:
                        new_custom_fields[key] = UnitConverter.to_storage(
                            value,
                            input_units[category],
                            category
                        )
                mutable_data['custom_fields'] = new_custom_fields

        return super().to_internal_value(mutable_data)