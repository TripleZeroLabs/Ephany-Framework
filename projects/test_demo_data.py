"""
Tests for the demo dataset lifecycle.

The teardown is the part worth guarding. Its failure mode is destroying records
someone created while exploring — data loss with no error, discovered later or
not at all. `Asset.manufacturer` is a CASCADE foreign key, so the obvious
implementation ("delete everything named in the demo lists") takes a user's
assets with it whenever they reuse a demo manufacturer, which is the normal
thing to do when you are trying the software out.
"""

import datetime

from django.core.management import call_command
from django.test import TestCase

from assets.models import (
    Asset,
    AssetAttribute,
    AssetCategory,
    Manufacturer,
    Prototype,
    PrototypeItem,
    Vendor,
)
from projects.demo_data import DEMO_TAG, PROTOTYPES, SITES, clear_demo_data
from projects.models import AssetInstance, Project, Site, Snapshot


class SeedDemoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", verbosity=0)

    def test_loads_a_portfolio(self):
        self.assertEqual(Site.objects.count(), len(SITES))
        self.assertEqual(Project.objects.count(), len(SITES))
        self.assertEqual(Snapshot.objects.count(), len(SITES) * 3)
        self.assertGreater(AssetInstance.objects.count(), 3000)

    def test_every_snapshot_declares_the_standard_it_was_built_to(self):
        self.assertEqual(Snapshot.objects.filter(prototype__isnull=True).count(), 0)

    def test_prototypes_are_versioned(self):
        """Two revisions of the retail standard, so the data is mid-rollout."""
        retail = Prototype.objects.filter(code="RTL-STD").order_by("version")

        self.assertEqual([p.version for p in retail], ["2024.1", "2025.1"])
        self.assertNotEqual(
            {(i.asset.type_id, i.quantity) for i in retail[0].items.all()},
            {(i.asset.type_id, i.quantity) for i in retail[1].items.all()},
        )

    def test_a_project_can_change_standard_between_phases(self):
        """The case Snapshot.prototype exists for: a change order mid-build."""
        project = Project.objects.get(site__site_id="RTL-004")
        versions = [s.prototype.version for s in project.snapshots.order_by("date")]

        self.assertEqual(versions, ["2024.1", "2024.1", "2025.1"])

    def test_seeded_assets_pass_custom_field_validation(self):
        """custom_fields is validated against AssetAttribute, so the demo must comply."""
        for asset in Asset.objects.all():
            with self.subTest(asset=asset.type_id):
                asset.clean()

    def test_running_twice_is_stable(self):
        before = AssetInstance.objects.count()
        call_command("seed_demo", verbosity=0)
        self.assertEqual(AssetInstance.objects.count(), before)

    def test_a_referenced_prototype_cannot_be_edited(self):
        """Reseeding must not try to rewrite a version snapshots already use."""
        from django.core.exceptions import ValidationError

        prototype = Prototype.objects.filter(code="RTL-STD", version="2024.1").first()
        self.assertTrue(prototype.is_locked)
        with self.assertRaises(ValidationError):
            PrototypeItem.objects.create(
                prototype=prototype, asset=Asset.objects.first(), quantity=1
            )


