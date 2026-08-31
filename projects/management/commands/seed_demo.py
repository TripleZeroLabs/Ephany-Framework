"""
Load a believable fleet of demo data.

A fresh clone gives you an empty admin and an API that returns
`{"count": 0, "results": []}`, which tells you nothing about what the framework
is for. This command fills it with three verticals of near-identical sites so
the shape of the data — a standard kit of parts, repeated across a fleet, with
deviations — is visible immediately.

Usage:
    python manage.py seed_demo
    python manage.py seed_demo --flush     # delete demo data first, then reload

Everything it creates is tagged, so --flush removes exactly what it added and
leaves anything you made by hand alone.
"""

import datetime

from django.core.management.base import BaseCommand
from django.db import transaction

from assets.models import (
    Asset,
    AssetAttribute,
    AssetAttributeChoice,
    AssetCategory,
    AssetComponent,
    Manufacturer,
    Vendor,
    VendorProduct,
)
from projects.models import AssetInstance, Project, Site, Snapshot

# Everything this command creates carries this marker, so --flush can find it.
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
    ("power_draw_watts", "int", "int", "none", []),
    ("rack_units", "type", "int", "none", []),
    ("weight_capacity", "type", "float", "autodesk.spec.aec:mass-2.0.0", []),
    ("finish", "type", "choice", "none", ["Anodised", "Black Powdercoat", "Brushed Steel", "White"]),
    ("fire_rating", "type", "choice", "none", ["Class A", "Class B", "Not Rated"]),
    ("serial_number", "instance", "str", "none", []),
    ("install_date", "instance", "str", "none", []),
    ("condition", "instance", "choice", "none", ["New", "Good", "Fair", "Needs Replacement"]),
]

