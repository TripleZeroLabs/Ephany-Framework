"""
The demo dataset: what it contains, and how to remove it safely.

Shared by the `seed_demo` and `clear_demo` management commands so there is one
definition of what "demo data" means.

## Why removal is careful

The obvious teardown - delete everything whose name appears in the lists below
- destroys user data. `Asset.manufacturer` is a CASCADE foreign key, so
deleting the demo manufacturer "Aurora Systems" also deletes any asset someone
built on it while testing. Deleting an AssetCategory nulls the category on
their assets. Neither failure announces itself.

So the teardown deletes records the demo created outright, and treats shared
lookup records - manufacturers, categories, vendors, attributes - as
*reference-counted*: they go only if nothing outside the demo set still points
at them. Anything kept is reported with the reason, rather than silently
skipped.
"""

from django.db import transaction

DEMO_TAG = "demo"

MANUFACTURERS = [
    ("Aurora Systems", "https://example.com/aurora"),
    ("Northwind Fixtures", "https://example.com/northwind"),
    ("Corvid Electric", "https://example.com/corvid"),
    ("Basalt Furniture", "https://example.com/basalt"),
    ("Halden Cooling", "https://example.com/halden"),
]

CATEGORIES = [
    ("Racks & Enclosures", "Server racks, cabinets, and enclosures"),
    ("Power Distribution", "PDUs, UPS units, and electrical distribution"),
    ("Cooling", "CRAC units, fans, and thermal management"),
    ("Seating", "Chairs, stools, and soft seating"),
    ("Work Surfaces", "Desks, benches, and counters"),
    ("Lighting", "Fixtures, lamps, and controls"),
    ("Displays", "Screens, monitors, and signage"),
    ("Storage", "Shelving, lockers, and cabinets"),
]

# name, scope, data_type, unit_type, [choices]
ATTRIBUTES = [
    ("voltage", "type", "int", "none", []),
    ("power_draw_watts", "type", "int", "none", []),
    ("rack_units", "type", "int", "none", []),
    ("weight_capacity", "type", "float", "autodesk.spec.aec:mass-2.0.0", []),
    ("finish", "type", "choice", "none",
     ["Anodised", "Black Powdercoat", "Brushed Steel", "White"]),
    ("fire_rating", "type", "choice", "none", ["Class A", "Class B", "Not Rated"]),
    ("serial_number", "instance", "str", "none", []),
    ("install_date", "instance", "str", "none", []),
    ("condition", "instance", "choice", "none",
     ["New", "Good", "Fair", "Needs Replacement"]),
]

