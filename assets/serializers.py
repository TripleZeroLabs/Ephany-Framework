import json
from typing import Any, Dict
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from .models import (
    Manufacturer,
    Asset,
    AssetFile,
    AssetAttribute,
    AssetAttributeChoice,
    AssetCategory,
    AssetComponent,
    Prototype,
    PrototypeItem,
    Vendor,
    VendorProduct,
)
from ephany_framework.utils import UnitConverter


class ManufacturerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Manufacturer
        fields = ['id', 'name', 'url', 'logo']


class AssetCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetCategory
        fields = ['id', 'name', 'description']


class AssetAttributeChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetAttributeChoice
        fields = ['id', 'value', 'order']

    def validate(self, attrs):
        # On create, 'attribute' comes from the URL/view context via perform_create.
        # On update, check the existing instance's attribute.
        attribute = None

        if self.instance:
            attribute = self.instance.attribute
        else:
            # For create, the attribute is injected by the viewset via the serializer context
            attribute = self.context.get('attribute')

        if attribute and attribute.data_type != AssetAttribute.AttributeType.CHOICE:
            raise serializers.ValidationError(
                f"Choices can only be added to attributes with data type 'Picklist'. "
                f"'{attribute.name}' is of type '{attribute.get_data_type_display()}'."
            )
        return attrs

    def get_inline_instances(self, request, obj=None):
        choice_types = {
            AssetAttribute.AttributeType.CHOICE,
            AssetAttribute.AttributeType.MULTI_CHOICE,
        }
        if obj and obj.data_type in choice_types:
            return super().get_inline_instances(request, obj)
        return []

    def choice_count(self, obj):
        choice_types = {
            AssetAttribute.AttributeType.CHOICE,
            AssetAttribute.AttributeType.MULTI_CHOICE,
        }
        if obj.data_type in choice_types:
            return obj.choices.count()
        return '—'
    choice_count.short_description = 'Choices'


class AssetAttributeSerializer(serializers.ModelSerializer):
    choices = AssetAttributeChoiceSerializer(many=True, read_only=True)

    class Meta:
        model = AssetAttribute
        fields = ['id', 'name', 'scope', 'data_type', 'unit_type', 'choices']
        read_only_fields = ['choices']


class VendorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vendor
        fields = ['id', 'name', 'website', 'contact_email']


class VendorProductSerializer(serializers.ModelSerializer):
    asset_id = serializers.PrimaryKeyRelatedField(
        queryset=Asset.objects.all(),
        source='asset',
        write_only=True
    )
    vendor_id = serializers.PrimaryKeyRelatedField(
        queryset=Vendor.objects.all(),
        source='vendor',
        write_only=True
    )
    asset_name = serializers.CharField(source='asset.name', read_only=True)
    vendor_name = serializers.CharField(source='vendor.name', read_only=True)

    class Meta:
        model = VendorProduct
        fields = [
            'id', 'asset_id', 'vendor_id', 'asset_name', 'vendor_name',
            'sku', 'cost', 'lead_time_days', 'url',
        ]


class CategoryListSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetCategory
        fields = ['id', 'name']


class AssetFileSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source='get_category_display', read_only=True)

    class Meta:
        model = AssetFile
        fields = ['id', 'file', 'category', 'category_display', 'uploaded_at']


class NestedAssetSerializer(serializers.ModelSerializer):
    """
    Simplified Asset serializer to avoid recursion in AssetComponentSerializer.
    """
    manufacturer = ManufacturerSerializer(read_only=True)
    category = AssetCategorySerializer(read_only=True)

    class Meta:
        model = Asset
        fields = [
            'id', 'type_id', 'manufacturer', 'category', 'model', 'name',
            'description', 'url', 'catalog_img', 'overall_height',
            'overall_width', 'overall_depth', 'custom_fields'
        ]


class AssetComponentSerializer(serializers.ModelSerializer):
    """
    Serializer for AssetComponent (through model for assemblies).
    """
    child_asset_id = serializers.PrimaryKeyRelatedField(
        queryset=Asset.objects.all(),
        source='child_asset',
        write_only=True
    )
    child_asset = NestedAssetSerializer(read_only=True)

    class Meta:
        model = AssetComponent
        fields = ['id', 'child_asset_id', 'child_asset', 'quantity_required', 'can_add_per_instance']


