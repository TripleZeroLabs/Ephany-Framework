from rest_framework import viewsets
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Max

from .models import Project, Site, Snapshot, AssetInstance
from .serializers import ProjectSerializer, SiteSerializer, SnapshotSerializer, AssetInstanceSerializer


class SiteViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Sites.
    """
    queryset = Site.objects.prefetch_related('projects').all()
    serializer_class = SiteSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['site_id', 'name']
    ordering_fields = ['site_id', 'name', 'created_at']


class ProjectViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Projects.

    Optimized to include the date of the most recent snapshot for
    sorting purposes on the dashboard.
    """
    queryset = Project.objects.select_related('site').prefetch_related('snapshots').annotate(
        latest_snapshot_date=Max('snapshots__date')
    ).all()

    serializer_class = ProjectSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'site']
    search_fields = ['job_id', 'name', 'site__site_id', 'city']

    ordering_fields = [
        'job_id',
        'name',
        'go_live_date',
        'status',
        'created_at',
        'updated_at',
        'latest_snapshot_date',
    ]


class SnapshotViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Project Snapshots.

    Uses select_related to join the project data in a single query.
    """
    queryset = Snapshot.objects.select_related('project').all()
    serializer_class = SnapshotSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['project']


class AssetInstanceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for AssetInstances.

    Provides CRUD operations for assets placed within a project snapshot.
    Optimized to handle deep nesting of library data and optional components.
    """
    queryset = AssetInstance.objects.select_related(
        'asset',
        'asset__manufacturer',
        'asset__category',
        'snapshot',
        'snapshot__project'
    ).prefetch_related(
        # Prefetch AssetComponentInstance (Project App) -> AssetComponent (Assets App)
        'optional_components',
        'optional_components__asset_component',

        # Traverse into the Asset library data for the optional components
        'optional_components__asset_component__child_asset',
        'optional_components__asset_component__child_asset__manufacturer',
        'optional_components__asset_component__child_asset__category',

        # Prefetch library-level required components (Asset -> AssetComponent)
        'asset__components',
        'asset__components__child_asset',
        'asset__components__child_asset__manufacturer',

        # Support for file attachments and galleries
        'asset__files'
    ).all()

    serializer_class = AssetInstanceSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['snapshot', 'asset']
    search_fields = [
        'asset__name',
        'asset__model',
        'instance_id',
        'location',
        'custom_fields'
    ]