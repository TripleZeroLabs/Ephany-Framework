import json
from rest_framework import serializers
from .models import Project, Site, Snapshot, AssetInstance, AssetComponentInstance
from assets.serializers import AssetSerializer, AssetComponentSerializer
from assets.models import AssetComponent


class SiteSerializer(serializers.ModelSerializer):
    project_count = serializers.IntegerField(source='projects.count', read_only=True)

    class Meta:
        model = Site
        fields = ['id', 'site_id', 'name', 'project_count', 'created_at', 'updated_at']


class AssetComponentInstanceSerializer(serializers.ModelSerializer):
    """
    Serializer for AssetComponentInstance.

    Handles the linking of optional AssetComponents to specific AssetInstances.
    Uses SerializerMethodField for 'asset_component' to prevent circular import
    issues and ensure full nested serialization of the component definition.
    """
    # Write-only fields for creating relationships
    asset_instance_id = serializers.PrimaryKeyRelatedField(
        queryset=AssetInstance.objects.all(),
        source='asset_instance',
        write_only=True,
        required=False
    )
    asset_component_id = serializers.PrimaryKeyRelatedField(
        queryset=AssetComponent.objects.all(),
        source='asset_component',
        write_only=True
    )

    # Custom method field to force nested serialization of the library component
    # This avoids "Integer ID" returns caused by circular app dependencies
    asset_component = serializers.SerializerMethodField()

    # Read-only convenience fields for flat data access
    component_name = serializers.CharField(source='asset_component.child_asset.name', read_only=True)
    component_type_id = serializers.CharField(source='asset_component.child_asset.type_id', read_only=True)
    component_quantity = serializers.IntegerField(source='asset_component.quantity', read_only=True)
    asset_instance_asset_name = serializers.CharField(source='asset_instance.asset.name', read_only=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'asset_instance_id' in self.fields:
            # Enforce requirement only when used outside of a nested AssetInstance context
            if not hasattr(self, 'parent') or self.parent is None:
                self.fields['asset_instance_id'].required = True

    def get_asset_component(self, obj):
        """
        Manually serializes the related AssetComponent.
        Imports the serializer locally to resolve circular dependencies between
        the 'assets' and 'projects' applications.
        """
        if not obj.asset_component:
            return None

        from assets.serializers import AssetComponentSerializer
        return AssetComponentSerializer(obj.asset_component, context=self.context).data

    def validate(self, attrs):
        """
        Validates business logic for component assignment.
        1. Validates that the component belongs to the correct parent asset.
        2. Validates that the component is marked as optional (can_add_per_instance).
        """
        asset_instance = attrs.get('asset_instance')
        asset_component = attrs.get('asset_component')

        # Fallback logic to retrieve asset_instance from parent context if not provided directly
        if not asset_instance:
            if self.instance:
                asset_instance = self.instance.asset_instance
            elif hasattr(self, 'parent') and self.parent and hasattr(self.parent, 'instance'):
                asset_instance = getattr(self.parent.instance, 'asset_instance', None) if hasattr(self.parent,
                                                                                                  'instance') else None

        if not asset_instance and not hasattr(self, 'parent'):
            raise serializers.ValidationError({
                'asset_instance_id': 'This field is required when creating an AssetComponentInstance.'
            })

        if asset_instance and asset_component:
            if asset_component.parent_asset != asset_instance.asset:
                raise serializers.ValidationError({
                    'asset_component_id': (
                        f"Component mismatch: belongs to '{asset_component.parent_asset.name}', "
                        f"but instance is for '{asset_instance.asset.name}'."
                    )
                })

            if not asset_component.can_add_per_instance:
                raise serializers.ValidationError({
                    'asset_component_id': "Only components with 'can_add_per_instance' set to True can be added."
                })

        return attrs

    class Meta:
        model = AssetComponentInstance
        fields = [
            'id',
            'asset_instance_id',
            'asset_component_id',
            'asset_component',
            'component_name',
            'component_type_id',
            'component_quantity',
            'asset_instance_asset_name',
            'quantity'
        ]

class AssetInstanceSerializer(serializers.ModelSerializer):
    """
    Serializer for AssetInstance.

    Includes detailed asset library information and a collection of
    optional component instances selected for this specific snapshot.
    """
    asset_details = AssetSerializer(source='asset', read_only=True)
    optional_components = AssetComponentInstanceSerializer(
        many=True,
        read_only=True
    )
    optional_component_data = serializers.ListField(
        child=serializers.DictField(),
        write_only=True,
        required=False
    )

    class Meta:
        model = AssetInstance
        fields = [
            'id',
            'snapshot',
            'asset',
            'instance_id',
            'asset_details',
            'location',
            'custom_fields',
            'optional_components',
            'optional_component_data',
            'created_at',
            'updated_at'
        ]

    def validate_optional_component_data(self, value):
        """
        Validates the batch of optional components provided during creation or update.
        Ensures all IDs exist and are valid children of the assigned parent asset.
        """
        if not value:
            return value

        from assets.models import AssetComponent

        asset = None
        if self.instance:
            asset = self.instance.asset
        elif 'asset' in self.initial_data:
            asset_id = self.initial_data['asset']
            from assets.models import Asset
            try:
                asset = Asset.objects.get(pk=asset_id)
            except Asset.DoesNotExist:
                raise serializers.ValidationError("Invalid asset ID.")

        if not asset:
            return value

        component_ids = [comp_data.get('asset_component_id') for comp_data in value if
                         comp_data.get('asset_component_id')]

        components = AssetComponent.objects.filter(
            pk__in=component_ids,
            parent_asset=asset
        )

        found_ids = set(components.values_list('pk', flat=True))
        requested_ids = set(component_ids)

        if found_ids != requested_ids:
            missing = requested_ids - found_ids
            raise serializers.ValidationError(
                f"Components not found or incompatible with parent asset: {missing}"
            )

        non_optional = components.filter(can_add_per_instance=False)
        if non_optional.exists():
            raise serializers.ValidationError(
                f"Required components cannot be added as optional instances: {list(non_optional.values_list('id', flat=True))}"
            )

        return value

    def create(self, validated_data):
        optional_component_data = validated_data.pop('optional_component_data', [])
        instance = super().create(validated_data)

        for comp_data in optional_component_data:
            AssetComponentInstance.objects.create(
                asset_instance=instance,
                asset_component_id=comp_data['asset_component_id'],
                quantity=comp_data.get('quantity', 1)
            )

        return instance

    def update(self, instance, validated_data):
        optional_component_data = validated_data.pop('optional_component_data', None)
        instance = super().update(instance, validated_data)

        if optional_component_data is not None:
            instance.optional_components.all().delete()
            for comp_data in optional_component_data:
                AssetComponentInstance.objects.create(
                    asset_instance=instance,
                    asset_component_id=comp_data['asset_component_id'],
                    quantity=comp_data.get('quantity', 1)
                )

        return instance


class SnapshotSerializer(serializers.ModelSerializer):
    """
    Serializer for Project Snapshots.
    Includes an aggregated count of all asset instances within the snapshot.
    """
    instance_count = serializers.IntegerField(source='instances.count', read_only=True)

    class Meta:
        model = Snapshot
        fields = ['id', 'project', 'name', 'date', 'instance_count', 'created_at']


class ProjectSnapshotSerializer(serializers.ModelSerializer):
    """
    Lightweight Snapshot representation used within Project list views.
    """

    class Meta:
        model = Snapshot
        fields = ['id', 'name', 'date']


class ProjectSerializer(serializers.ModelSerializer):
    """
    Primary Serializer for Project data.
    Provides nested snapshot history and aggregated snapshot counts.
    """
    snapshot_count = serializers.IntegerField(source='snapshots.count', read_only=True)
    snapshots = ProjectSnapshotSerializer(many=True, read_only=True)
    site_detail = SiteSerializer(source='site', read_only=True)

    class Meta:
        model = Project
        fields = [
            'id',
            'job_id',
            'name',
            'description',
            'portfolio_img',
            # Site
            'site',
            'site_detail',
            # Address
            'address_line1',
            'address_line2',
            'city',
            'state',
            'zip_code',
            'country',
            'latitude',
            'longitude',
            # Project details
            'go_live_date',
            'status',
            'custom_fields',
            # Meta
            'snapshot_count',
            'created_at',
            'updated_at',
            'snapshots',
        ]