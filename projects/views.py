from rest_framework import viewsets
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from .models import Project, Snapshot, AssetInstance
from .serializers import ProjectSerializer, SnapshotSerializer, AssetInstanceSerializer

class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['job_id', 'name']

class SnapshotViewSet(viewsets.ModelViewSet):
    queryset = Snapshot.objects.all()
    serializer_class = SnapshotSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['project'] # Find snapshots for a project

class AssetInstanceViewSet(viewsets.ModelViewSet):
    queryset = AssetInstance.objects.all()
    serializer_class = AssetInstanceSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    # filter by snapshot to see the "state" of the project at that time
    filterset_fields = ['snapshot', 'asset']
    search_fields = ['asset__name', 'asset__model', 'instance_id', 'custom_fields']