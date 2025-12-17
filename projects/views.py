from rest_framework import viewsets
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from .models import Project, Snapshot
from .serializers import ProjectSerializer, SnapshotSerializer


class ProjectViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing Projects.
    Supports search by job_id and name.
    """
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]

    # Enable search on these fields
    search_fields = ['job_id', 'name', 'description']

    # Enable filtering by specific fields
    filterset_fields = {
        'job_id': ['exact', 'icontains'],
        'name': ['icontains'],
    }

    ordering_fields = ['job_id', 'name', 'created_at']


class SnapshotViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing Snapshots.
    To list snapshots for a specific project, use: /api/snapshots/?project=<id>
    """
    queryset = Snapshot.objects.all()
    serializer_class = SnapshotSerializer

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]

    # 1. Search: Allows searching snapshot names AND the related project name
    search_fields = ['name', 'project__name', 'project__job_id']

    # 2. Filtering: Critical for the UI to show "Snapshots for this Project"
    filterset_fields = ['project']

    ordering_fields = ['date', 'name', 'created_at']