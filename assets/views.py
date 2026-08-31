from drf_spectacular.utils import extend_schema
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework.filters import SearchFilter
from ephany_framework.filters import StableOrderingFilter
from .summary import AssetSummarySerializer, asset_summary
from django_filters.rest_framework import DjangoFilterBackend

from .models import (
    Manufacturer,
    Asset,
    AssetAttribute,
    AssetAttributeChoice,
    AssetCategory,
    AssetFile,
    Prototype,
    PrototypeItem,
    Vendor,
    VendorProduct
)
from .serializers import (
    ManufacturerSerializer,
    AssetSerializer,
    AssetFileSerializer,
    AssetCategorySerializer,
    AssetAttributeSerializer,
    AssetAttributeChoiceSerializer,
    CategoryListSerializer,
    PrototypeSerializer,
    PrototypeItemSerializer,
    VendorSerializer,
    VendorProductSerializer,
)


class ManufacturerViewSet(viewsets.ModelViewSet):
    """
    ViewSet for viewing and editing manufacturers.
    Supports search by name and ordering.
    """
    queryset = Manufacturer.objects.all()
    serializer_class = ManufacturerSerializer

    filter_backends = [DjangoFilterBackend, SearchFilter, StableOrderingFilter]

    # Fields for 'DjangoFilterBackend' (exact matches)
    filterset_fields = {
        'name': ['exact', 'iexact', 'icontains']
    }

    # Fields for 'SearchFilter' (?search=...)
    search_fields = ['name']

    # Default ordering and allowed ordering fields
    ordering_fields = ['name']
    ordering = ['name']


