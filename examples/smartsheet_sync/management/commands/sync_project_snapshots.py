"""
EXAMPLE INTEGRATION — import a folder of sheets as Project Snapshots.

A second worked example, and a deliberately harder one than
`sync_projects_from_smartsheet`. Read that file first: it covers the basic
fetch-map-diff-write shape. This one adds the three things that make real
importers messy.

## What this one adds

**Many sources, not one.** It walks a folder of sheets rather than reading a
single sheet, so a partial failure is expected. One unreadable sheet logs a
warning and the loop continues; it does not abort the other forty.

**Structure encoded in a filename.** Each sheet is named

    <prefix>_<job_id>_<YYYY-MM-DD>_<snapshot_name>

and STEP 2 pulls the job ID, date, and snapshot name out of it. This is a
common shape when the external system has no schema for the metadata you need.
It is also fragile, which is why every parse failure is a skip-with-warning
rather than an exception — one badly named sheet should not cost you the run.

**A second lookup source.** Project names live in a different sheet entirely,
loaded once up front into a dict rather than re-fetched per row. Same idea as
any N+1 fix: one query for the lookup table, then in-memory joins.

## The choice that differs from the other example

`sync_projects_from_smartsheet` refuses to create Projects. This command
creates them freely, because here the folder of sheets *is* the system of
record for which snapshots exist — there is no prior Django record to match
against. Decide which side owns the truth before you write an importer; it
determines whether an unmatched row is an error or an insert.

## Destructive behavior — read before running

Re-importing an existing snapshot DELETES its AssetInstances and rebuilds them
from the sheet. This is intentional: a snapshot is meant to mirror its sheet
exactly, and merging would leave behind rows deleted upstream. It also means a
run against the wrong folder ID will happily wipe good data.

Use --dry-run first. Every time.

## Quantity expansion

A row with Quantity=12 creates twelve AssetInstance records, not one row with
a quantity field. That is a modelling decision inherited from the schema: each
instance can carry its own location, instance_id, and custom_fields, which a
quantity column could not express. Worth understanding before you copy this
loop — for a source where units are genuinely interchangeable, a quantity
field on a single row would be the better model.

## Configuration

    SMARTSHEET_SNAPSHOTS_FOLDER_ID   folder of per-snapshot sheets
    SMARTSHEET_LOOKUP_SHEET_ID       sheet mapping Project ID -> project name

Both are overridable with --folder-id and --lookup-sheet-id. See .env.example.

## Usage

    export SMARTSHEET_SNAPSHOTS_FOLDER_ID=<your-folder-id>
    export SMARTSHEET_LOOKUP_SHEET_ID=<your-lookup-sheet-id>
    python manage.py sync_project_snapshots <API_KEY> --dry-run
    python manage.py sync_project_snapshots <API_KEY>
"""

import requests
from datetime import date

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from assets.models import Asset
from projects.models import AssetInstance, Project, Snapshot

# Everything that knows Smartsheet exists lives in client.py. Swap that module
# and this command works against a different source unchanged.
from examples.smartsheet_sync import client

# ---------------------------------------------------------------------------
# STEP 1 - Declare the mapping
#
# Fewer columns than the other example, because the interesting metadata is
# encoded in each sheet's *name* rather than its cells. See section 3a below.
# ---------------------------------------------------------------------------

# Job IDs in sheet names may or may not carry the prefix. Normalising both
# forms to one canonical value is what makes the lookup below reliable - a
# source that is inconsistent about identifiers is the norm, not the exception.
JPS_PREFIX = "JPS-"

# Column titles expected in each per-snapshot sheet.
COL_ASSET_ID = "Asset ID"      # matched against Asset.type_id in the catalog
COL_QUANTITY = "Quantity"      # expanded into N AssetInstance rows

# Column titles in the separate lookup sheet.
COL_PROJECT_ID = "Project ID"
COL_PROJECT_NAME = "Smartsheet Project Name"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize_job_id(raw: str) -> str:
    """
    Return a job ID in canonical prefixed form.

    Sheet names are maintained by hand, so some carry the prefix and some do
    not. Normalising on the way in means the lookup dict needs only one key
    per project. If your own identifiers are inconsistent in a different way,
    this is the function to replace.
    """
    raw = raw.strip()
    return raw if raw.startswith(JPS_PREFIX) else f"{JPS_PREFIX}{raw}"


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------

