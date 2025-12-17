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
    """
    Serializer for the Manufacturer model.
    Includes logo and url fields for display on the Manufacturers page.
    """

    class Meta:
        model = Manufacturer
        fields = ['id', 'name', 'url', 'logo']


class AssetCategorySerializer(serializers.ModelSerializer):
    """
    Basic serializer to manage AssetCategory records via the API.
    """

    class Meta:
        model = AssetCategory
        fields = ['id', 'name']


class CategoryListSerializer(serializers.ModelSerializer):
    """
    Minimal serializer used by custom view actions.
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
    Primary serializer for Asset instances.
    Separates Read (Nested Object) from Write (ID) for Manufacturer and Category.
    """
    # --- READ FIELDS (Nested Objects) ---
    # These will output the full object structure (id, name, logo, etc.) on GET requests
    manufacturer = ManufacturerSerializer(read_only=True)
    category = AssetCategorySerializer(read_only=True)

    # We can keep these for backward compatibility if your frontend relies on flattened keys,
    # otherwise they are redundant because 'manufacturer.name' is available in the objects above.
    manufacturer_name = serializers.CharField(source='manufacturer.name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)

    # --- WRITE FIELDS (IDs) ---
    # These accept an ID (integer) on POST/PATCH and save it to the relationship
    manufacturer_id = serializers.PrimaryKeyRelatedField(
        queryset=Manufacturer.objects.all(),
        source='manufacturer',  # Maps this input to the model's 'manufacturer' field
        write_only=True,
        required=False,
        allow_null=True
    )
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=AssetCategory.objects.all(),
        source='category',  # Maps this input to the model's 'category' field
        write_only=True,
        required=False,
        allow_null=True
    )

    # --- FILES HANDLING ---
    files = AssetFileSerializer(many=True, read_only=True)
    file_ids = serializers.PrimaryKeyRelatedField(
        queryset=AssetFile.objects.all(),
        source='files',
        many=True,
        write_only=True,
        required=False
    )

    # --- UNITS HANDLING ---
    input_units = serializers.DictField(
        required=False,
        write_only=True,
        help_text="Required if providing dimensions. Example: {'length': 'ft'}"
    )

    class Meta:
        model = Asset
        fields = [
            'id',
            'type_id',
            # Read fields
            'manufacturer',
            'manufacturer_name',
            'category',
            'category_name',
            # Write fields
            'manufacturer_id',
            'category_id',
            # Standard fields
            'model',
            'name',
            'description',
            'url',
            'catalog_img',
            'overall_height',
            'overall_width',
            'overall_depth',
            'custom_fields',
            'files',
            'file_ids',
            'input_units',
        ]

    def _get_user_units(self):
        """Helper to retrieve user-defined unit preferences."""
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
        """Maps Autodesk SpecTypeId to internal categories."""
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
        validated_data.pop('input_units', None)
        return super().create(validated_data)

    def update(self, instance, validated_data):
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
        ret = super().to_representation(instance)
        user_units = self._get_user_units()

        # 1. Convert Standard Fields
        for field in ['overall_height', 'overall_width', 'overall_depth']:
            if field in ret and ret[field] is not None:
                ret[field] = UnitConverter.from_storage(
                    ret[field],
                    user_units['length'],
                    'length'
                )

        # 2. Convert Custom Fields
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
        if hasattr(data, 'dict'):
            mutable_data = data.dict()
        else:
            mutable_data = dict(data)

        request = self.context.get('request')
        if request and request.FILES:
            for key, file_obj in request.FILES.items():
                mutable_data[key] = file_obj

        input_units = mutable_data.get('input_units')
        required_categories = set()

        for field in ['overall_height', 'overall_width', 'overall_depth']:
            if field in mutable_data and mutable_data[field] is not None:
                required_categories.add('length')

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

        if required_categories:
            if not input_units or not isinstance(input_units, dict):
                raise serializers.ValidationError({
                    "input_units": f"Required units for: {', '.join(required_categories)}"
                })

            for cat, unit_str in input_units.items():
                if unit_str not in UnitConverter.TO_BASE.get(cat, {}):
                    if cat in required_categories:
                        valid_opts = list(UnitConverter.TO_BASE[cat].keys())
                        raise serializers.ValidationError({
                            "input_units": f"Invalid unit '{unit_str}' for category '{cat}'."
                        })

            # Perform Conversion
            for field in ['overall_height', 'overall_width', 'overall_depth']:
                if field in mutable_data and mutable_data[field] is not None:
                    mutable_data[field] = UnitConverter.to_storage(
                        mutable_data[field],
                        input_units['length'],
                        'length'
                    )

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