# type_id, name, category, manufacturer, model, description, custom_fields
ASSETS = [
    # --- Data centre kit -----------------------------------------------
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
    # --- Workplace kit --------------------------------------------------
    ("CHR-100", "Task Chair", "Seating", "Basalt Furniture", "BF-100",
     "Mesh-back adjustable task chair", {"weight_capacity": 135.0, "finish": "Black Powdercoat"}),
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
    # --- Shared / front of house ----------------------------------------
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

# The standard kit for each vertical. This is the point of the whole dataset:
# every site of a given type gets the same parts list, and the drift between
# them is what a fleet tool exists to surface.
KITS = {
    "Edge Data Centre": [
        ("RK-4200", 4), ("PDU-3020", 8), ("UPS-5000", 2), ("CRAC-201", 2),
        ("FAN-110", 4), ("SHLF-1U", 6), ("LGT-100", 12), ("LGT-EX1", 2),
    ],
    "Coworking Floor": [
        ("DSK-160", 24), ("DSK-120", 12), ("CHR-100", 36), ("CHR-200", 8),
        ("BNC-240", 4), ("LCK-012", 3), ("SHL-900", 6), ("LGT-400", 18),
        ("LGT-EX1", 4), ("DSP-055", 2), ("DSP-032", 3), ("STL-050", 10),
    ],
    "Retail Store": [
        ("SHL-900", 14), ("DSP-055", 6), ("DSP-032", 4), ("LGT-100", 40),
        ("LGT-400", 8), ("LGT-EX1", 3), ("CHR-100", 4), ("STL-050", 6),
        ("LCK-012", 1),
    ],
}

# site_id, name, vertical, city, state, country, status
SITES = [
    ("EDC-001", "Ashburn Edge Pod", "Edge Data Centre", "Ashburn", "VA", "USA", "green"),
    ("EDC-002", "Hillsboro Edge Pod", "Edge Data Centre", "Hillsboro", "OR", "USA", "green"),
    ("EDC-003", "Dallas Edge Pod", "Edge Data Centre", "Dallas", "TX", "USA", "yellow"),
    ("EDC-004", "Columbus Edge Pod", "Edge Data Centre", "Columbus", "OH", "USA", "blue"),
    ("CWK-001", "Shoreditch Floor 3", "Coworking Floor", "London", "", "UK", "green"),
    ("CWK-002", "Kreuzberg Floor 2", "Coworking Floor", "Berlin", "", "Germany", "green"),
    ("CWK-003", "Mission Floor 5", "Coworking Floor", "San Francisco", "CA", "USA", "yellow"),
    ("CWK-004", "Liberties Floor 1", "Coworking Floor", "Dublin", "", "Ireland", "red"),
    ("CWK-005", "Kaapse Floor 4", "Coworking Floor", "Amsterdam", "", "Netherlands", "blue"),
    ("RTL-001", "Flagship Fifth Ave", "Retail Store", "New York", "NY", "USA", "green"),
    ("RTL-002", "Michigan Avenue", "Retail Store", "Chicago", "IL", "USA", "green"),
    ("RTL-003", "Santa Monica Promenade", "Retail Store", "Santa Monica", "CA", "USA", "yellow"),
    ("RTL-004", "Design District", "Retail Store", "Miami", "FL", "USA", "green"),
    ("RTL-005", "The Domain", "Retail Store", "Austin", "TX", "USA", "blue"),
    ("RTL-006", "Pearl District", "Retail Store", "Portland", "OR", "USA", "red"),
]

PHASES = [
    ("Phase 1: Design Intent", -180),
    ("Phase 2: Procurement", -90),
    ("Phase 3: As-Built", -10),
]

# Deliberate deviations from the standard kit, so the fleet is not uniform.
# (site_id, type_id, quantity_delta) — negative removes, positive adds.
DEVIATIONS = [
    ("EDC-003", "CRAC-201", -1),    # one cooling unit never installed
    ("EDC-004", "RK-4200", 2),      # expanded beyond standard
    ("CWK-003", "DSK-160", -6),     # smaller floorplate
    ("CWK-004", "CHR-100", -12),    # order short-shipped
    ("CWK-005", "DSP-055", 3),      # extra signage
    ("RTL-003", "SHL-900", -4),
    ("RTL-006", "LGT-100", -15),    # value-engineered lighting
]


class Command(BaseCommand):
    help = (
        "Load a demo fleet: 15 sites across 3 verticals, each built from a "
        "standard kit of parts, with deliberate deviations between them."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete previously seeded demo data before loading.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["flush"]:
            self._flush()

        self.stdout.write("Seeding demo fleet...")

        categories = self._categories()
        manufacturers = self._manufacturers()
        self._attributes()
        assets = self._assets(categories, manufacturers)
        self._assemblies(assets)
        self._vendor_products(assets)
        sites, projects = self._sites_and_projects()
        instances = self._snapshots(projects, assets)

        self.stdout.write(self.style.SUCCESS("\nDone. The fleet now contains:"))
        self.stdout.write(f"  {len(manufacturers):>5} manufacturers")
        self.stdout.write(f"  {len(categories):>5} categories")
        self.stdout.write(f"  {len(assets):>5} catalog assets")
        self.stdout.write(f"  {len(sites):>5} sites")
        self.stdout.write(f"  {len(projects):>5} projects")
        self.stdout.write(f"  {Snapshot.objects.count():>5} snapshots")
        self.stdout.write(f"  {instances:>5} asset instances")

        self.stdout.write("\nTry it:")
        self.stdout.write("  python manage.py runserver")
        self.stdout.write("  http://127.0.0.1:8000/api/docs/")
        self.stdout.write("  curl 'http://127.0.0.1:8000/api/assets/?search=rack'")
        self.stdout.write(
            "  curl 'http://127.0.0.1:8000/api/instances/?asset=1'"
            "   # every site using one catalog asset"
        )

    # -- flush ---------------------------------------------------------------

    def _flush(self):
        """Remove only what a previous run created, in FK-safe order."""
        self.stdout.write(self.style.WARNING("Flushing existing demo data..."))

        AssetInstance.objects.filter(custom_fields__source=DEMO_TAG).delete()
        Snapshot.objects.filter(project__custom_fields__source=DEMO_TAG).delete()
        Project.objects.filter(custom_fields__source=DEMO_TAG).delete()
        Site.objects.filter(site_id__in=[s[0] for s in SITES]).delete()

        demo_type_ids = [a[0] for a in ASSETS]
        VendorProduct.objects.filter(asset__type_id__in=demo_type_ids).delete()
        AssetComponent.objects.filter(parent_asset__type_id__in=demo_type_ids).delete()
        Asset.objects.filter(type_id__in=demo_type_ids).delete()
        Vendor.objects.filter(name__in=[v[0] for v in VENDORS]).delete()
        Manufacturer.objects.filter(name__in=[m[0] for m in MANUFACTURERS]).delete()
        AssetCategory.objects.filter(name__in=[c[0] for c in CATEGORIES]).delete()
        AssetAttribute.objects.filter(name__in=[a[0] for a in ATTRIBUTES]).delete()

    # -- catalog -------------------------------------------------------------

    def _categories(self):
        result = {}
        for name, description in CATEGORIES:
            result[name], _ = AssetCategory.objects.get_or_create(
                name=name, defaults={"description": description}
            )
        return result

    def _manufacturers(self):
        result = {}
        for name, url in MANUFACTURERS:
            result[name], _ = Manufacturer.objects.get_or_create(
                name=name, defaults={"url": url}
            )
        return result

    def _attributes(self):
        """
        Define the schema that Asset.custom_fields is validated against.

        Without these, every custom_fields value below would be rejected by
        Asset.clean() as an unknown field.
        """
        for name, scope, data_type, unit_type, choices in ATTRIBUTES:
            attribute, _ = AssetAttribute.objects.get_or_create(
                name=name,
                defaults={"scope": scope, "data_type": data_type, "unit_type": unit_type},
            )
            for order, value in enumerate(choices):
                AssetAttributeChoice.objects.get_or_create(
                    attribute=attribute, value=value, defaults={"order": order}
                )

    def _assets(self, categories, manufacturers):
        result = {}
        for type_id, name, category, manufacturer, model, description, fields in ASSETS:
            result[type_id], _ = Asset.objects.get_or_create(
                type_id=type_id,
                defaults={
                    "name": name,
                    "category": categories[category],
                    "manufacturer": manufacturers[manufacturer],
                    "model": model,
                    "description": description,
                    "custom_fields": fields,
                },
            )
        return result

    def _assemblies(self, assets):
        """Some assets are kits in their own right — a rack ships with PDUs."""
        for parent_id, children in ASSEMBLIES.items():
            for child_id, quantity, optional in children:
                AssetComponent.objects.get_or_create(
                    parent_asset=assets[parent_id],
                    child_asset=assets[child_id],
                    defaults={
                        "quantity_required": quantity,
                        "can_add_per_instance": optional,
                    },
                )

    def _vendor_products(self, assets):
        """Two vendors quoting the same parts at different prices and lead times."""
        vendors = []
        for name, website, email in VENDORS:
            vendor, _ = Vendor.objects.get_or_create(
                name=name, defaults={"website": website, "contact_email": email}
            )
            vendors.append(vendor)

        for index, (type_id, *_rest) in enumerate(ASSETS):
            base_cost = 120 + (index * 37) % 900
            for offset, vendor in enumerate(vendors):
                VendorProduct.objects.get_or_create(
                    asset=assets[type_id],
                    vendor=vendor,
                    defaults={
                        "sku": f"{vendor.name[:3].upper()}-{type_id}",
                        "cost": base_cost + (offset * 15),
                        "lead_time_days": 14 + (offset * 7) + (index % 3) * 5,
                    },
                )

    # -- fleet ---------------------------------------------------------------

    def _sites_and_projects(self):
        today = datetime.date.today()
        sites, projects = {}, {}

        for index, (site_id, name, vertical, city, state, country, status) in enumerate(SITES):
            site, _ = Site.objects.get_or_create(site_id=site_id, defaults={"name": name})
            sites[site_id] = site

            project, _ = Project.objects.get_or_create(
                job_id=f"JOB-{1000 + index}",
                defaults={
                    "name": name,
                    "description": f"{vertical} fit-out at {name}",
                    "site": site,
                    "city": city,
                    "state": state,
                    "country": country,
                    "status": status,
                    "go_live_date": today + datetime.timedelta(days=30 + index * 14),
                    "custom_fields": {"source": DEMO_TAG, "vertical": vertical},
                },
            )
            projects[site_id] = project

        return sites, projects

    def _snapshots(self, projects, assets):
        """
        Three snapshots per project, so each site has a history.

        Earlier phases carry the standard kit; the as-built snapshot carries
        the deviations, which is where a fleet report earns its keep.
        """
        today = datetime.date.today()
        deviations = {}
        for site_id, type_id, delta in DEVIATIONS:
            deviations.setdefault(site_id, {})[type_id] = delta

        total = 0
        for site_id, name, vertical, *_rest in SITES:
            project = projects[site_id]
            kit = KITS[vertical]

            for phase_index, (phase_name, day_offset) in enumerate(PHASES):
                snapshot, _ = Snapshot.objects.get_or_create(
                    project=project,
                    name=phase_name,
                    date=today + datetime.timedelta(days=day_offset),
                )
                if snapshot.instances.exists():
                    continue

                is_as_built = phase_index == len(PHASES) - 1
                rows = []
                for type_id, quantity in kit:
                    if is_as_built:
                        quantity += deviations.get(site_id, {}).get(type_id, 0)
                    for unit in range(max(quantity, 0)):
                        rows.append(
                            AssetInstance(
                                snapshot=snapshot,
                                asset=assets[type_id],
                                instance_id=f"{type_id}-{unit + 1:03d}",
                                location=f"{name} / Level {1 + (unit % 3)}",
                                custom_fields={
                                    "source": DEMO_TAG,
                                    "condition": "New" if is_as_built else "Good",
                                },
                            )
                        )
                AssetInstance.objects.bulk_create(rows)
                total += len(rows)

            self.stdout.write(f"  {site_id}  {name} ({vertical})")

        return total
