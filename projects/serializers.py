from rest_framework import serializers
from .models import Project, Snapshot

class SnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = Snapshot
        fields = '__all__'

class ProjectSerializer(serializers.ModelSerializer):
    # Optional: Include snapshots in the project detail
    # snapshots = SnapshotSerializer(many=True, read_only=True)

    class Meta:
        model = Project
        fields = '__all__'