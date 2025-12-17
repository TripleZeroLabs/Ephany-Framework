from rest_framework import serializers
from .models import Project, Snapshot

class SnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = Snapshot
        fields = ['id', 'project', 'name', 'date', 'created_at']


class ProjectSerializer(serializers.ModelSerializer):
    # Optional: Include the latest snapshot date or count if needed for the table
    snapshot_count = serializers.IntegerField(source='snapshots.count', read_only=True)

    class Meta:
        model = Project
        fields = [
            'id',
            'job_id',
            'name',
            'description',
            'created_at',
            'updated_at',
            'snapshot_count'
        ]