class AssetAttributeViewSet(viewsets.ModelViewSet):
    """
    Full CRUD endpoint for asset custom attribute definitions.
    Choices are nested inline for read. Manage choices via /api/attribute-choices/.
    """
    queryset = AssetAttribute.objects.prefetch_related('choices').all().order_by('name')
    serializer_class = AssetAttributeSerializer
    filter_backends = [SearchFilter, StableOrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name', 'scope', 'data_type']


class AssetAttributeChoiceViewSet(viewsets.ModelViewSet):
    """
    Full CRUD endpoint for picklist choices belonging to a 'choice'-type AssetAttribute.
    Supports filtering by attribute id: /api/attribute-choices/?attribute=<id>
    Supports filtering by attribute name: /api/attribute-choices/?attribute__name=<name>
    """
    queryset = AssetAttributeChoice.objects.select_related('attribute').all()
    serializer_class = AssetAttributeChoiceSerializer
    filter_backends = [DjangoFilterBackend, StableOrderingFilter]
    filterset_fields = {
        'attribute': ['exact'],
        'attribute__name': ['exact', 'icontains'],
    }
    ordering_fields = ['attribute__name', 'order', 'value']
    ordering = ['attribute__name', 'order']

    def get_serializer_context(self):
        context = super().get_serializer_context()
        # Inject the attribute object into serializer context on create
        # so validate() can check its data_type before the instance is saved.
        if self.request.method == 'POST':
            attribute_id = self.request.data.get('attribute')
            if attribute_id:
                try:
                    context['attribute'] = AssetAttribute.objects.get(pk=attribute_id)
                except AssetAttribute.DoesNotExist:
                    pass  # Let DRF's standard FK validation handle the missing object error
        return context


class AssetCategoryViewSet(viewsets.ModelViewSet):
    queryset = AssetCategory.objects.all()
    serializer_class = AssetCategorySerializer


class AssetFileViewSet(viewsets.ModelViewSet):
    queryset = AssetFile.objects.all()
    serializer_class = AssetFileSerializer


class AssetViewSet(viewsets.ModelViewSet):
    # AssetSerializer nests the manufacturer, the category, every attached
    # file, and every assembly component (which nests its own child asset's
    # manufacturer and category in turn). Without this, serializing one page
    # of 20 assets issued 118 queries.
    queryset = Asset.objects.select_related("manufacturer", "category").prefetch_related(
        "files",
        "components__child_asset__manufacturer",
        "components__child_asset__category",
    )
    serializer_class = AssetSerializer

    def get_queryset(self):
        # The summary reads only the manufacturer name, so the file and
        # assembly prefetches above would be work done and thrown away.
        if self.action == "summary":
            return Asset.objects.select_related("manufacturer")
        return super().get_queryset()

    # Enable file uploads
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    # Configuration for filtering, searching, and sorting
    # Added OrderingFilter here to enable the ?ordering parameter
    filter_backends = [DjangoFilterBackend, SearchFilter, StableOrderingFilter]

    # Fielded filtering (allows exact/partial matches on specific fields)
    filterset_fields = {
        "type_id": ["exact", "iexact"],
        "manufacturer__name": ["exact", "iexact", "icontains"],
        "model": ["exact", "iexact", "icontains"],
        "name": ["icontains", "exact"],
        "description": ["icontains", "exact"],
        "category__name": ["exact"],
    }

    # Keyword search (allows searching across these fields simultaneously)
    search_fields = [
        "name",
        "description",
        "model",
        "manufacturer__name",
    ]

    # NEW: Define which fields are allowed to be sorted
    ordering_fields = [
        'type_id',
        'name',
        'manufacturer__name', # Allows sorting by manufacturer name
        'model',
        'category__name',     # Allows sorting by category name
        'created_at',
        'updated_at'
    ]

    @extend_schema(
        summary="Aggregate view of this asset across the portfolio",
        description=(
            """Aggregates one catalog asset across every project: how many are installed,
where, and what replacing them would cost.

Answers the question a catalog cannot: a manufacturer discontinues a part, and
you need to know how many are in the field, where, and what replacing them
costs.

Counts the **latest snapshot of each project**. A project holds several
snapshots of the same physical installation - design intent, procurement,
as-built - so counting across all of them would multiply every unit by the
number of snapshots. The `totals.basis` field states this in the response.

Sites with none installed are omitted. Knowing where an asset *should* be but
is not is a question about a standard, which this endpoint has no concept of."""
        ),
        responses={200: AssetSummarySerializer},
    )
    @action(detail=True, methods=["get"])
    def summary(self, request, pk=None):
        """Where this catalog asset is installed, and what replacing it costs."""
        # Rendered through the serializer rather than returned raw, so the
        # response cannot disagree with the schema that documents it - money
        # in particular serializes as a string, not a lossy float.
        payload = AssetSummarySerializer(asset_summary(self.get_object())).data
        return Response(payload, status=status.HTTP_200_OK)

    @extend_schema(
        summary="List every asset category, unpaginated",
        responses={200: CategoryListSerializer(many=True)},
    )
    @action(detail=False, methods=['get'], pagination_class=None)
    def all_categories(self, request):
        """
        Custom action to return a non-paginated, complete list of unique
        asset categories for filter dropdowns in the frontend.
        Endpoint: /api/assets/all_categories/
        """
        categories = AssetCategory.objects.all().order_by('name')
        serializer = CategoryListSerializer(categories, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="List every manufacturer, unpaginated",
        responses={200: ManufacturerSerializer(many=True)},
    )
    @action(detail=False, methods=['get'], pagination_class=None)
    def all_manufacturers(self, request):
        """
        Returns a non-paginated list of all manufacturers for filter dropdowns.
        Endpoint: /api/assets/all_manufacturers/
        """
        manufacturers = Manufacturer.objects.all().order_by('name')
        serializer = ManufacturerSerializer(manufacturers, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class VendorViewSet(viewsets.ModelViewSet):
    # Ordering comes from Vendor.Meta ('name', 'id'). Vendor.name is not
    # unique, so ordering by it alone here would leave pagination unstable.
    queryset = Vendor.objects.all()
    serializer_class = VendorSerializer
    filter_backends = [SearchFilter, StableOrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name']


class VendorProductViewSet(viewsets.ModelViewSet):
    queryset = VendorProduct.objects.select_related('asset', 'vendor').all()
    serializer_class = VendorProductSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, StableOrderingFilter]
    filterset_fields = ['vendor', 'asset']
    search_fields = ['asset__name', 'vendor__name', 'sku']
    ordering_fields = ['vendor__name', 'asset__name', 'cost']

class PrototypeViewSet(viewsets.ModelViewSet):
    """
    Versioned standard kits of parts.

    A row is one version. RTL-STD 2024.1 and RTL-STD 2025.1 are separate
    records with separate item lists, and a Snapshot points at whichever it was
    built to. Filter by `code` to see every revision of one standard, or by
    `is_active` to hide superseded ones.
    """
    queryset = Prototype.objects.prefetch_related("items__asset")
    serializer_class = PrototypeSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, StableOrderingFilter]
    filterset_fields = {
        "code": ["exact", "iexact"],
        "version": ["exact"],
        "is_active": ["exact"],
    }
    search_fields = ["code", "name", "description"]
    ordering_fields = ["code", "version", "name", "created_at"]


class PrototypeItemViewSet(viewsets.ModelViewSet):
    """
    Individual lines of a standard.

    Writes are refused once a snapshot references the parent version - see
    PrototypeItem.clean(). Editing a referenced standard rewrites history, so
    publish a new version instead.
    """
    queryset = PrototypeItem.objects.select_related("prototype", "asset")
    serializer_class = PrototypeItemSerializer
    filter_backends = [DjangoFilterBackend, StableOrderingFilter]
    filterset_fields = ["prototype", "asset"]
    ordering_fields = ["quantity"]
