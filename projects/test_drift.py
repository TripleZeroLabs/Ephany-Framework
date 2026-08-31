"""
Tests for drift reporting and prototype instantiation.

The load-bearing one is test_measures_against_the_snapshots_own_version. Every
other assertion here would still pass if drift compared against the newest
revision of a standard instead of the one a snapshot declares — the response
would keep its shape and its status code, and simply report sites as broken
that are not.
"""

import datetime

from django.test import TestCase, override_settings

from assets.models import Asset, Manufacturer, Prototype, PrototypeItem
from projects.models import AssetInstance, Project, Snapshot

OPEN_API = {"API_ALLOW_ANONYMOUS": True}
DATE = datetime.date(2026, 6, 1)


@override_settings(**OPEN_API)
class SnapshotDriftTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        manufacturer = Manufacturer.objects.create(name="Acme")
        cls.chair = Asset.objects.create(
            type_id="CHR-1", manufacturer=manufacturer, model="C", name="Chair"
        )
        cls.light = Asset.objects.create(
            type_id="LGT-1", manufacturer=manufacturer, model="L", name="Light"
        )
        cls.rogue = Asset.objects.create(
            type_id="RGE-1", manufacturer=manufacturer, model="R", name="Not In Any Standard"
        )

        # Two revisions: v2 raises the light count from 10 to 20.
        cls.v1 = Prototype.objects.create(code="STD", version="1.0", name="Standard")
        PrototypeItem.objects.create(prototype=cls.v1, asset=cls.chair, quantity=4)
        PrototypeItem.objects.create(prototype=cls.v1, asset=cls.light, quantity=10)

        cls.v2 = Prototype.objects.create(code="STD", version="2.0", name="Standard")
        PrototypeItem.objects.create(prototype=cls.v2, asset=cls.chair, quantity=4)
        PrototypeItem.objects.create(prototype=cls.v2, asset=cls.light, quantity=20)

        cls.project = Project.objects.create(job_id="J-1", name="Site One")

    def build_snapshot(self, prototype, contents, name="As-Built"):
        snapshot = Snapshot.objects.create(
            project=self.project, name=name, date=DATE, prototype=prototype
        )
        for asset, count in contents.items():
            AssetInstance.objects.bulk_create(
                AssetInstance(snapshot=snapshot, asset=asset) for _ in range(count)
            )
        return snapshot

    def drift(self, snapshot):
        response = self.client.get(f"/api/snapshots/{snapshot.id}/drift/")
        self.assertEqual(response.status_code, 200)
        return response.json()

    # -- the rule the report rests on ----------------------------------------

    def test_measures_against_the_snapshots_own_version(self):
        """
        A site built to v1 stays compliant after v2 is published.

        Comparing against the newest revision instead would report this site as
        ten lights short for doing exactly what it was told to do — and would
        turn every existing site red the day a standard is revised.
        """
        snapshot = self.build_snapshot(self.v1, {self.chair: 4, self.light: 10})

        payload = self.drift(snapshot)

        self.assertEqual(payload["prototype"]["version"], "1.0")
        self.assertTrue(payload["summary"]["is_compliant"])

    def test_two_sites_on_different_versions_are_both_compliant(self):
        older = self.build_snapshot(self.v1, {self.chair: 4, self.light: 10}, name="Old Site")
        newer = self.build_snapshot(self.v2, {self.chair: 4, self.light: 20}, name="New Site")

        self.assertTrue(self.drift(older)["summary"]["is_compliant"])
        self.assertTrue(self.drift(newer)["summary"]["is_compliant"])

    def test_a_project_can_change_version_between_snapshots(self):
        """Each phase is judged against what it declared, not the project's latest."""
        design = self.build_snapshot(self.v1, {self.chair: 4, self.light: 10}, name="Design")
        as_built = self.build_snapshot(self.v2, {self.chair: 4, self.light: 20}, name="As-Built")

        self.assertEqual(self.drift(design)["prototype"]["version"], "1.0")
        self.assertEqual(self.drift(as_built)["prototype"]["version"], "2.0")
        self.assertTrue(self.drift(design)["summary"]["is_compliant"])
        self.assertTrue(self.drift(as_built)["summary"]["is_compliant"])

    # -- the four statuses ---------------------------------------------------

    def test_reports_a_shortfall(self):
        snapshot = self.build_snapshot(self.v1, {self.chair: 4, self.light: 7})

        payload = self.drift(snapshot)
        line = next(l for l in payload["lines"] if l["type_id"] == "LGT-1")

        self.assertEqual((line["status"], line["expected"], line["actual"], line["delta"]),
                         ("short", 10, 7, -3))
        self.assertFalse(payload["summary"]["is_compliant"])

    def test_reports_a_surplus(self):
        snapshot = self.build_snapshot(self.v1, {self.chair: 6, self.light: 10})

        line = next(l for l in self.drift(snapshot)["lines"] if l["type_id"] == "CHR-1")

        self.assertEqual((line["status"], line["delta"]), ("over", 2))

    def test_reports_something_installed_that_is_not_in_the_standard(self):
        """A distinct finding from a shortfall: nobody specified this at all."""
        snapshot = self.build_snapshot(
            self.v1, {self.chair: 4, self.light: 10, self.rogue: 3}
        )

        payload = self.drift(snapshot)
        line = next(l for l in payload["lines"] if l["type_id"] == "RGE-1")

        self.assertEqual((line["status"], line["expected"], line["actual"]), ("unexpected", 0, 3))
        self.assertFalse(payload["summary"]["is_compliant"])

    def test_an_absent_optional_item_is_reported_but_not_a_fault(self):
        """Optional means site-dependent. Reporting it as non-compliance is noise."""
        optional_prototype = Prototype.objects.create(code="OPT", version="1.0", name="Opt")
        PrototypeItem.objects.create(prototype=optional_prototype, asset=self.chair, quantity=4)
        PrototypeItem.objects.create(
            prototype=optional_prototype, asset=self.light, quantity=5, is_required=False
        )
        snapshot = self.build_snapshot(optional_prototype, {self.chair: 4})

        payload = self.drift(snapshot)
        line = next(l for l in payload["lines"] if l["type_id"] == "LGT-1")

        self.assertEqual(line["status"], "short")
        self.assertFalse(line["is_required"])
        self.assertTrue(payload["summary"]["is_compliant"], "optional shortfall counted as a fault")

    # -- edges ---------------------------------------------------------------

    def test_snapshot_without_a_prototype_is_409(self):
        """"No baseline" is a different answer from "no differences"."""
        snapshot = Snapshot.objects.create(project=self.project, name="Ad hoc", date=DATE)

        response = self.client.get(f"/api/snapshots/{snapshot.id}/drift/")

        self.assertEqual(response.status_code, 409)
        self.assertIn("no prototype", response.json()["detail"])

    def test_empty_snapshot_reports_everything_short(self):
        snapshot = self.build_snapshot(self.v1, {})

        payload = self.drift(snapshot)

        self.assertEqual(payload["summary"]["short"], 2)
        self.assertEqual(payload["summary"]["units_actual"], 0)
        self.assertEqual(payload["summary"]["units_expected"], 14)

    def test_unknown_snapshot_is_404(self):
        self.assertEqual(self.client.get("/api/snapshots/999999/drift/").status_code, 404)


