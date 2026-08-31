"""
Tests for the fleet rollup endpoint.

The one that matters is test_counts_only_the_latest_snapshot_per_project. Every
other assertion here would still pass if that rule broke — the response would
keep its shape, keep its status code, and report a number several times too
large. Nothing would look wrong.
"""

import datetime

from django.test import TestCase, override_settings

from assets.models import Asset, Manufacturer, Vendor, VendorProduct
from projects.models import AssetInstance, Project, Site, Snapshot

OPEN_API = {"API_ALLOW_ANONYMOUS": True}
TODAY = datetime.date(2026, 6, 1)


def fleet_url(asset):
    return f"/api/assets/{asset.id}/fleet/"


@override_settings(**OPEN_API)
class FleetRollupTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        manufacturer = Manufacturer.objects.create(name="Aurora")
        cls.display = Asset.objects.create(
            type_id="DSP-055", manufacturer=manufacturer, model="AR-D55", name="55in Display"
        )
        cls.orphan = Asset.objects.create(
            type_id="NEW-001", manufacturer=manufacturer, model="X", name="Never Installed"
        )

        # Two sites. Each has three snapshots of the SAME physical install, so
        # a rollup that ignores snapshots counts every unit three times.
        cls.projects = []
        for index, (site_id, quantity) in enumerate([("RTL-001", 6), ("RTL-002", 2)]):
            site = Site.objects.create(site_id=site_id, name=f"Store {index + 1}")
            project = Project.objects.create(
                job_id=f"JOB-{index}", name=f"Store {index + 1}", site=site, status="green"
            )
            cls.projects.append(project)
            for offset, phase in enumerate(["Design", "Procurement", "As-Built"]):
                snapshot = Snapshot.objects.create(
                    project=project,
                    name=phase,
                    date=TODAY - datetime.timedelta(days=60 - offset * 30),
                )
                AssetInstance.objects.bulk_create(
                    AssetInstance(snapshot=snapshot, asset=cls.display)
                    for _ in range(quantity)
                )

        cheap = Vendor.objects.create(name="Meridian")
        pricey = Vendor.objects.create(name="Trellis")
        VendorProduct.objects.create(
            asset=cls.display, vendor=pricey, cost="801.00", lead_time_days=21, sku="T-1"
        )
        VendorProduct.objects.create(
            asset=cls.display, vendor=cheap, cost="786.00", lead_time_days=14, sku="M-1"
        )

    def get_fleet(self, asset):
        response = self.client.get(fleet_url(asset))
        self.assertEqual(response.status_code, 200)
        return response.json()

    # -- the rule the whole endpoint rests on --------------------------------

    def test_counts_only_the_latest_snapshot_per_project(self):
        """
        Six units at one store and two at another is eight, not twenty-four.

        Each project holds three snapshots of the same installation. Counting
        across all of them triples every unit and returns a wrong number in a
        correct-looking response, which nothing downstream would flag.
        """
        payload = self.get_fleet(self.display)

        self.assertEqual(AssetInstance.objects.filter(asset=self.display).count(), 24)
        self.assertEqual(payload["summary"]["total_installed"], 8)
        self.assertEqual(payload["summary"]["site_count"], 2)

    def test_each_site_reports_its_latest_snapshot(self):
        payload = self.get_fleet(self.display)
        for site in payload["sites"]:
            self.assertEqual(site["snapshot"]["name"], "As-Built")

    def test_a_newer_snapshot_supersedes_the_previous_count(self):
        """Adding a newer snapshot changes the answer; it does not add to it."""
        project = self.projects[0]
        newer = Snapshot.objects.create(
            project=project, name="Post-Handover", date=TODAY + datetime.timedelta(days=10)
        )
        AssetInstance.objects.create(snapshot=newer, asset=self.display)

        payload = self.get_fleet(self.display)

        # Store 1 drops from 6 to 1 because that is what its newest snapshot
        # says. Store 2 is untouched at 2.
        self.assertEqual(payload["summary"]["total_installed"], 3)
        by_site = {s["site_id"]: s["quantity"] for s in payload["sites"]}
        self.assertEqual(by_site, {"RTL-001": 1, "RTL-002": 2})

    def test_basis_is_stated_in_the_response(self):
        """Clients must be able to tell which question was answered."""
        self.assertEqual(
            self.get_fleet(self.display)["summary"]["basis"],
            "latest snapshot per project",
        )

    # -- shape and content ---------------------------------------------------

    def test_sites_are_ranked_by_quantity(self):
        payload = self.get_fleet(self.display)
        quantities = [site["quantity"] for site in payload["sites"]]
        self.assertEqual(quantities, sorted(quantities, reverse=True))

    def test_site_rows_identify_the_project_and_snapshot(self):
        site = self.get_fleet(self.display)["sites"][0]

        self.assertEqual(site["site_id"], "RTL-001")
        self.assertEqual(site["quantity"], 6)
        self.assertEqual(site["project"]["job_id"], "JOB-0")
        self.assertEqual(site["project"]["status"], "green")
        self.assertIn("date", site["snapshot"])

    def test_replacement_uses_the_cheapest_quote_and_lists_them_all(self):
        replacement = self.get_fleet(self.display)["replacement"]

        self.assertEqual(replacement["vendor"], "Meridian")
        self.assertEqual(replacement["unit_cost"], "786.00")
        self.assertEqual(replacement["lead_time_days"], 14)
        # 8 installed x 786.00 = 6288.00. A snapshot-blind count would say
        # 24 x 786.00 = 18864.00, which is the number this guards against.
        self.assertEqual(replacement["estimated_total"], "6288.00")
        self.assertEqual(len(replacement["quotes"]), 2)

    def test_money_is_a_string_not_a_float(self):
        """Currency through a float is a bug waiting on a big enough fleet."""
        replacement = self.get_fleet(self.display)["replacement"]
        self.assertIsInstance(replacement["unit_cost"], str)
        self.assertIsInstance(replacement["estimated_total"], str)

    # -- edges ---------------------------------------------------------------

    def test_asset_installed_nowhere_returns_an_empty_rollup(self):
        payload = self.get_fleet(self.orphan)

        self.assertEqual(payload["summary"]["total_installed"], 0)
        self.assertEqual(payload["summary"]["site_count"], 0)
        self.assertEqual(payload["sites"], [])

    def test_replacement_is_null_when_no_vendor_quotes_the_asset(self):
        self.assertIsNone(self.get_fleet(self.orphan)["replacement"])

    def test_unknown_asset_is_404(self):
        self.assertEqual(self.client.get("/api/assets/999999/fleet/").status_code, 404)

    def test_project_without_a_site_does_not_break_the_rollup(self):
        """Project.site is nullable, so a site-less project must not 500."""
        project = Project.objects.create(job_id="JOB-NOSITE", name="Unsited")
        snapshot = Snapshot.objects.create(project=project, name="As-Built", date=TODAY)
        AssetInstance.objects.create(snapshot=snapshot, asset=self.display)

        payload = self.get_fleet(self.display)

        unsited = [s for s in payload["sites"] if s["project"]["job_id"] == "JOB-NOSITE"]
        self.assertEqual(len(unsited), 1)
        self.assertIsNone(unsited[0]["site_id"])

    def test_rollup_runs_in_a_constant_number_of_queries(self):
        """The point of the endpoint is replacing a paginated crawl."""
        with self.assertNumQueries(3):
            # 1 asset lookup, 1 aggregate over instances, 1 for vendor quotes.
            self.client.get(fleet_url(self.display))


@override_settings(**OPEN_API)
class FleetAuthTests(TestCase):
    """The action inherits the project's default permission, like any route."""

    @classmethod
    def setUpTestData(cls):
        manufacturer = Manufacturer.objects.create(name="Aurora")
        cls.asset = Asset.objects.create(
            type_id="A-1", manufacturer=manufacturer, model="M", name="Thing"
        )

    @override_settings(API_ALLOW_ANONYMOUS=False)
    def test_requires_a_credential_when_anonymous_access_is_closed(self):
        self.assertEqual(self.client.get(fleet_url(self.asset)).status_code, 401)