# type_id, name, category, manufacturer, model, description, custom_fields
ASSETS = [
    # --- Data centre kit ------------------------------------------------
    ("RK-4200", "42U Server Rack", "Racks & Enclosures", "Aurora Systems", "AR-42",
     "Standard 42U enclosed rack with perforated doors",
     {"rack_units": 42, "weight_capacity": 1360.0, "finish": "Black Powdercoat"}),
    ("RK-2400", "24U Wall Cabinet", "Racks & Enclosures", "Aurora Systems", "AR-24",
     "Wall-mounted 24U cabinet for edge deployments",
     {"rack_units": 24, "weight_capacity": 450.0, "finish": "Black Powdercoat"}),
    ("PDU-3020", "30A Rack PDU", "Power Distribution", "Corvid Electric", "CE-3020",
     "Vertical rack PDU, 30A, 20 outlets", {"voltage": 208, "power_draw_watts": 0}),
    ("UPS-5000", "5kVA Rack UPS", "Power Distribution", "Corvid Electric", "CE-5000",
     "Online double-conversion UPS, 5kVA",
     {"voltage": 208, "rack_units": 4, "power_draw_watts": 250}),
    ("CRAC-201", "In-Row Cooling Unit", "Cooling", "Halden Cooling", "HC-201",
     "In-row precision cooling, 20kW", {"voltage": 480, "power_draw_watts": 4200}),
    ("FAN-110", "Rack Fan Tray", "Cooling", "Halden Cooling", "HC-110",
     "1U four-fan tray for passive racks", {"rack_units": 1, "power_draw_watts": 45}),
    ("SHLF-1U", "1U Vented Shelf", "Racks & Enclosures", "Aurora Systems", "AR-S1",
     "Vented equipment shelf", {"rack_units": 1, "weight_capacity": 45.0}),
    # --- Workplace kit ---------------------------------------------------
    ("CHR-100", "Task Chair", "Seating", "Basalt Furniture", "BF-100",
     "Mesh-back adjustable task chair",
     {"weight_capacity": 135.0, "finish": "Black Powdercoat"}),
    ("CHR-200", "Lounge Chair", "Seating", "Basalt Furniture", "BF-200",
     "Upholstered lounge seating", {"weight_capacity": 160.0}),
    ("STL-050", "Counter Stool", "Seating", "Basalt Furniture", "BF-050",
     "Fixed-height counter stool", {"weight_capacity": 120.0}),
    ("DSK-160", "Sit-Stand Desk 1600mm", "Work Surfaces", "Basalt Furniture", "BF-D160",
     "Electric height-adjustable desk",
     {"voltage": 240, "weight_capacity": 80.0, "finish": "Brushed Steel"}),
    ("DSK-120", "Sit-Stand Desk 1200mm", "Work Surfaces", "Basalt Furniture", "BF-D120",
     "Electric height-adjustable desk, compact",
     {"voltage": 240, "weight_capacity": 70.0, "finish": "Brushed Steel"}),
    ("BNC-240", "Bench Work Surface", "Work Surfaces", "Northwind Fixtures", "NW-240",
     "Shared bench top, 2400mm", {"weight_capacity": 200.0}),
    ("LCK-012", "12-Door Locker Bank", "Storage", "Northwind Fixtures", "NW-L12",
     "Personal storage lockers", {"finish": "White"}),
    ("SHL-900", "Open Shelving Unit", "Storage", "Northwind Fixtures", "NW-900",
     "Five-tier open shelving", {"weight_capacity": 300.0, "finish": "Anodised"}),
    # --- Shared / front of house -----------------------------------------
    ("LGT-400", "Linear Pendant", "Lighting", "Northwind Fixtures", "NW-P400",
     "Suspended linear LED pendant", {"voltage": 240, "power_draw_watts": 48}),
    ("LGT-100", "Recessed Downlight", "Lighting", "Northwind Fixtures", "NW-D100",
     "Recessed LED downlight", {"voltage": 240, "power_draw_watts": 12}),
    ("LGT-EX1", "Emergency Exit Sign", "Lighting", "Corvid Electric", "CE-EX1",
     "Illuminated exit sign with battery backup",
     {"voltage": 240, "power_draw_watts": 5, "fire_rating": "Class A"}),
    ("DSP-055", "55in Display", "Displays", "Aurora Systems", "AR-D55",
     "Commercial 4K display panel", {"voltage": 240, "power_draw_watts": 120}),
    ("DSP-032", "32in Wayfinding Display", "Displays", "Aurora Systems", "AR-D32",
     "Portrait wayfinding display", {"voltage": 240, "power_draw_watts": 65}),
]

# Assemblies: parent -> [(child, quantity, optional)]
ASSEMBLIES = {
    "RK-4200": [("PDU-3020", 2, False), ("FAN-110", 1, False), ("SHLF-1U", 2, True)],
    "RK-2400": [("PDU-3020", 1, False), ("SHLF-1U", 1, True)],
    "DSK-160": [("CHR-100", 1, True)],
}

VENDORS = [
    ("Meridian Supply", "https://example.com/meridian", "sales@example.com"),
    ("Trellis Trade", "https://example.com/trellis", "orders@example.com"),
]