class ClearDemoTests(TestCase):
    """Teardown must remove the demo and nothing else."""

    def setUp(self):
        call_command("seed_demo", verbosity=0)

    def test_removes_the_demo(self):
        clear_demo_data()

        self.assertEqual(Project.objects.filter(custom_fields__source=DEMO_TAG).count(), 0)
        self.assertEqual(AssetInstance.objects.filter(custom_fields__source=DEMO_TAG).count(), 0)
        self.assertEqual(Prototype.objects.count(), 0)
        self.assertEqual(Asset.objects.count(), 0)
        self.assertEqual(Manufacturer.objects.count(), 0)

    def test_keeps_a_manufacturer_a_user_asset_depends_on(self):
        """
        The regression this suite exists for.

        Asset.manufacturer is CASCADE. Deleting the demo manufacturer takes any
        asset built on it too — silently, with the right exit code.
        """
        manufacturer = Manufacturer.objects.get(name="Aurora Systems")
        mine = Asset.objects.create(
            type_id="MY-001", manufacturer=manufacturer, model="M", name="Mine"
        )

        clear_demo_data()

        self.assertTrue(Asset.objects.filter(pk=mine.pk).exists(), "user asset was destroyed")
        self.assertTrue(Manufacturer.objects.filter(pk=manufacturer.pk).exists())

    def test_keeps_a_category_a_user_asset_depends_on(self):
        """Category is SET_NULL, so the loss is quieter: the asset survives, mis-filed."""
        category = AssetCategory.objects.get(name="Displays")
        manufacturer = Manufacturer.objects.create(name="Mine Ltd")
        mine = Asset.objects.create(
            type_id="MY-002", manufacturer=manufacturer, category=category,
            model="M", name="Mine",
        )

        clear_demo_data()
        mine.refresh_from_db()

        self.assertIsNotNone(mine.category, "user asset lost its category")

    def test_keeps_a_site_a_user_project_uses(self):
        site = Site.objects.get(site_id="RTL-001")
        Project.objects.create(job_id="MY-JOB", name="Mine", site=site)

        clear_demo_data()

        self.assertTrue(Site.objects.filter(pk=site.pk).exists())
        self.assertTrue(Project.objects.filter(job_id="MY-JOB").exists())

    def test_keeps_a_prototype_a_user_snapshot_is_measured_against(self):
        prototype = Prototype.objects.get(code="RTL-STD", version="2024.1")
        project = Project.objects.create(job_id="MY-JOB", name="Mine")
        Snapshot.objects.create(
            project=project, name="Mine", date=datetime.date(2026, 1, 1), prototype=prototype
        )

        clear_demo_data()

        self.assertTrue(Prototype.objects.filter(pk=prototype.pk).exists())
        self.assertTrue(prototype.items.exists(), "kept prototype lost its items")

    def test_keeps_an_asset_a_user_instance_points_at(self):
        """AssetInstance.asset is PROTECT — deleting would raise, not cascade."""
        asset = Asset.objects.get(type_id="DSP-055")
        project = Project.objects.create(job_id="MY-JOB", name="Mine")
        snapshot = Snapshot.objects.create(
            project=project, name="Mine", date=datetime.date(2026, 1, 1)
        )
        AssetInstance.objects.create(snapshot=snapshot, asset=asset)

        clear_demo_data()

        self.assertTrue(Asset.objects.filter(pk=asset.pk).exists())

    def test_explains_everything_it_keeps(self):
        """A silent skip is indistinguishable from a bug."""
        manufacturer = Manufacturer.objects.get(name="Aurora Systems")
        Asset.objects.create(type_id="MY-003", manufacturer=manufacturer, model="M", name="Mine")

        _deleted, kept = clear_demo_data()

        self.assertTrue(any("Aurora Systems" in reason for reason in kept))
        self.assertTrue(all(":" in reason for reason in kept), "a reason was not given")

    def test_distinguishes_user_held_records_from_demo_held_ones(self):
        """
        "Kept because you depend on it" and "kept because the demo does" need
        different wording — only the first is something to act on.
        """
        prototype = Prototype.objects.get(code="RTL-STD", version="2024.1")
        project = Project.objects.create(job_id="MY-JOB", name="Mine")
        Snapshot.objects.create(
            project=project, name="Mine", date=datetime.date(2026, 1, 1), prototype=prototype
        )

        _deleted, kept = clear_demo_data()
        assets_kept = [r for r in kept if r.startswith("asset ")]

        self.assertTrue(assets_kept, "expected the kept prototype to hold its assets")
        for reason in assets_kept:
            self.assertIn("held by", reason)
            self.assertNotIn("you created", reason)

    def test_is_safe_to_run_twice(self):
        clear_demo_data()
        deleted, kept = clear_demo_data()
        self.assertEqual((deleted, kept), ({}, []))

    def test_dry_run_deletes_nothing(self):
        before = (Project.objects.count(), Asset.objects.count(), AssetInstance.objects.count())

        call_command("clear_demo", "--dry-run", verbosity=0)

        after = (Project.objects.count(), Asset.objects.count(), AssetInstance.objects.count())
        self.assertEqual(before, after)

    def test_seed_demo_flush_uses_the_same_safe_teardown(self):
        manufacturer = Manufacturer.objects.get(name="Aurora Systems")
        mine = Asset.objects.create(
            type_id="MY-004", manufacturer=manufacturer, model="M", name="Mine"
        )

        call_command("seed_demo", "--flush", verbosity=0)

        self.assertTrue(Asset.objects.filter(pk=mine.pk).exists())
        self.assertEqual(Project.objects.filter(custom_fields__source=DEMO_TAG).count(), len(SITES))


class PrototypeModelTests(TestCase):
    """The immutability rule that makes versioned standards trustworthy."""

    @classmethod
    def setUpTestData(cls):
        cls.manufacturer = Manufacturer.objects.create(name="Acme")
        cls.asset = Asset.objects.create(
            type_id="A-1", manufacturer=cls.manufacturer, model="M", name="Thing"
        )
        cls.prototype = Prototype.objects.create(code="STD", version="1.0", name="Standard")

    def test_unreferenced_prototype_is_editable(self):
        self.assertFalse(self.prototype.is_locked)
        PrototypeItem.objects.create(prototype=self.prototype, asset=self.asset, quantity=2)
        self.assertEqual(self.prototype.items.count(), 1)

    def test_referenced_prototype_is_locked(self):
        """
        Editing a version snapshots were built to rewrites history: a site that
        passed inspection becomes non-compliant because someone edited a spec.
        """
        from django.core.exceptions import ValidationError

        project = Project.objects.create(job_id="J-1", name="Project")
        Snapshot.objects.create(
            project=project, name="As-Built", date=datetime.date(2026, 1, 1),
            prototype=self.prototype,
        )

        self.assertTrue(self.prototype.is_locked)
        with self.assertRaises(ValidationError):
            PrototypeItem.objects.create(prototype=self.prototype, asset=self.asset, quantity=1)

    def test_versions_of_one_standard_are_separate_records(self):
        other = Prototype.objects.create(code="STD", version="2.0", name="Standard")
        self.assertNotEqual(self.prototype.pk, other.pk)

    def test_code_and_version_together_are_unique(self):
        from django.db import IntegrityError

        with self.assertRaises(IntegrityError):
            Prototype.objects.create(code="STD", version="1.0", name="Duplicate")
