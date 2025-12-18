from rest_framework import serializers
from .models import Project, Snapshot, AssetInstance
from assets.serializers import AssetSerializer


class AssetInstanceSerializer(serializers.ModelSerializer):
    asset_details = AssetSerializer(source='asset', read_only=True)

    class Meta:
        model = AssetInstance
        fields = [
            'id',
            'snapshot',
            'asset',
            'asset_details',
            'location',
            'custom_fields',
            'created_at',
            'updated_at'
        ]


class SnapshotSerializer(serializers.ModelSerializer):
    instance_count = serializers.IntegerField(source='instances.count', read_only=True)

    class Meta:
        model = Snapshot
        fields = ['id', 'project', 'name', 'date', 'instance_count', 'created_at']


class ProjectSerializer(serializers.ModelSerializer):
    snapshot_count = serializers.IntegerField(source='snapshots.count', read_only=True)

    class Meta:
        model = Project
        fields = ['id', 'job_id', 'name', 'description', 'portfolio_img', 'snapshot_count', 'created_at']