# --- The standards ----------------------------------------------------------
#
# Two versions of the retail standard, on purpose. Later stores are built to
# 2025.1, which calls for more display than 2024.1 did. Those stores are not
# deviating - they are compliant with a newer spec. A portfolio where every
# site follows one immutable standard is not one anybody operates; being
# mid-rollout is the permanent condition, and the data should show it.
#
# code, version, name, [(type_id, quantity, is_required)]
PROTOTYPES = [
    ("EDC-STD", "2024.1", "Edge Data Centre", [
        ("RK-4200", 4, True), ("PDU-3020", 8, True), ("UPS-5000", 2, True),
        ("CRAC-201", 2, True), ("FAN-110", 4, True), ("SHLF-1U", 6, False),
        ("LGT-100", 12, True), ("LGT-EX1", 2, True),
    ]),
    ("CWK-STD", "2024.1", "Coworking Floor", [
        ("DSK-160", 24, True), ("DSK-120", 12, True), ("CHR-100", 36, True),
        ("CHR-200", 8, True), ("BNC-240", 4, True), ("LCK-012", 3, True),
        ("SHL-900", 6, False), ("LGT-400", 18, True), ("LGT-EX1", 4, True),
        ("DSP-055", 2, True), ("DSP-032", 3, True), ("STL-050", 10, False),
    ]),
    ("RTL-STD", "2024.1", "Retail Store", [
        ("SHL-900", 14, True), ("DSP-055", 6, True), ("DSP-032", 4, True),
        ("LGT-100", 40, True), ("LGT-400", 8, True), ("LGT-EX1", 3, True),
        ("CHR-100", 4, False), ("STL-050", 6, False), ("LCK-012", 1, False),
    ]),
    # 2025.1 raises the display spec. Stores on it legitimately carry more
    # than stores on 2024.1, and neither set is in drift.
    ("RTL-STD", "2025.1", "Retail Store", [
        ("SHL-900", 14, True), ("DSP-055", 9, True), ("DSP-032", 6, True),
        ("LGT-100", 40, True), ("LGT-400", 8, True), ("LGT-EX1", 3, True),
        ("CHR-100", 4, False), ("STL-050", 6, False), ("LCK-012", 1, False),
    ]),
]

# site_id, name, prototype code, prototype version, city, state, country, status
SITES = [
    ("EDC-001", "Ashburn Edge Pod", "EDC-STD", "2024.1", "Ashburn", "VA", "USA", "green"),
    ("EDC-002", "Hillsboro Edge Pod", "EDC-STD", "2024.1", "Hillsboro", "OR", "USA", "green"),
    ("EDC-003", "Dallas Edge Pod", "EDC-STD", "2024.1", "Dallas", "TX", "USA", "yellow"),
    ("EDC-004", "Columbus Edge Pod", "EDC-STD", "2024.1", "Columbus", "OH", "USA", "blue"),
    ("CWK-001", "Shoreditch Floor 3", "CWK-STD", "2024.1", "London", "", "UK", "green"),
    ("CWK-002", "Kreuzberg Floor 2", "CWK-STD", "2024.1", "Berlin", "", "Germany", "green"),
    ("CWK-003", "Mission Floor 5", "CWK-STD", "2024.1", "San Francisco", "CA", "USA", "yellow"),
    ("CWK-004", "Liberties Floor 1", "CWK-STD", "2024.1", "Dublin", "", "Ireland", "red"),
    ("CWK-005", "Kaapse Floor 4", "CWK-STD", "2024.1", "Amsterdam", "", "Netherlands", "blue"),
    ("RTL-001", "Flagship Fifth Ave", "RTL-STD", "2024.1", "New York", "NY", "USA", "green"),
    ("RTL-002", "Michigan Avenue", "RTL-STD", "2024.1", "Chicago", "IL", "USA", "green"),
    ("RTL-003", "Santa Monica Promenade", "RTL-STD", "2024.1", "Santa Monica", "CA", "USA", "yellow"),
    ("RTL-004", "Design District", "RTL-STD", "2024.1", "Miami", "FL", "USA", "green"),
    # Built after the spec was revised.
    ("RTL-005", "The Domain", "RTL-STD", "2025.1", "Austin", "TX", "USA", "blue"),
    ("RTL-006", "Pearl District", "RTL-STD", "2025.1", "Portland", "OR", "USA", "red"),
]