class AssetSerializer(serializers.ModelSerializer):
    """
    Primary serializer for Asset instances.
    Handles unit conversion (metric/imperial) based on user settings.
    """
    # --- READ FIELDS ---
    manufacturer = ManufacturerSerializer(read_only=True)
    category = AssetCategorySerializer(read_only=True)
    manufacturer_name = serializers.CharField(source='manufacturer.name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)

    # --- WRITE FIELDS ---
    manufacturer_id = serializers.PrimaryKeyRelatedField(
        queryset=Manufacturer.objects.all(),
        source='manufacturer',
        write_only=True,
        required=False,
        allow_null=True
    )
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=AssetCategory.objects.all(),
        source='category',
        write_only=True,
        required=False,
        allow_null=True
    )

    # --- FILES ---
    files = AssetFileSerializer(many=True, read_only=True)
    file_ids = serializers.PrimaryKeyRelatedField(
        queryset=AssetFile.objects.all(),
        source='files',
        many=True,
        write_only=True,
        required=False
    )

    # --- ASSEMBLY COMPONENTS ---
    components = AssetComponentSerializer(many=True, read_only=True)
    component_data = serializers.ListField(
        child=serializers.DictField(),
        write_only=True,
        required=False,
        help_text="List of components with 'child_asset_id', 'quantity_required', and optional 'can_add_per_instance'. Example: [{'child_asset_id': 1, 'quantity': 2, 'can_add_per_instance': False}]"
    )

    # --- UNITS ---
    input_units = serializers.DictField(
        required=False,
        write_only=True,
        help_text="Required if providing dimensions. Example: {'length': 'ft'}"
    )

    # Explicitly define custom_fields
    custom_fields = serializers.JSONField(required=False, allow_null=True)

    class Meta:
        model = Asset
        fields = [
            'id',
            'type_id',
            'manufacturer',
            'manufacturer_name',
            'category',
            'category_name',
            'manufacturer_id',
            'category_id',
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
            'components',
            'component_data',
        ]

    def _get_user_units(self):
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
        SPECS = {
            'autodesk.spec.aec:length-2.0.0': 'length',
            'autodesk.spec.aec:distance-1.0.0': 'length',
            'autodesk.spec.aec:area-2.0.0': 'area',
            'autodesk.spec.aec:volume-2.0.0': 'volume',
            'autodesk.spec.aec:mass-2.0.0': 'mass',
            'autodesk.spec.aec:massDensity-2.0.0': 'mass',
        }
        return SPECS.get(spec_type)

    def validate_custom_fields(self, value):
        """
        Field-level validation for custom_fields.
        Ensures all keys exist as AssetAttributes in the database.
        """
        if not value or not isinstance(value, dict):
            return value

        input_keys = set(value.keys())

        # Query DB for these keys to see which ones exist
        valid_attributes = set(
            AssetAttribute.objects.filter(name__in=input_keys).values_list('name', flat=True)
        )

        invalid_keys = input_keys - valid_attributes

        if invalid_keys:
            sorted_invalid = sorted(list(invalid_keys))
            raise serializers.ValidationError(
                f"Invalid custom fields detected: {', '.join(sorted_invalid)}. "
                "You must define these as AssetAttributes in the system before using them."
            )

        return value

    def validate_component_data(self, value):
        """Validate component_data to prevent self-referential components."""
        if not value:
            return value
        
        # Get the asset ID (either from existing instance or from initial_data)
        asset_id = None
        if self.instance:
            asset_id = self.instance.pk
        elif 'id' in self.initial_data:
            asset_id = self.initial_data['id']
        
        # If we're creating a new asset, we can't validate self-reference yet
        # (the asset doesn't exist yet), but we can validate after creation
        # For updates, check for self-reference
        if asset_id:
            component_ids = [
                comp_data.get('child_asset_id') 
                for comp_data in value 
                if comp_data.get('child_asset_id')
            ]
            # Check if any component is the same as the parent asset
            if asset_id in component_ids:
                raise serializers.ValidationError(
                    "An asset cannot be a component of itself. "
                    f"Asset ID {asset_id} cannot be added as its own component."
                )
        
        return value

    def create(self, validated_data):
        component_data = validated_data.pop('component_data', [])
        validated_data.pop('input_units', None)
        
        asset = super().create(validated_data)
        
        # Create component relationships
        # Validation will happen in AssetComponent.save() via full_clean()
        for comp_data in component_data:
            # Additional check: prevent self-reference
            if comp_data.get('child_asset_id') == asset.pk:
                raise serializers.ValidationError({
                    'component_data': f"An asset cannot be a component of itself. Asset '{asset.name}' (ID: {asset.pk}) cannot be added as its own component."
                })
            
            AssetComponent.objects.create(
                parent_asset=asset,
                child_asset_id=comp_data['child_asset_id'],
                quantity_required=comp_data.get('quantity_required', 1),
                can_add_per_instance=comp_data.get('can_add_per_instance', False)
            )
        
        return asset

    def update(self, instance, validated_data):
        new_custom_fields = validated_data.pop('custom_fields', None)
        component_data = validated_data.pop('component_data', None)
        validated_data.pop('input_units', None)

        instance = super().update(instance, validated_data)

        if new_custom_fields is not None:
            existing_data = instance.custom_fields or {}
            existing_data.update(new_custom_fields)
            instance.custom_fields = existing_data
            instance.save()

        # Update component relationships if provided
        if component_data is not None:
            # Delete existing components
            instance.components.all().delete()
            # Create new components
            # Validation will happen in AssetComponent.save() via full_clean()
            for comp_data in component_data:
                # Additional check: prevent self-reference
                if comp_data.get('child_asset_id') == instance.pk:
                    raise serializers.ValidationError({
                        'component_data': f"An asset cannot be a component of itself. Asset '{instance.name}' (ID: {instance.pk}) cannot be added as its own component."
                    })
                
                AssetComponent.objects.create(
                    parent_asset=instance,
                    child_asset_id=comp_data['child_asset_id'],
                    quantity_required=comp_data.get('quantity_required', 1),
                    can_add_per_instance=comp_data.get('can_add_per_instance', False)
                )

        return instance

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        user_units = self._get_user_units()

        for field in ['overall_height', 'overall_width', 'overall_depth']:
            if field in ret and ret[field] is not None:
                ret[field] = UnitConverter.from_storage(
                    ret[field],
                    user_units['length'],
                    'length'
                )

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
        mutable_data: Dict[str, Any] = {}

        if hasattr(data, 'dict'):
            mutable_data = dict(data.dict())
        else:
            mutable_data = dict(data)

        request = self.context.get('request')
        if request and request.FILES:
            for key, file_obj in request.FILES.items():
                mutable_data[key] = file_obj

        # Helper to parse JSON strings from Multipart Forms
        if 'custom_fields' in mutable_data and isinstance(mutable_data['custom_fields'], str):
            try:
                mutable_data['custom_fields'] = json.loads(mutable_data['custom_fields'])
            except ValueError:
                pass

        if 'input_units' in mutable_data and isinstance(mutable_data['input_units'], str):
            try:
                mutable_data['input_units'] = json.loads(mutable_data['input_units'])
            except ValueError:
                pass

        units_payload = mutable_data.get('input_units')
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
            if not units_payload or not isinstance(units_payload, dict):
                raise serializers.ValidationError({
                    "input_units": f"Required units for: {', '.join(required_categories)}"
                })

            for cat, unit_str in units_payload.items():
                if unit_str not in UnitConverter.TO_BASE.get(cat, {}):
                    if cat in required_categories:
                        valid_opts = list(UnitConverter.TO_BASE[cat].keys())
                        raise serializers.ValidationError({
                            "input_units": f"Invalid unit '{unit_str}' for category '{cat}'."
                        })

            for field in ['overall_height', 'overall_width', 'overall_depth']:
                if field in mutable_data and mutable_data[field] is not None:
                    mutable_data[field] = UnitConverter.to_storage(
                        mutable_data[field],
                        units_payload['length'],
                        'length'
                    )

            if custom_fields:
                new_custom_fields = custom_fields.copy()
                for key, value in new_custom_fields.items():
                    category = custom_attr_map.get(key)
                    if category and value is not None and category in units_payload:
                        new_custom_fields[key] = UnitConverter.to_storage(
                            value,
                            units_payload[category],
                            category
                        )
                mutable_data['custom_fields'] = new_custom_fields

        return super().to_internal_value(mutable_data)

