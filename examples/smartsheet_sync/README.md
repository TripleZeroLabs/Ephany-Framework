# Example: Smartsheet Sync

Two management commands that pull a fleet of projects, and the assets installed
at each one, out of Smartsheet and into this framework.

They are here as a **worked example**. Smartsheet is incidental — the shape of
the code is the point, and it transfers to Airtable, a Google Sheet, a nightly
CSV drop, or an internal REST API.

## Files

| File | Role |
| --- | --- |
| `client.py` | The only Smartsheet-specific code. Replace this to target another system. |
| `management/commands/sync_projects_from_smartsheet.py` | The simple case: one sheet, one row per project, update-only. |
| `management/commands/sync_project_snapshots.py` | The hard case: a folder of sheets, metadata in filenames, destructive rebuild. |

The split matters. `client.py` knows about auth headers, base URLs, and the
fact that Smartsheet addresses cells by numeric column ID. The commands know
about Django models and mapping rules, and never touch an HTTP library. Keep
that seam and swapping sources is a one-file job.

## Retargeting these at a different source

Reimplement the four functions in `client.py`, keeping their signatures:

```python
fetch(path, api_key)              # one GET, decoded, raises on error
column_map(sheet)                 # {column title: column id}
cell_value(row, col_map, title)   # one cell, by human-readable name
rows(sheet)                       # the data rows
```

`column_map` exists because Smartsheet cells are keyed by numeric ID. For a CSV
or an API that returns plain dicts, return `{title: title}` and have
`cell_value` do a normal lookup — the commands never inspect what a "column id"
is.

Then rewrite the mapping dicts under the `STEP 1` banner in each command. That
is usually the whole job.

## What each command does

**`sync_projects_from_smartsheet`** — reads one sheet, matches each row to an
existing `Project` by `job_id`, and updates only the fields that differ.
Creates `Site` records on demand. Never creates Projects: an unmatched row is a
warning, so a typo upstream cannot invent a project.

**`sync_project_snapshots`** — walks a folder of sheets, one per snapshot.
Parses the job ID, date, and snapshot name out of each sheet's filename, then
expands each row into `Quantity` separate `AssetInstance` records. Creates
Projects and Snapshots as needed, and resolves project names from a second
lookup sheet loaded once up front.

> **This one is destructive.** Re-importing an existing snapshot deletes its
> `AssetInstance` records and rebuilds them from the sheet, so the snapshot
> always mirrors its source exactly. Run with `--dry-run` first, and check the
> folder ID before you check anything else.

## Configuration

Set these in `.env` (see [`.env.example`](../../.env.example)):

| Variable | Used by |
| --- | --- |
| `SMARTSHEET_PROJECTS_SHEET_ID` | `sync_projects_from_smartsheet` |
| `SMARTSHEET_SNAPSHOTS_FOLDER_ID` | `sync_project_snapshots` |
| `SMARTSHEET_LOOKUP_SHEET_ID` | `sync_project_snapshots` (defaults to the projects sheet) |

Each is overridable per-run with `--sheet-id`, `--folder-id`, and
`--lookup-sheet-id`. With none of them set, the command exits with a message
naming what it needs rather than making a doomed API call.

The API key is passed as a positional argument, not read from the environment,
so it never lands in a committed `.env`. It will appear in your shell history —
use your shell's leading-space convention if that matters to you.

## Usage

```bash
python manage.py sync_projects_from_smartsheet <API_KEY> --dry-run
```

```bash
python manage.py sync_project_snapshots <API_KEY> --dry-run
```

Drop `--dry-run` to write. Both print a summary of what changed, what was
skipped, and how many warnings were raised — including on a clean run, so you
can tell "nothing to do" from "matched nothing at all".

## Removing this example

Delete `'examples.smartsheet_sync'` from `INSTALLED_APPS` in
`ephany_framework/settings/base.py`. The commands disappear. Nothing else in
the framework references this package.
