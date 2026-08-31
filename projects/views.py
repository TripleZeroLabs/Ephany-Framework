from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.response import Response
from ephany_framework.filters import StableOrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Max

from .drift import (
    InstantiateRequestSerializer,
    InstantiateResponseSerializer,
    SnapshotDriftSerializer,
    instantiate_prototype,
    snapshot_drift,
)
from .models import Project, Site, Snapshot, AssetInstance
from .serializers import ProjectSerializer, SiteSerializer, SnapshotSerializer, AssetInstanceSerializer


class SiteViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Sites.
    """
    queryset = Site.objects.prefetch_related('projects').all()
    serializer_class = SiteSerializer
    filter_backends = [SearchFilter, StableOrderingFilter]
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
    filter_backends = [DjangoFilterBackend, SearchFilter, StableOrderingFilter]
    filterset_fields = ['status', 'site']
    search_fields = ['job_id', 'name', 'site__site_id', 'city']

    @extend_schema(
        summary="Create a snapshot populated from a standard",
        description=(
            """Stamps a prototype's parts list into a new snapshot on this project.

Turns "set up the sixteenth store like the other fifteen" into one call. It is
also how a project adopts a revised standard - the operation is identical, so
there is no separate re-baselining path.

Quantities expand into individual AssetInstance rows, matching how installations
are modelled everywhere else: each unit can then carry its own location, tag,
and custom fields."""
        ),
        request=InstantiateRequestSerializer,
        responses={201: InstantiateResponseSerializer},
    )
    @action(detail=True, methods=["post"])
    def instantiate(self, request, pk=None):
        """Create a snapshot on this project from a prototype."""
        project = self.get_object()
        form = InstantiateRequestSerializer(data=request.data)
        form.is_valid(raise_exception=True)
        data = form.validated_data

        snapshot, created = instantiate_prototype(
            project=project,
            prototype=data["prototype"],
            name=data["name"],
            date=data["date"],
            include_optional=data["include_optional"],
        )

        payload = {
            "snapshot": {
                "id": snapshot.id,
                "name": snapshot.name,
                "date": snapshot.date,
                "project": {
                    "id": project.id,
                    "job_id": project.job_id,
                    "name": project.name,
                },
            },
            "prototype": {
                "id": snapshot.prototype.id,
                "code": snapshot.prototype.code,
                "version": snapshot.prototype.version,
                "name": snapshot.prototype.name,
            },
            "instances_created": created,
        }
        return Response(
            InstantiateResponseSerializer(payload).data,
            status=status.HTTP_201_CREATED,
        )

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
    queryset = Snapshot.objects.select_related('project', 'prototype').all()
    serializer_class = SnapshotSerializer
    filter_backends = [DjangoFilterBackend, StableOrderingFilter]
    filterset_fields = ['project', 'prototype']

    @extend_schema(
        summary="How this snapshot differs from the standard it was built to",
        description=(
            """Compares what is installed against the snapshot's own prototype.

Each snapshot is measured against the standard **it declares**, never against
the project's current one or the newest revision of that standard. A site
signed off against the 2024 spec stays compliant after the spec moves on;
measuring everything against the latest revision would turn the whole portfolio
red the day someone publishes one.

`status` distinguishes four cases rather than reducing to a number: `match`,
`short`, `over`, and `unexpected` (installed but absent from the standard).
`is_required` is reported per line because an optional item being absent is a
choice, not a fault - `summary.is_compliant` ignores those.

Returns 409 when the snapshot declares no prototype. There is no baseline to
measure against, which is a different answer from "no differences"."""
        ),
        responses={200: SnapshotDriftSerializer},
    )
    @action(detail=True, methods=["get"])
    def drift(self, request, pk=None):
        """Expected versus actual, against this snapshot's own standard."""
        result = snapshot_drift(self.get_object())
        if result is None:
            return Response(
                {"detail": "This snapshot declares no prototype, so there is "
                           "nothing to measure it against."},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(SnapshotDriftSerializer(result).data, status=status.HTTP_200_OK)


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