class PrototypeItemSerializer(serializers.ModelSerializer):
    """One line of a standard: this asset, this many."""
    asset_id = serializers.PrimaryKeyRelatedField(
        queryset=Asset.objects.all(), source="asset", write_only=True
    )
    type_id = serializers.CharField(source="asset.type_id", read_only=True)
    asset_name = serializers.CharField(source="asset.name", read_only=True)

    class Meta:
        model = PrototypeItem
        fields = [
            "id", "prototype", "asset", "asset_id", "type_id", "asset_name",
            "quantity", "is_required", "notes",
        ]
        read_only_fields = ["asset"]

    def validate(self, attrs):
        """
        Surface the model's immutability rule as a 400 rather than a 500.

        PrototypeItem.save() calls full_clean(), which raises Django's
        ValidationError. DRF does not translate that, so without this the API
        would answer a perfectly understandable refusal with a server error.
        """
        from django.core.exceptions import ValidationError as DjangoValidationError

        candidate = PrototypeItem(
            **{**{f: getattr(self.instance, f, None) for f in ("prototype", "asset")}, **attrs}
        )
        if self.instance:
            candidate.pk = self.instance.pk
        try:
            candidate.clean()
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.messages)
        return attrs


class PrototypeSerializer(serializers.ModelSerializer):
    """
    A versioned standard kit of parts.

    `code` identifies the standard, `version` the revision. Two rows sharing a
    code are two revisions of one standard, not duplicates.
    """
    items = PrototypeItemSerializer(many=True, read_only=True)
    item_count = serializers.IntegerField(source="items.count", read_only=True)
    total_units = serializers.SerializerMethodField()
    is_locked = serializers.BooleanField(
        read_only=True,
        help_text="True once a snapshot references this version, which freezes "
                  "its items. Publish a new version instead of editing it.",
    )
    snapshot_count = serializers.IntegerField(source="snapshots.count", read_only=True)

    class Meta:
        model = Prototype
        fields = [
            "id", "code", "version", "name", "description", "is_active",
            "items", "item_count", "total_units", "is_locked", "snapshot_count",
            "created_at", "updated_at",
        ]

    @extend_schema_field(serializers.IntegerField)
    def get_total_units(self, obj):
        """How many physical units this standard calls for in total."""
        return sum(item.quantity for item in obj.items.all())
