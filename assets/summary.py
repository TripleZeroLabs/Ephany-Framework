"""
Aggregate view of one catalog asset across the whole portfolio.

This answers the question a catalog alone cannot. `/api/assets/{id}/` says what
a thing is; `/api/instances/?asset={id}` says every place it occurs, one
fully-hydrated row at a time, leaving the caller to aggregate. Neither answers
"a manufacturer discontinued this part — how exposed am I, and where?"

The query lives here rather than in views.py because the snapshot rule below is
the whole correctness of the feature and deserves to be read on its own.
"""

from django.db.models import Count, F, OuterRef, Subquery
from rest_framework import serializers

from projects.models import AssetInstance, Snapshot


def current_instances(asset):
    """
    Instances of `asset` in the portfolio's *current* state.

    A project has several snapshots — design intent, procurement, as-built —
    and the same physical unit appears in each. Counting across all of them
    multiplies every unit by the number of snapshots and returns a confidently
    wrong number in the correct shape, which is the worst kind of wrong.

    "Current" therefore means the newest snapshot of each project. Ties on
    date fall back to the highest id, so the result is deterministic.
    """
    latest_snapshot = (
        Snapshot.objects.filter(project=OuterRef("snapshot__project"))
        .order_by("-date", "-id")
        .values("pk")[:1]
    )

    return (
        AssetInstance.objects.filter(asset=asset)
        .annotate(latest=Subquery(latest_snapshot))
        .filter(snapshot=F("latest"))
    )


def asset_summary(asset):
    """Build the payload for GET /api/assets/{id}/summary/."""
    rows = list(
        current_instances(asset)
        .values(
            "snapshot__project__site__site_id",
            "snapshot__project__site__name",
            "snapshot__project__job_id",
            "snapshot__project__name",
            "snapshot__project__status",
            "snapshot__id",
            "snapshot__name",
            "snapshot__date",
        )
        .annotate(quantity=Count("id"))
        .order_by("-quantity", "snapshot__project__site__site_id")
    )

    total = sum(row["quantity"] for row in rows)

    # Cheapest quote on file, so the figure is a floor rather than a forecast.
    # Every quote is listed alongside it; lead time often matters more than
    # price when a part has gone end-of-life.
    quotes = list(asset.vendor_products.select_related("vendor").order_by("cost"))

    return {
        "asset": {
            "id": asset.id,
            "type_id": asset.type_id,
            "name": asset.name,
            "manufacturer": asset.manufacturer.name if asset.manufacturer else None,
            "model": asset.model,
        },
        "totals": {
            "total_installed": total,
            "site_count": len(rows),
            # Stated explicitly so a client can never mistake which question
            # was answered, and so an `as_of` parameter has somewhere to live.
            "basis": "latest snapshot per project",
        },
        "replacement": _replacement(quotes, total),
        "sites": [
            {
                "site_id": row["snapshot__project__site__site_id"],
                "site_name": row["snapshot__project__site__name"],
                "project": {
                    "job_id": row["snapshot__project__job_id"],
                    "name": row["snapshot__project__name"],
                    "status": row["snapshot__project__status"],
                },
                "snapshot": {
                    "id": row["snapshot__id"],
                    "name": row["snapshot__name"],
                    "date": row["snapshot__date"],
                },
                "quantity": row["quantity"],
            }
            for row in rows
        ],
    }


def _replacement(quotes, total):
    """Cost of replacing every installed unit, plus every quote on file."""
    if not quotes:
        return None

    cheapest = quotes[0]
    return {
        "vendor": cheapest.vendor.name,
        "unit_cost": cheapest.cost,
        "lead_time_days": cheapest.lead_time_days,
        "estimated_total": cheapest.cost * total,
        "quotes": [
            {
                "vendor": quote.vendor.name,
                "sku": quote.sku,
                "unit_cost": quote.cost,
                "lead_time_days": quote.lead_time_days,
            }
            for quote in quotes
        ],
    }


# --- Serializers ------------------------------------------------------------
#
# The payload is built as plain dicts above, because it is an aggregate rather
# than a model. These exist so drf-spectacular can describe the response in
# openapi.yaml instead of falling back to a bare object.


class SummaryAssetSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    type_id = serializers.CharField()
    name = serializers.CharField()
    manufacturer = serializers.CharField(allow_null=True)
    model = serializers.CharField()


class SummaryTotalsSerializer(serializers.Serializer):
    total_installed = serializers.IntegerField(
        help_text="Units installed across the portfolio, counted once each."
    )
    site_count = serializers.IntegerField(help_text="Sites with at least one installed.")
    basis = serializers.CharField(
        help_text="Which snapshots were counted. Currently always the latest per project."
    )


class SummaryQuoteSerializer(serializers.Serializer):
    vendor = serializers.CharField()
    sku = serializers.CharField()
    unit_cost = serializers.DecimalField(max_digits=12, decimal_places=2)
    lead_time_days = serializers.IntegerField()


class SummaryReplacementSerializer(serializers.Serializer):
    vendor = serializers.CharField(help_text="Vendor offering the lowest unit cost.")
    unit_cost = serializers.DecimalField(max_digits=12, decimal_places=2)
    lead_time_days = serializers.IntegerField()
    estimated_total = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        help_text="Lowest unit cost multiplied by total_installed. A floor, not a forecast.",
    )
    quotes = SummaryQuoteSerializer(many=True)


class SummaryProjectSerializer(serializers.Serializer):
    job_id = serializers.CharField()
    name = serializers.CharField()
    status = serializers.CharField(allow_blank=True)


class SummarySnapshotSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    date = serializers.DateField()


class SummarySiteSerializer(serializers.Serializer):
    site_id = serializers.CharField(allow_null=True)
    site_name = serializers.CharField(allow_null=True)
    project = SummaryProjectSerializer()
    snapshot = SummarySnapshotSerializer()
    quantity = serializers.IntegerField()


class AssetSummarySerializer(serializers.Serializer):
    """Where one catalog asset is installed across every project."""

    asset = SummaryAssetSerializer()
    totals = SummaryTotalsSerializer()
    replacement = SummaryReplacementSerializer(
        allow_null=True, help_text="Null when no vendor has quoted this asset."
    )
    sites = SummarySiteSerializer(many=True)
