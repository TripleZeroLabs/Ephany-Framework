"""
projects/management/commands/sync_projects_from_smartsheet.py

One-way sync from a Smartsheet sheet → Django Project records.
Looks up each row by "Project ID" and updates the matching Project in Django.

The sheet is identified by the SMARTSHEET_PROJECTS_SHEET_ID environment
variable, or by the --sheet-id flag. The column titles below are the ones this
command expects; edit the mapping dicts to match your own sheet.

Only updates fields that have changed. Skips rows with no matching Project.
Creates Site records on-the-fly if a Site ID is encountered that doesn't exist yet.

Column → Django field mapping:
    Project ID                              → job_id  (lookup key)
    Smartsheet Project Name                 → name
    Site ID                                 → site    (FK via Site.site_id)
    Overall Status                          → status  (Blue/Red/Yellow/Green → blue/red/yellow/green)
    Store Go Live                           → go_live_date
    Street                                  → address_line1
    Address 2: Location in Building / Venue → address_line2
    City                                    → city
    State/Province                          → state
    Zip/Postal Code                         → zip_code
    Country/Territory                       → country

    Written to custom_fields{}:
    FCID                                    → custom_fields['fc_id']
    RI Model                                → custom_fields['ri_model']
    Vision Only %                           → custom_fields['vo_percentage']  (whole number)
    Trackable Area                          → custom_fields['trackable_area_planned']
    Vertical                                → custom_fields['vertical']

Usage:
    export SMARTSHEET_PROJECTS_SHEET_ID=<your-sheet-id>
    python manage.py sync_projects_from_smartsheet <SMARTSHEET_API_KEY> [--dry-run]

    # or, without the environment variable:
    python manage.py sync_projects_from_smartsheet <API_KEY> --sheet-id <SHEET_ID>
"""

import requests
from datetime import date, datetime

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from projects.models import Project, Site

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SMARTSHEET_BASE = "https://api.smartsheet.com/2.0"

# Smartsheet column title → Django Project direct field name
DIRECT_FIELDS = {
    "Smartsheet Project Name":                 "name",
    "Street":                                  "address_line1",
    "Address 2: Location in Building / Venue": "address_line2",
    "City":                                    "city",
    "State/Province":                          "state",
    "Zip/Postal Code":                         "zip_code",
    "Country/Territory":                       "country",
}

# Smartsheet column title → custom_fields key (string values, stored as-is)
CUSTOM_STRING_FIELDS = {
    "FCID":     "fc_id",
    "Vertical": "vertical",
}

# Overall Status display value → Django choices key
STATUS_MAP = {
    "blue":   "blue",
    "red":    "red",
    "yellow": "yellow",
    "green":  "green",
}

# RI Model display value → stored key in custom_fields
RI_MODEL_MAP = {
    "App, Fully Delegated":                  "app_delegated",
    "CCE, Fully Delegated":                  "cce_delegated",
    "CCE, Fully Integrated":                 "cce_integrated",
    "CCE, Order Delegated":                  "cce_order_delegated",
    "CCE, Partially Delegated":              "cce_partial",
    "Combo (App + CCE, Fully Integrated)":   "combo_cce",
    "Combo (APP + Ordering By Amazon)":      "combo_ordering",
    "Custom - Requires SA Support":          "custom_sa",
    "Ordering by Amazon: CA":                "oba_ca",
    "Ordering by Amazon: UK":                "oba_uk",
    "Ordering by Amazon: US":                "oba_us",
    "Ordering by Amazon: AU":                "oba_au",
}


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
    """Return the raw cell value by column title, or None."""
    col_id = col_map.get(col_title)
    if col_id is None:
        return None
    cells_by_col = {cell["columnId"]: cell for cell in row.get("cells", [])}
    return cells_by_col.get(col_id, {}).get("value")


def _str(value) -> str:
    """Coerce a cell value to a stripped string, or empty string."""
    if value is None:
        return ""
    return str(value).strip()


def _parse_date(value) -> date | None:
    """Parse a Smartsheet date cell to a Python date, or None."""
    if value is None:
        return None
    if isinstance(value, (date, datetime)):
        return value.date() if isinstance(value, datetime) else value
    raw = str(value).strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------