@override_settings(**OPEN_API)
class InstantiateTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        manufacturer = Manufacturer.objects.create(name="Acme")
        cls.chair = Asset.objects.create(
            type_id="CHR-1", manufacturer=manufacturer, model="C", name="Chair"
        )
        cls.mat = Asset.objects.create(
            type_id="MAT-1", manufacturer=manufacturer, model="M", name="Optional Mat"
        )
        cls.prototype = Prototype.objects.create(code="STD", version="1.0", name="Standard")
        PrototypeItem.objects.create(prototype=cls.prototype, asset=cls.chair, quantity=5)
        PrototypeItem.objects.create(
            prototype=cls.prototype, asset=cls.mat, quantity=2, is_required=False
        )
        cls.project = Project.objects.create(job_id="J-1", name="Site One")

    def instantiate(self, **overrides):
        body = {"prototype": self.prototype.id, "name": "Design Intent", "date": "2026-06-01"}
        body.update(overrides)
        return self.client.post(
            f"/api/projects/{self.project.id}/instantiate/", body, content_type="application/json"
        )

    def test_creates_a_snapshot_populated_from_the_standard(self):
        response = self.instantiate()

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["instances_created"], 7)
        self.assertEqual(payload["prototype"]["version"], "1.0")

        snapshot = Snapshot.objects.get(pk=payload["snapshot"]["id"])
        self.assertEqual(snapshot.prototype, self.prototype)
        self.assertEqual(snapshot.instances.count(), 7)

    def test_quantities_expand_into_individual_instances(self):
        """Five chairs is five rows, so each can carry its own location and tag."""
        self.instantiate()

        snapshot = Snapshot.objects.latest("id")
        self.assertEqual(snapshot.instances.filter(asset=self.chair).count(), 5)

    def test_the_result_is_immediately_compliant(self):
        """Stamping a standard and then measuring against it must agree."""
        snapshot_id = self.instantiate().json()["snapshot"]["id"]

        drift = self.client.get(f"/api/snapshots/{snapshot_id}/drift/").json()

        self.assertTrue(drift["summary"]["is_compliant"])
        self.assertEqual(drift["summary"]["short"], 0)

    def test_optional_items_can_be_left_out(self):
        response = self.instantiate(include_optional=False)

        self.assertEqual(response.json()["instances_created"], 5)

    def test_adopting_a_new_standard_is_the_same_operation(self):
        """There is no separate re-baselining path to get wrong."""
        self.instantiate(name="Design Intent")
        newer = Prototype.objects.create(code="STD", version="2.0", name="Standard")
        PrototypeItem.objects.create(prototype=newer, asset=self.chair, quantity=9)

        response = self.instantiate(prototype=newer.id, name="As-Built", date="2026-09-01")

        self.assertEqual(response.status_code, 201)
        versions = [s.prototype.version for s in self.project.snapshots.order_by("date")]
        self.assertEqual(versions, ["1.0", "2.0"])

    def test_rejects_an_unknown_prototype(self):
        self.assertEqual(self.instantiate(prototype=999999).status_code, 400)

    def test_rejects_a_missing_date(self):
        response = self.client.post(
            f"/api/projects/{self.project.id}/instantiate/",
            {"prototype": self.prototype.id, "name": "No Date"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)


@override_settings(**OPEN_API)
class PrototypeEndpointTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        manufacturer = Manufacturer.objects.create(name="Acme")
        cls.asset = Asset.objects.create(
            type_id="A-1", manufacturer=manufacturer, model="M", name="Thing"
        )
        cls.v1 = Prototype.objects.create(code="STD", version="1.0", name="Standard")
        PrototypeItem.objects.create(prototype=cls.v1, asset=cls.asset, quantity=3)
        Prototype.objects.create(code="OTHER", version="1.0", name="Other")

    def test_lists_standards_with_their_items(self):
        payload = self.client.get("/api/prototypes/").json()

        standard = next(p for p in payload["results"] if p["code"] == "STD")
        self.assertEqual(standard["item_count"], 1)
        self.assertEqual(standard["total_units"], 3)
        self.assertEqual(standard["items"][0]["type_id"], "A-1")

    def test_filters_to_one_standards_revisions(self):
        Prototype.objects.create(code="STD", version="2.0", name="Standard")

        payload = self.client.get("/api/prototypes/?code=STD").json()

        self.assertEqual(payload["count"], 2)
        self.assertEqual({p["version"] for p in payload["results"]}, {"1.0", "2.0"})

    def test_reports_whether_a_version_is_locked(self):
        payload = self.client.get("/api/prototypes/").json()
        standard = next(p for p in payload["results"] if p["code"] == "STD")
        self.assertFalse(standard["is_locked"])

        project = Project.objects.create(job_id="J-1", name="Site")
        Snapshot.objects.create(
            project=project, name="As-Built", date=DATE, prototype=self.v1
        )

        payload = self.client.get("/api/prototypes/").json()
        standard = next(p for p in payload["results"] if p["code"] == "STD")
        self.assertTrue(standard["is_locked"])
        self.assertEqual(standard["snapshot_count"], 1)

    def test_editing_a_locked_version_through_the_api_is_rejected(self):
        """The model guard has to hold at the HTTP boundary too."""
        project = Project.objects.create(job_id="J-1", name="Site")
        Snapshot.objects.create(project=project, name="As-Built", date=DATE, prototype=self.v1)

        response = self.client.post(
            "/api/prototype-items/",
            {"prototype": self.v1.id, "asset_id": self.asset.id, "quantity": 99},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