PHASES = [
    ("Phase 1: Design Intent", -180),
    ("Phase 2: Procurement", -90),
    ("Phase 3: As-Built", -10),
]

# Real drift, applied to the as-built snapshot only: what was specified and
# what got installed are not the same thing.
# (site_id, type_id, quantity delta)
DEVIATIONS = [
    ("EDC-003", "CRAC-201", -1),    # one cooling unit never installed
    ("EDC-004", "RK-4200", 2),      # expanded beyond standard
    ("CWK-003", "DSK-160", -6),     # smaller floorplate
    ("CWK-004", "CHR-100", -12),    # order short-shipped
    ("CWK-005", "DSP-055", 3),      # extra signage
    ("RTL-003", "SHL-900", -4),
    ("RTL-006", "LGT-100", -15),    # value-engineered lighting
]

# One site mid-build re-baselines onto the newer standard, which is the case
# Snapshot.prototype exists to express. Its earlier phases stay measured
# against 2024.1 and stay correct.
REBASELINE = {"RTL-004": ("Phase 3: As-Built", "RTL-STD", "2025.1")}


# --- Teardown ---------------------------------------------------------------

def _demo_type_ids():
    return [row[0] for row in ASSETS]


@transaction.atomic
def clear_demo_data():
    """
    Remove the demo dataset, leaving anything else untouched.

    Returns (deleted, kept) where `deleted` maps a label to a count and `kept`
    is a list of human-readable reasons a record was left in place.

    Two different reasons show up in `kept`, and the distinction matters to
    whoever reads it:

      * something you created references this record, so removing it would
        take your data with it
      * a demo record that had to be kept references this one, so it is held
        alive by that chain

    Only the first is a reason to intervene, so they are worded differently
    rather than both blamed on the user.
    """
    from assets.models import (
        Asset, AssetAttribute, AssetCategory, AssetComponent,
        Manufacturer, Prototype, PrototypeItem, Vendor, VendorProduct,
    )
    from projects.models import AssetInstance, Project, Site, Snapshot

    deleted, kept = {}, []
    demo_type_ids = set(_demo_type_ids())

    def record(label, result):
        count = result[0] if isinstance(result, tuple) else result
        if count:
            deleted[label] = deleted.get(label, 0) + count

    def bump(label, count=1):
        deleted[label] = deleted.get(label, 0) + count

    demo_projects = Project.objects.filter(custom_fields__source=DEMO_TAG)
    demo_project_ids = set(demo_projects.values_list("id", flat=True))

    # 1. Records the demo unambiguously owns, deepest first.
    record("asset instances",
           AssetInstance.objects.filter(snapshot__project__in=demo_projects).delete())
    record("snapshots", Snapshot.objects.filter(project__in=demo_projects).delete())
    record("projects", demo_projects.delete())

    # Sites belong to the demo only while no surviving project uses them.
    for site in Site.objects.filter(site_id__in=[row[0] for row in SITES]):
        if site.projects.exists():
            kept.append(f"site {site.site_id}: a project you created uses it")
        else:
            site.delete()
            bump("sites")

    # Prototypes go before assets, since PrototypeItem protects Asset.
    kept_prototypes = set()
    for prototype in Prototype.objects.filter(
        code__in={row[0] for row in PROTOTYPES}, version__in={row[1] for row in PROTOTYPES}
    ):
        referencing = prototype.snapshots.exclude(project_id__in=demo_project_ids)
        if referencing.exists():
            kept_prototypes.add(prototype.id)
            kept.append(
                f"prototype {prototype.code} {prototype.version}: "
                f"{referencing.count()} snapshot(s) you created are measured against it"
            )
            continue
        record("prototype items", PrototypeItem.objects.filter(prototype=prototype).delete())
        prototype.delete()
        bump("prototypes")

    demo_assets = Asset.objects.filter(type_id__in=demo_type_ids)
    record("vendor products", VendorProduct.objects.filter(asset__in=demo_assets).delete())
    record("assemblies", AssetComponent.objects.filter(parent_asset__in=demo_assets).delete())

    # 2. Assets. AssetInstance.asset is PROTECT, so a surviving instance would
    #    raise mid-teardown; better to skip with an explanation.
    for asset in demo_assets:
        held_by_user, held_by_demo = [], []

        if AssetInstance.objects.filter(asset=asset).exists():
            held_by_user.append("an asset instance")
        blocking_items = PrototypeItem.objects.filter(asset=asset)
        if blocking_items.exists():
            if blocking_items.filter(prototype_id__in=kept_prototypes).exists():
                held_by_demo.append("a prototype kept above")
            else:
                held_by_user.append("a prototype")
        if AssetComponent.objects.filter(child_asset=asset).exists():
            held_by_demo.append("an assembly")

        if held_by_user:
            kept.append(f"asset {asset.type_id}: used by {' and '.join(held_by_user)} you created")
        elif held_by_demo:
            kept.append(f"asset {asset.type_id}: held by {' and '.join(held_by_demo)}")
        else:
            asset.delete()
            bump("assets")

    surviving_demo_assets = set(
        Asset.objects.filter(type_id__in=demo_type_ids).values_list("type_id", flat=True)
    )

    def describe(queryset, noun):
        """Say whether a lookup is held by the user's records or by the demo's."""
        yours = queryset.exclude(type_id__in=demo_type_ids).count()
        if yours:
            return f"{yours} {noun} you created reference(s) it"
        return f"referenced by demo {noun}s that had to be kept"

    # 3. Shared lookups. Asset.manufacturer is CASCADE, so deleting one that
    #    someone reused would silently take their assets with it.
    for vendor in Vendor.objects.filter(name__in=[row[0] for row in VENDORS]):
        if vendor.products.exists():
            kept.append(f"vendor {vendor.name}: still quoting an asset that was kept")
        else:
            vendor.delete()
            bump("vendors")

    for manufacturer in Manufacturer.objects.filter(name__in=[row[0] for row in MANUFACTURERS]):
        assets = manufacturer.assets.all()
        if assets.exists():
            kept.append(
                f"manufacturer {manufacturer.name}: {describe(assets, 'asset')} "
                f"(deleting it would cascade)"
            )
        else:
            manufacturer.delete()
            bump("manufacturers")

    for category in AssetCategory.objects.filter(name__in=[row[0] for row in CATEGORIES]):
        assets = category.assets.all()
        if assets.exists():
            kept.append(f"category {category.name}: {describe(assets, 'asset')}")
        else:
            category.delete()
            bump("categories")

    # An attribute is referenced from custom_fields, a JSON blob rather than a
    # foreign key, so the surviving assets have to be scanned.
    user_keys, demo_keys = set(), set()
    for type_id, fields in Asset.objects.values_list("type_id", "custom_fields"):
        (demo_keys if type_id in surviving_demo_assets else user_keys).update(fields or {})

    for attribute in AssetAttribute.objects.filter(name__in=[row[0] for row in ATTRIBUTES]):
        if attribute.name in user_keys:
            kept.append(f"attribute {attribute.name}: an asset you created uses it")
        elif attribute.name in demo_keys:
            kept.append(f"attribute {attribute.name}: used by a demo asset that was kept")
        else:
            attribute.choices.all().delete()
            attribute.delete()
            bump("attributes")

    return deleted, kept