class Command(BaseCommand):
    help = (
        "Sync Project fields from a Smartsheet sheet into Django. "
        "Looks up each row by Project ID and updates the matching Project record. "
        "Set SMARTSHEET_PROJECTS_SHEET_ID or pass --sheet-id."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "api_key",
            type=str,
            help="Smartsheet API Bearer token",
        )
        parser.add_argument(
            "--sheet-id",
            type=str,
            default=None,
            help=(
                "Smartsheet sheet ID to read from. "
                "Defaults to the SMARTSHEET_PROJECTS_SHEET_ID environment variable."
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

        sheet_id: str = options["sheet_id"] or settings.SMARTSHEET_PROJECTS_SHEET_ID
        if not sheet_id:
            raise CommandError(
                "No Smartsheet sheet ID configured. Set SMARTSHEET_PROJECTS_SHEET_ID "
                "in your .env file, or pass --sheet-id <SHEET_ID>."
            )

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no database changes will be made.\n"))

        # ------------------------------------------------------------------
        # Fetch sheet
        # ------------------------------------------------------------------
        self.stdout.write(f"Fetching sheet {sheet_id}…")
        try:
            sheet = _get(f"{SMARTSHEET_BASE}/sheets/{sheet_id}", api_key)
        except requests.HTTPError as exc:
            raise CommandError(f"Failed to fetch sheet: {exc}") from exc

        col_map = _column_map(sheet)
        rows = sheet.get("rows", [])
        self.stdout.write(self.style.SUCCESS(f"  {len(rows)} row(s) found.\n"))

        # Warn about any expected columns that are missing
        expected_cols = (
            {"Project ID", "Site ID", "Overall Status", "RI Model",
             "Store Go Live", "Vision Only %", "Trackable Area"}
            | set(DIRECT_FIELDS.keys())
            | set(CUSTOM_STRING_FIELDS.keys())
        )
        missing_cols = expected_cols - set(col_map.keys())
        if missing_cols:
            self.stdout.write(
                self.style.WARNING(f"  WARNING: columns not found in sheet: {sorted(missing_cols)}\n")
            )

        # ------------------------------------------------------------------
        # Process rows
        # ------------------------------------------------------------------
        updated = 0
        skipped_no_project = 0
        skipped_no_id = 0
        warnings = 0

        for row in rows:
            raw_job_id = _cell_value(row, col_map, "Project ID")
            if not raw_job_id:
                skipped_no_id += 1
                continue

            job_id = str(raw_job_id).strip()

            try:
                project = Project.objects.select_related("site").get(job_id=job_id)
            except Project.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f"  SKIP: no Project with job_id='{job_id}'")
                )
                skipped_no_project += 1
                warnings += 1
                continue

            direct_changes: dict = {}
            custom_changes: dict = {}
            current_cf = project.custom_fields or {}

            # ---- Direct string fields ------------------------------------
            for col_title, field_name in DIRECT_FIELDS.items():
                new_val = _str(_cell_value(row, col_map, col_title))
                if new_val != getattr(project, field_name, ""):
                    direct_changes[field_name] = new_val

            # ---- Custom string fields ------------------------------------
            for col_title, cf_key in CUSTOM_STRING_FIELDS.items():
                new_val = _str(_cell_value(row, col_map, col_title))
                current_val = current_cf.get(cf_key, "")
                if new_val != current_val:
                    custom_changes[cf_key] = new_val

            # ---- Site (FK) -----------------------------------------------
            raw_site_id = _str(_cell_value(row, col_map, "Site ID"))
            if raw_site_id:
                current_site_id = project.site.site_id if project.site else None
                if raw_site_id != current_site_id:
                    if not dry_run:
                        site, site_created = Site.objects.get_or_create(site_id=raw_site_id)
                        if site_created:
                            self.stdout.write(f"  [+] Created Site: {raw_site_id}")
                    direct_changes["_site_id_value"] = raw_site_id  # internal tracking
            elif project.site is not None:
                direct_changes["site"] = None

            # ---- Overall Status ------------------------------------------
            raw_status = _str(_cell_value(row, col_map, "Overall Status"))
            if raw_status:
                mapped_status = STATUS_MAP.get(raw_status.lower())
                if mapped_status is None:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  WARNING: unknown status '{raw_status}' for '{job_id}' — skipping field"
                        )
                    )
                    warnings += 1
                elif mapped_status != project.status:
                    direct_changes["status"] = mapped_status
            elif project.status:
                direct_changes["status"] = ""

            # ---- RI Model → custom_fields['ri_model'] --------------------
            raw_ri = _str(_cell_value(row, col_map, "RI Model"))
            if raw_ri:
                mapped_ri = RI_MODEL_MAP.get(raw_ri)
                if mapped_ri is None:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  WARNING: unknown RI Model '{raw_ri}' for '{job_id}' — skipping field"
                        )
                    )
                    warnings += 1
                elif mapped_ri != current_cf.get("ri_model", ""):
                    custom_changes["ri_model"] = mapped_ri
            elif current_cf.get("ri_model"):
                custom_changes["ri_model"] = ""

            # ---- Store Go Live -------------------------------------------
            raw_date = _cell_value(row, col_map, "Store Go Live")
            parsed_date = _parse_date(raw_date)
            if parsed_date != project.go_live_date:
                direct_changes["go_live_date"] = parsed_date

            # ---- Vision Only % → custom_fields['vo_percentage'] ----------
            raw_vo = _cell_value(row, col_map, "Vision Only %")
            if raw_vo is not None:
                try:
                    vo_int = int(float(raw_vo))
                    if vo_int != current_cf.get("vo_percentage"):
                        custom_changes["vo_percentage"] = vo_int
                except (ValueError, TypeError):
                    self.stdout.write(
                        self.style.WARNING(
                            f"  WARNING: invalid Vision Only % '{raw_vo}' for '{job_id}' — skipping field"
                        )
                    )
                    warnings += 1
            elif current_cf.get("vo_percentage") is not None:
                custom_changes["vo_percentage"] = None

            # ---- Trackable Area → custom_fields['trackable_area_planned'] -
            raw_area = _cell_value(row, col_map, "Trackable Area")
            if raw_area is not None:
                try:
                    area_val = float(raw_area)
                    if area_val != current_cf.get("trackable_area_planned"):
                        custom_changes["trackable_area_planned"] = area_val
                except (ValueError, TypeError):
                    self.stdout.write(
                        self.style.WARNING(
                            f"  WARNING: invalid Trackable Area '{raw_area}' for '{job_id}' — skipping field"
                        )
                    )
                    warnings += 1
            elif current_cf.get("trackable_area_planned") is not None:
                custom_changes["trackable_area_planned"] = None

            # ---- Apply changes -------------------------------------------
            if not direct_changes and not custom_changes:
                continue

            # Extract internal tracking key before display/apply
            site_id_value = direct_changes.pop("_site_id_value", None)

            display = {}
            if site_id_value:
                display["site"] = site_id_value
            display.update({k: v for k, v in direct_changes.items()})
            if custom_changes:
                display["custom_fields"] = custom_changes

            self.stdout.write(f"  [{'DRY' if dry_run else '~'}] {job_id}: {display}")

            if not dry_run:
                update_fields = []

                # Apply direct field changes
                for field, value in direct_changes.items():
                    setattr(project, field, value)
                    update_fields.append(field)

                # Resolve site FK
                if site_id_value:
                    site, _ = Site.objects.get_or_create(site_id=site_id_value)
                    project.site = site
                    update_fields.append("site")

                # Merge custom_fields changes
                if custom_changes:
                    merged_cf = dict(current_cf)
                    merged_cf.update(custom_changes)
                    # Remove keys that were explicitly cleared (set to None or "")
                    merged_cf = {k: v for k, v in merged_cf.items() if v not in (None, "")}
                    project.custom_fields = merged_cf
                    update_fields.append("custom_fields")

                project.save(update_fields=update_fields + ["updated_at"])
                updated += 1
            else:
                updated += 1  # count intended updates in dry-run

        # ------------------------------------------------------------------
        # Summary
        # ------------------------------------------------------------------
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("Sync complete."))
        self.stdout.write(f"  Projects updated      : {updated}")
        self.stdout.write(f"  Skipped (no match)    : {skipped_no_project}")
        self.stdout.write(f"  Skipped (no job_id)   : {skipped_no_id}")
        if warnings:
            self.stdout.write(self.style.WARNING(f"  Warnings              : {warnings}"))
        if dry_run:
            self.stdout.write(self.style.WARNING("\nDRY RUN — no changes were written."))