class Command(BaseCommand):
    help = (
        "Sync all sheets in a Smartsheet folder into Django as Project "
        "Snapshots with AssetInstances. Set SMARTSHEET_SNAPSHOTS_FOLDER_ID and "
        "SMARTSHEET_LOOKUP_SHEET_ID, or pass --folder-id / --lookup-sheet-id."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "api_key",
            type=str,
            help="Smartsheet API Bearer token",
        )
        parser.add_argument(
            "--folder-id",
            type=str,
            default=None,
            help=(
                "Smartsheet folder ID containing the snapshot sheets. "
                "Defaults to the SMARTSHEET_SNAPSHOTS_FOLDER_ID environment variable."
            ),
        )
        parser.add_argument(
            "--lookup-sheet-id",
            type=str,
            default=None,
            help=(
                "Smartsheet sheet ID mapping Project ID to project name. "
                "Defaults to the SMARTSHEET_LOOKUP_SHEET_ID environment variable."
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Preview changes without writing to the database.",
        )

    def handle(self, *args, **options):
        api_key: str = options["api_key"]
        dry_run: bool = options["dry_run"]

        folder_id: str = options["folder_id"] or settings.SMARTSHEET_SNAPSHOTS_FOLDER_ID
        if not folder_id:
            raise CommandError(
                "No Smartsheet folder ID configured. Set SMARTSHEET_SNAPSHOTS_FOLDER_ID "
                "in your .env file, or pass --folder-id <FOLDER_ID>."
            )

        lookup_sheet_id: str = options["lookup_sheet_id"] or settings.SMARTSHEET_LOOKUP_SHEET_ID
        if not lookup_sheet_id:
            raise CommandError(
                "No Smartsheet lookup sheet ID configured. Set SMARTSHEET_LOOKUP_SHEET_ID "
                "(or SMARTSHEET_PROJECTS_SHEET_ID) in your .env file, or pass "
                "--lookup-sheet-id <SHEET_ID>."
            )

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no database changes will be made.\n"))

        # ------------------------------------------------------------------
        # STEP 2a - Load the lookup table once
        #
        # Fetched once and held in a dict rather than queried per sheet. With
        # forty sheets in the folder, the per-sheet version would make forty
        # redundant HTTP calls. Same instinct as avoiding an N+1 query.
        #
        # Missing columns here are fatal, unlike almost everywhere else in
        # this file: without the lookup nothing downstream can resolve, so
        # failing immediately beats forty identical warnings.
        # ------------------------------------------------------------------
        self.stdout.write("Loading project name lookup sheet…")
        try:
            lookup_sheet = client.fetch(f"sheets/{lookup_sheet_id}", api_key)
        except requests.HTTPError as exc:
            raise CommandError(f"Failed to fetch lookup sheet: {exc}") from exc

        lookup_col_map = client.column_map(lookup_sheet)
        if COL_PROJECT_ID not in lookup_col_map or COL_PROJECT_NAME not in lookup_col_map:
            raise CommandError(
                f"Lookup sheet is missing required columns: "
                f'"{COL_PROJECT_ID}" and/or "{COL_PROJECT_NAME}"'
            )

        project_name_by_job_id: dict[str, str] = {}
        for row in client.rows(lookup_sheet):
            pid = client.cell_value(row, lookup_col_map, COL_PROJECT_ID)
            pname = client.cell_value(row, lookup_col_map, COL_PROJECT_NAME)
            if pid and pname:
                project_name_by_job_id[str(pid).strip()] = str(pname).strip()

        self.stdout.write(
            self.style.SUCCESS(f"  Loaded {len(project_name_by_job_id)} project name entries.\n")
        )

        # ------------------------------------------------------------------
        # STEP 2b - List the sheets to import
        # ------------------------------------------------------------------
        self.stdout.write(f"Fetching folder {folder_id}…")
        try:
            folder = client.fetch(f"folders/{folder_id}", api_key)
        except requests.HTTPError as exc:
            raise CommandError(f"Failed to fetch folder: {exc}") from exc

        sheets = folder.get("sheets", [])
        if not sheets:
            self.stdout.write(self.style.WARNING("No sheets found in folder. Nothing to import."))
            return

        self.stdout.write(self.style.SUCCESS(f"  Found {len(sheets)} sheet(s).\n"))

        # ------------------------------------------------------------------
        # STEP 3 - Process each sheet independently
        #
        # Every failure mode below is a `continue`, never a raise. One sheet
        # with a malformed name, an unknown project, or a missing column
        # should cost you that sheet and nothing else. The warning counter in
        # the summary is how you find out it happened.
        # ------------------------------------------------------------------
        total_projects_created = 0
        total_projects_updated = 0
        total_snapshots_created = 0
        total_snapshots_overwritten = 0
        total_instances_created = 0
        total_warnings = 0

        for sheet_meta in sheets:
            sheet_id = sheet_meta["id"]
            sheet_name: str = sheet_meta["name"]

            self.stdout.write(f"Processing sheet: {sheet_name}")

            # --------------------------------------------------------------
            # 3a. Parse metadata out of the sheet name
            #
            # Fragile by nature: it depends on a naming convention no system
            # enforces. Hence the length check and the explicit date parse,
            # both of which skip rather than raise.
            # --------------------------------------------------------------
            segments = sheet_name.split("_")
            if len(segments) < 4:
                self.stdout.write(
                    self.style.WARNING(
                        f"  SKIP: sheet name has fewer than 4 segments: '{sheet_name}'"
                    )
                )
                total_warnings += 1
                continue

            raw_job_id = segments[1]
            raw_date = segments[2]
            snapshot_name = "_".join(segments[3:])

            job_id = _normalize_job_id(raw_job_id)

            try:
                snapshot_date = date.fromisoformat(raw_date)
            except ValueError:
                self.stdout.write(
                    self.style.WARNING(
                        f"  SKIP: cannot parse date '{raw_date}' in sheet '{sheet_name}'"
                    )
                )
                total_warnings += 1
                continue

            # --------------------------------------------------------------
            # 3b. Resolve project name from lookup sheet
            # --------------------------------------------------------------
            project_name = project_name_by_job_id.get(job_id)
            if not project_name:
                self.stdout.write(
                    self.style.WARNING(
                        f"  SKIP: no project name found in lookup sheet for job_id '{job_id}'"
                    )
                )
                total_warnings += 1
                continue

            # --------------------------------------------------------------
            # 3c. Create / update Project
            # --------------------------------------------------------------
            if not dry_run:
                project, project_created = Project.objects.get_or_create(
                    job_id=job_id,
                    defaults={"name": project_name},
                )
                if project_created:
                    total_projects_created += 1
                    self.stdout.write(f"  [+] Created Project: {job_id} — {project_name}")
                elif project.name != project_name:
                    project.name = project_name
                    project.save(update_fields=["name", "updated_at"])
                    total_projects_updated += 1
                    self.stdout.write(
                        f"  [~] Updated Project name: {job_id} → '{project_name}'"
                    )
                else:
                    self.stdout.write(f"  [=] Project exists: {job_id} — {project_name}")
            else:
                self.stdout.write(
                    f"  [DRY] Would create/update Project: {job_id} — {project_name}"
                )

            # --------------------------------------------------------------
            # 3d. Create or REBUILD the Snapshot
            #
            # The destructive step. An existing snapshot has its instances
            # deleted and rebuilt, so the snapshot always mirrors the sheet
            # exactly. Merging instead would strand rows that were deleted
            # upstream, and a snapshot that quietly disagrees with its source
            # is worse than no snapshot.
            #
            # The delete count is printed because silently discarding rows is
            # exactly the kind of thing you want to see in a log.
            # --------------------------------------------------------------
            if not dry_run:
                snapshot, snapshot_created = Snapshot.objects.get_or_create(
                    project=project,
                    name=snapshot_name,
                    date=snapshot_date,
                )
                if snapshot_created:
                    total_snapshots_created += 1
                    self.stdout.write(
                        f"  [+] Created Snapshot: '{snapshot_name}' on {snapshot_date}"
                    )
                else:
                    deleted_count, _ = snapshot.instances.all().delete()
                    total_snapshots_overwritten += 1
                    self.stdout.write(
                        f"  [~] Overwriting Snapshot: '{snapshot_name}' on {snapshot_date} "
                        f"(cleared {deleted_count} existing instance(s))"
                    )
            else:
                self.stdout.write(
                    f"  [DRY] Would create/overwrite Snapshot: "
                    f"'{snapshot_name}' on {snapshot_date}"
                )

            # --------------------------------------------------------------
            # 3e. Fetch full sheet data
            # --------------------------------------------------------------
            try:
                sheet_data = client.fetch(f"sheets/{sheet_id}", api_key)
            except requests.HTTPError as exc:
                self.stdout.write(
                    self.style.WARNING(f"  SKIP sheet data: HTTP error fetching sheet — {exc}")
                )
                total_warnings += 1
                continue

            col_map = client.column_map(sheet_data)

            if COL_ASSET_ID not in col_map:
                self.stdout.write(
                    self.style.WARNING(
                        f"  SKIP: sheet missing required column '{COL_ASSET_ID}'"
                    )
                )
                total_warnings += 1
                continue

            if COL_QUANTITY not in col_map:
                self.stdout.write(
                    self.style.WARNING(
                        f"  SKIP: sheet missing required column '{COL_QUANTITY}'"
                    )
                )
                total_warnings += 1
                continue

            # --------------------------------------------------------------
            # 3f. STEP 4 - Expand rows into AssetInstances
            #
            # One row with Quantity=N becomes N records, each independently
            # addressable later. Rows referencing an unknown Asset are skipped
            # with a warning: the catalog is the authority on what exists, and
            # a snapshot must not invent assets to satisfy a sheet.
            # --------------------------------------------------------------
            sheet_instances = 0

            for row in client.rows(sheet_data):
                raw_asset_id = client.cell_value(row, col_map, COL_ASSET_ID)
                raw_quantity = client.cell_value(row, col_map, COL_QUANTITY)

                if not raw_asset_id:
                    continue  # blank row — skip silently

                asset_id = str(raw_asset_id).strip()

                try:
                    quantity = int(float(raw_quantity)) if raw_quantity is not None else 0
                except (ValueError, TypeError):
                    self.stdout.write(
                        self.style.WARNING(
                            f"  WARNING: invalid quantity '{raw_quantity}' "
                            f"for asset '{asset_id}' (row {row.get('rowNumber')}) — skipping row"
                        )
                    )
                    total_warnings += 1
                    continue

                if quantity <= 0:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  WARNING: zero/negative quantity for asset '{asset_id}' "
                            f"(row {row.get('rowNumber')}) — skipping row"
                        )
                    )
                    total_warnings += 1
                    continue

                try:
                    asset = Asset.objects.get(type_id=asset_id)
                except Asset.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  WARNING: no Asset with type_id='{asset_id}' — skipping row"
                        )
                    )
                    total_warnings += 1
                    continue

                if not dry_run:
                    for _ in range(quantity):
                        AssetInstance.objects.create(snapshot=snapshot, asset=asset)

                sheet_instances += quantity

            total_instances_created += sheet_instances

            if dry_run:
                self.stdout.write(
                    f"  [DRY] Would create {sheet_instances} AssetInstance(s)"
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  Created {sheet_instances} AssetInstance(s) for this snapshot."
                    )
                )

        # ------------------------------------------------------------------
        # 4. Summary
        # ------------------------------------------------------------------
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("Sync complete."))
        self.stdout.write(f"  Projects created  : {total_projects_created}")
        self.stdout.write(f"  Projects updated  : {total_projects_updated}")
        self.stdout.write(f"  Snapshots created : {total_snapshots_created}")
        self.stdout.write(f"  Snapshots cleared : {total_snapshots_overwritten}")
        self.stdout.write(f"  AssetInstances    : {total_instances_created}")
        if total_warnings:
            self.stdout.write(self.style.WARNING(f"  Warnings          : {total_warnings}"))
        if dry_run:
            self.stdout.write(self.style.WARNING("\nDRY RUN — no changes were written."))
