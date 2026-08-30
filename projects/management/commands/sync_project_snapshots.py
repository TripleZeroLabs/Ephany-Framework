"""
projects/management/commands/sync_project_snapshots.py

Imports all sheets from a Smartsheet folder as Django Project + Snapshot
records, then populates each Snapshot with AssetInstances.

The folder is identified by the SMARTSHEET_SNAPSHOTS_FOLDER_ID environment
variable (or --folder-id), and the project-name lookup sheet by
SMARTSHEET_LOOKUP_SHEET_ID (or --lookup-sheet-id).

Sheet naming convention (underscore-delimited):
    <prefix>_<job_id>_<YYYY-MM-DD>_<snapshot_name>

    segment[0]  — ignored prefix/category
    segment[1]  — job_id (normalised to JPS-XXXXX if not already prefixed)
    segment[2]  — snapshot date (YYYY-MM-DD)
    segment[3+] — snapshot name (remaining segments joined with '_')

Project names are resolved from a separate lookup sheet using
"Project ID" → "Smartsheet Project Name".

Each data row in a sheet contributes N AssetInstance records where N is the
value in the "Quantity" column (one record per unit).

Usage:
    export SMARTSHEET_SNAPSHOTS_FOLDER_ID=<your-folder-id>
    export SMARTSHEET_LOOKUP_SHEET_ID=<your-lookup-sheet-id>
    python manage.py sync_project_snapshots <SMARTSHEET_API_KEY> [--dry-run]

    # or, without the environment variables:
    python manage.py sync_project_snapshots <API_KEY> --folder-id <FOLDER_ID> --lookup-sheet-id <SHEET_ID>
"""

import requests
from datetime import date

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from assets.models import Asset
from projects.models import AssetInstance, Project, Snapshot

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SMARTSHEET_BASE = "https://api.smartsheet.com/2.0"

JPS_PREFIX = "JPS-"

# Column titles expected in project snapshot sheets
COL_ASSET_ID = "Asset ID"
COL_QUANTITY = "Quantity"

# Column titles in the lookup sheet
COL_PROJECT_ID = "Project ID"
COL_PROJECT_NAME = "Smartsheet Project Name"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _headers(api_key: str) -> dict:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def _get(url: str, api_key: str) -> dict:
    resp = requests.get(url, headers=_headers(api_key))
    resp.raise_for_status()
    return resp.json()


def _column_map(sheet: dict) -> dict:
    """Return {column_title: column_id} for a sheet response."""
    return {col["title"]: col["id"] for col in sheet.get("columns", [])}


def _cell_value(row: dict, col_map: dict, col_title: str):
    """Return the raw value of a cell by column title, or None."""
    col_id = col_map.get(col_title)
    if col_id is None:
        return None
    cells_by_col = {cell["columnId"]: cell for cell in row.get("cells", [])}
    return cells_by_col.get(col_id, {}).get("value")


def _normalize_job_id(raw: str) -> str:
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
        # 1. Load lookup sheet: job_id → project name
        # ------------------------------------------------------------------
        self.stdout.write("Loading project name lookup sheet…")
        try:
            lookup_sheet = _get(f"{SMARTSHEET_BASE}/sheets/{lookup_sheet_id}", api_key)
        except requests.HTTPError as exc:
            raise CommandError(f"Failed to fetch lookup sheet: {exc}") from exc

        lookup_col_map = _column_map(lookup_sheet)
        if COL_PROJECT_ID not in lookup_col_map or COL_PROJECT_NAME not in lookup_col_map:
            raise CommandError(
                f"Lookup sheet is missing required columns: "
                f'"{COL_PROJECT_ID}" and/or "{COL_PROJECT_NAME}"'
            )

        project_name_by_job_id: dict[str, str] = {}
        for row in lookup_sheet.get("rows", []):
            pid = _cell_value(row, lookup_col_map, COL_PROJECT_ID)
            pname = _cell_value(row, lookup_col_map, COL_PROJECT_NAME)
            if pid and pname:
                project_name_by_job_id[str(pid).strip()] = str(pname).strip()

        self.stdout.write(
            self.style.SUCCESS(f"  Loaded {len(project_name_by_job_id)} project name entries.\n")
        )

        # ------------------------------------------------------------------
        # 2. Fetch folder contents
        # ------------------------------------------------------------------
        self.stdout.write(f"Fetching folder {folder_id}…")
        try:
            folder = _get(f"{SMARTSHEET_BASE}/folders/{folder_id}", api_key)
        except requests.HTTPError as exc:
            raise CommandError(f"Failed to fetch folder: {exc}") from exc

        sheets = folder.get("sheets", [])
        if not sheets:
            self.stdout.write(self.style.WARNING("No sheets found in folder. Nothing to import."))
            return

        self.stdout.write(self.style.SUCCESS(f"  Found {len(sheets)} sheet(s).\n"))

        # ------------------------------------------------------------------
        # 3. Process each sheet
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
            # 3a. Parse sheet name
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
            # 3d. Create / overwrite Snapshot
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
                sheet_data = _get(f"{SMARTSHEET_BASE}/sheets/{sheet_id}", api_key)
            except requests.HTTPError as exc:
                self.stdout.write(
                    self.style.WARNING(f"  SKIP sheet data: HTTP error fetching sheet — {exc}")
                )
                total_warnings += 1
                continue

            col_map = _column_map(sheet_data)

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
            # 3f. Create AssetInstances
            # --------------------------------------------------------------
            sheet_instances = 0

            for row in sheet_data.get("rows", []):
                raw_asset_id = _cell_value(row, col_map, COL_ASSET_ID)
                raw_quantity = _cell_value(row, col_map, COL_QUANTITY)

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
