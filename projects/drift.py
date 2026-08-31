"""
Drift: how a snapshot differs from the standard it was built to.

`Prototype` says what should be installed, `AssetInstance` says what is. This
is the gap between them, per asset.

Each snapshot is compared against **its own** declared prototype, never against
the project's current one or the newest revision of that standard. A store
signed off against the 2024 spec stays compliant after the spec moves on; the
alternative turns every site red the day someone publishes a revision, and a
report that is always red is one nobody opens.
"""

from collections import Counter

from rest_framework import serializers

from assets.models import Prototype

# What a single line of the report means.
STATUS_MATCH = "match"
STATUS_SHORT = "short"        # fewer installed than the standard calls for
STATUS_OVER = "over"          # more installed than the standard calls for
STATUS_UNEXPECTED = "unexpected"  # installed but not in the standard at all


def snapshot_drift(snapshot):
    """
    Compare one snapshot against its prototype.

    Returns None when the snapshot declares no prototype - there is no baseline
    to measure against, which is a different answer from "no differences".
    """
    prototype = snapshot.prototype
    if prototype is None:
        return None

    expected = {}
    for item in prototype.items.select_related("asset"):
        expected[item.asset.type_id] = item

    actual = Counter(
        snapshot.instances.values_list("asset__type_id", "asset__name")
    )
    actual_by_type = {}
    for (type_id, name), count in actual.items():
        actual_by_type[type_id] = (name, count)

    lines = []
    for type_id in sorted(set(expected) | set(actual_by_type)):
        item = expected.get(type_id)
        name, installed = actual_by_type.get(type_id, (None, 0))
        required = item.quantity if item else 0

        if item is None:
            status = STATUS_UNEXPECTED
        elif installed == required:
            status = STATUS_MATCH
        elif installed < required:
            status = STATUS_SHORT
        else:
            status = STATUS_OVER

        lines.append({
            "type_id": type_id,
            "name": item.asset.name if item else name,
            "expected": required,
            "actual": installed,
            "delta": installed - required,
            "status": status,
            # An optional item being absent is a choice, not a fault. Callers
            # that only care about real problems filter on this.
            "is_required": item.is_required if item else False,
        })

    return {
        "snapshot": {
            "id": snapshot.id,
            "name": snapshot.name,
            "date": snapshot.date,
            "project": {
                "id": snapshot.project_id,
                "job_id": snapshot.project.job_id,
                "name": snapshot.project.name,
            },
        },
        "prototype": {
            "id": prototype.id,
            "code": prototype.code,
            "version": prototype.version,
            "name": prototype.name,
        },
        "summary": _summarise(lines),
        "lines": lines,
    }


def _summarise(lines):
    """Headline figures, so a caller does not have to reduce `lines` itself."""
    problems = [
        line for line in lines
        if line["status"] != STATUS_MATCH
        and (line["is_required"] or line["status"] in (STATUS_OVER, STATUS_UNEXPECTED))
    ]
    return {
        "is_compliant": not problems,
        "lines_checked": len(lines),
        "lines_matching": sum(1 for line in lines if line["status"] == STATUS_MATCH),
        "short": sum(1 for line in lines if line["status"] == STATUS_SHORT),
        "over": sum(1 for line in lines if line["status"] == STATUS_OVER),
        "unexpected": sum(1 for line in lines if line["status"] == STATUS_UNEXPECTED),
        "units_expected": sum(line["expected"] for line in lines),
        "units_actual": sum(line["actual"] for line in lines),
    }


# --- Serializers ------------------------------------------------------------

class DriftProjectSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    job_id = serializers.CharField()
    name = serializers.CharField()


class DriftSnapshotSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    date = serializers.DateField()
    project = DriftProjectSerializer()


class DriftPrototypeSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    code = serializers.CharField()
    version = serializers.CharField()
    name = serializers.CharField()


class DriftSummarySerializer(serializers.Serializer):
    is_compliant = serializers.BooleanField(
        help_text="True when nothing required is missing and nothing unexpected is present."
    )
    lines_checked = serializers.IntegerField()
    lines_matching = serializers.IntegerField()
    short = serializers.IntegerField(help_text="Assets with fewer installed than specified.")
    over = serializers.IntegerField(help_text="Assets with more installed than specified.")
    unexpected = serializers.IntegerField(help_text="Assets installed but not in the standard.")
    units_expected = serializers.IntegerField()
    units_actual = serializers.IntegerField()


class DriftLineSerializer(serializers.Serializer):
    type_id = serializers.CharField()
    name = serializers.CharField(allow_null=True)
    expected = serializers.IntegerField()
    actual = serializers.IntegerField()
    delta = serializers.IntegerField(help_text="actual minus expected; negative means short.")
    status = serializers.ChoiceField(
        choices=[STATUS_MATCH, STATUS_SHORT, STATUS_OVER, STATUS_UNEXPECTED]
    )
    is_required = serializers.BooleanField(
        help_text="An optional item being absent is a choice, not a fault."
    )


class SnapshotDriftSerializer(serializers.Serializer):
    """How one snapshot differs from the standard it declares."""

    snapshot = DriftSnapshotSerializer()
    prototype = DriftPrototypeSerializer()
    summary = DriftSummarySerializer()
    lines = DriftLineSerializer(many=True)


# --- Instantiation ----------------------------------------------------------

class InstantiateRequestSerializer(serializers.Serializer):
    """Body for POST /api/projects/{id}/instantiate/."""

    prototype = serializers.PrimaryKeyRelatedField(
        queryset=Prototype.objects.all(),
        help_text="The standard to stamp into the new snapshot.",
    )
    name = serializers.CharField(
        max_length=200, help_text="Name for the new snapshot, e.g. 'Phase 1: Design Intent'."
    )
    date = serializers.DateField(help_text="Date the snapshot represents.")
    include_optional = serializers.BooleanField(
        default=True,
        help_text="Include items the standard marks optional. Turn off to stamp "
                  "only what is mandatory and add the rest per site.",
    )


def instantiate_prototype(project, prototype, name, date, include_optional=True):
    """
    Create a snapshot for `project` populated from `prototype`.

    This is what turns "set up the sixteenth store like the other fifteen" into
    one call. It is also how a project adopts a revised standard: the operation
    is identical, so there is no separate re-baselining path to get wrong.

    Quantities expand into individual AssetInstance rows, matching how the rest
    of the system models installations - each unit can then carry its own
    location, tag, and custom fields.
    """
    from projects.models import AssetInstance, Snapshot

    snapshot = Snapshot.objects.create(
        project=project, name=name, date=date, prototype=prototype
    )

    items = prototype.items.select_related("asset")
    if not include_optional:
        items = items.filter(is_required=True)

    rows = []
    for item in items:
        for unit in range(item.quantity):
            rows.append(
                AssetInstance(
                    snapshot=snapshot,
                    asset=item.asset,
                    instance_id=f"{item.asset.type_id}-{unit + 1:03d}",
                )
            )
    AssetInstance.objects.bulk_create(rows)

    return snapshot, len(rows)


class InstantiateResponseSerializer(serializers.Serializer):
    snapshot = DriftSnapshotSerializer()
    prototype = DriftPrototypeSerializer()
    instances_created = serializers.IntegerField()
