"""
Load a believable demo portfolio.

A fresh clone gives you an empty admin and an API that returns
`{"count": 0, "results": []}`, which tells you nothing about what the framework
is for. This fills it with three verticals of standardized sites so the shape
of the data is visible immediately: a standard kit of parts, repeated across a
portfolio, with the two ways reality diverges from it.

Both kinds of divergence are seeded on purpose, because telling them apart is
the whole job:

  drift    a site does not match the standard it was built to - a cooling unit
           never installed, an order short-shipped
  rollout  a site matches a *different version* of the standard, because it was
           built after the spec was revised. Not a problem; just not uniform.

Usage:
    python manage.py seed_demo
    python manage.py seed_demo --flush     # remove existing demo data first

The dataset itself lives in projects/demo_data.py, shared with clear_demo.
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
    Prototype,
    PrototypeItem,
    Vendor,
    VendorProduct,
)
from projects.demo_data import (
    ASSEMBLIES,
    ASSETS,
    ATTRIBUTES,
    CATEGORIES,
    DEMO_TAG,
    DEVIATIONS,
    MANUFACTURERS,
    PHASES,
    PROTOTYPES,
    REBASELINE,
    SITES,
    VENDORS,
    clear_demo_data,
)
from projects.models import AssetInstance, Project, Site, Snapshot


class Command(BaseCommand):
    help = (
        "Load a demo portfolio: 15 sites across 3 verticals, built from four "
        "versioned standards, with deliberate drift and a mid-rollout spec change."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Remove existing demo data first. Never touches records you created.",
        )

    def say(self, message="", style=None):
        """Write unless the caller asked for silence (verbosity 0)."""
        if self.verbosity:
            self.stdout.write(style(message) if style else message)

    @transaction.atomic
    def handle(self, *args, **options):
        self.verbosity = options["verbosity"]

        if options["flush"]:
            self.say("Removing existing demo data...", self.style.WARNING)
            deleted, kept = clear_demo_data()
            for label, count in sorted(deleted.items()):
                self.say(f"  removed {count} {label}")
            for reason in kept:
                self.say(f"  kept {reason}", self.style.WARNING)
            self.say("")

        self.say("Seeding demo portfolio...")

        categories = self._categories()
        manufacturers = self._manufacturers()
        self._attributes()
        assets = self._assets(categories, manufacturers)
        self._assemblies(assets)
        self._vendor_products(assets)
        prototypes = self._prototypes(assets)
        projects = self._sites_and_projects()
        self._snapshots(projects, prototypes)

        self.say("\nDone. The portfolio now contains:", self.style.SUCCESS)
        self.say(f"  {len(manufacturers):>5} manufacturers")
        self.say(f"  {len(assets):>5} catalog assets")
        self.say(f"  {len(prototypes):>5} prototype versions")
        self.say(f"  {len(SITES):>5} sites")
        self.say(f"  {Snapshot.objects.count():>5} snapshots")
        self.say(f"  {AssetInstance.objects.count():>5} asset instances")

        self.say("\nTry it:")
        self.say("  python manage.py runserver")
        self.say("  http://127.0.0.1:8000/api/docs/")
        self.say("  curl 'http://127.0.0.1:8000/api/assets/40/summary/'")

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
        Define the schema Asset.custom_fields is validated against.

        Without these, every custom_fields value below is rejected by
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
        """Some catalog assets are kits in their own right - a rack ships with PDUs."""
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

    # -- standards -----------------------------------------------------------

    def _prototypes(self, assets):
        """
        The standards themselves - what each kind of site is supposed to contain.

        Items are written only when a prototype is newly created. A version that
        snapshots already reference is immutable and PrototypeItem.clean()
        enforces it, so re-running must not try to rewrite one.
        """
        result = {}
        for code, version, name, items in PROTOTYPES:
            prototype, created = Prototype.objects.get_or_create(
                code=code,
                version=version,
                defaults={
                    "name": name,
                    "description": f"{name} standard, revision {version}",
                },
            )
            result[(code, version)] = prototype
            if not created:
                continue
            for type_id, quantity, required in items:
                PrototypeItem.objects.create(
                    prototype=prototype,
                    asset=assets[type_id],
                    quantity=quantity,
                    is_required=required,
                )
        return result

    # -- portfolio -----------------------------------------------------------

    def _sites_and_projects(self):
        today = datetime.date.today()
        projects = {}

        for index, (site_id, name, code, version, city, state, country, status) in enumerate(SITES):
            site, _ = Site.objects.get_or_create(site_id=site_id, defaults={"name": name})
            projects[site_id], _ = Project.objects.get_or_create(
                job_id=f"JOB-{1000 + index}",
                defaults={
                    "name": name,
                    "description": f"{code} fit-out at {name}",
                    "site": site,
                    "city": city,
                    "state": state,
                    "country": country,
                    "status": status,
                    "go_live_date": today + datetime.timedelta(days=30 + index * 14),
                    "custom_fields": {"source": DEMO_TAG},
                },
            )
        return projects

    def _snapshots(self, projects, prototypes):
        """
        Three snapshots per project, each declaring the standard it was built to.

        Instances are generated from the prototype's own items rather than a
        separate list, so the demo cannot silently drift from its own standards
        except where DEVIATIONS says so. The as-built phase carries those
        deviations; earlier phases match their standard exactly.

        One site re-baselines onto a newer version at its final phase, which is
        the case Snapshot.prototype exists to express.
        """
        today = datetime.date.today()
        deviations = {}
        for site_id, type_id, delta in DEVIATIONS:
            deviations.setdefault(site_id, {})[type_id] = delta

        for site_id, name, code, version, *_rest in SITES:
            project = projects[site_id]

            for phase_index, (phase_name, day_offset) in enumerate(PHASES):
                # A phase may adopt a different standard than the project began
                # with: a change order mid-build.
                phase_code, phase_version = code, version
                rebaseline = REBASELINE.get(site_id)
                if rebaseline and rebaseline[0] == phase_name:
                    _, phase_code, phase_version = rebaseline

                prototype = prototypes[(phase_code, phase_version)]
                snapshot, _ = Snapshot.objects.get_or_create(
                    project=project,
                    name=phase_name,
                    date=today + datetime.timedelta(days=day_offset),
                    defaults={"prototype": prototype},
                )
                if snapshot.instances.exists():
                    continue

                is_as_built = phase_index == len(PHASES) - 1
                rows = []
                for item in prototype.items.select_related("asset"):
                    quantity = item.quantity
                    if is_as_built:
                        quantity += deviations.get(site_id, {}).get(item.asset.type_id, 0)
                    for unit in range(max(quantity, 0)):
                        rows.append(
                            AssetInstance(
                                snapshot=snapshot,
                                asset=item.asset,
                                instance_id=f"{item.asset.type_id}-{unit + 1:03d}",
                                location=f"{name} / Level {1 + (unit % 3)}",
                                custom_fields={
                                    "source": DEMO_TAG,
                                    "condition": "New" if is_as_built else "Good",
                                },
                            )
                        )
                AssetInstance.objects.bulk_create(rows)

            note = ""
            if site_id in REBASELINE:
                note = f"  -> re-baselined to {REBASELINE[site_id][1]} {REBASELINE[site_id][2]}"
            self.say(f"  {site_id}  {name}  [{code} {version}]{note}")
