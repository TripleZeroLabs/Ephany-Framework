# Examples

Working code you can read, copy, and point at your own systems. Nothing here is
imported by `assets`, `projects`, `access`, or `users` — delete this whole
directory and the framework still runs.

| Example | What it demonstrates |
| --- | --- |
| [`api_scripts/`](api_scripts/) | Talking to the API from a standalone Python script: pagination, filtering, credentials |
| [`smartsheet_sync/`](smartsheet_sync/) | Importing a portfolio of projects and their asset snapshots from an external system of record |

Start with `api_scripts/` if you are new here — `check_connection.py` is the
shortest path to knowing your setup works.

## Why one of these ships enabled

`api_scripts/` is just files — run them directly, nothing to install.

`smartsheet_sync/` is a Django app listed in `INSTALLED_APPS`. That is the only way
its management commands show up in `python manage.py help`, which is where
people actually discover them. They add no models, no migrations, and no
routes — an example app costs you a line of config and nothing at runtime.

To remove one, delete its line from `INSTALLED_APPS` in
`ephany_framework/settings/base.py`. The commands disappear; nothing else
changes.

## Writing your own importer

The recurring problem this framework has to solve: some other system already
knows things about your portfolio — which sites exist, what got installed where,
which projects go live when — and you need that reflected here without hand
typing it.

Both Smartsheet commands follow the same four steps, and they are marked with
`STEP` banners in the source so you can find them:

1. **Declare the mapping.** Which source column feeds which Django field, as
   data rather than a wall of if-statements. This is the part you rewrite.
2. **Fetch the source data.** Isolated in `client.py`, so retargeting the
   importer at a different system means replacing one module.
3. **Diff each row.** Compare incoming values against what is stored, and
   collect only what actually differs.
4. **Write only what changed.** With `update_fields` on the save, and a
   `--dry-run` flag that exercises every step except the write.

Read [`sync_projects_from_smartsheet.py`](smartsheet_sync/management/commands/sync_projects_from_smartsheet.py)
first — it is the simple case. Then
[`sync_project_snapshots.py`](smartsheet_sync/management/commands/sync_project_snapshots.py),
which adds partial failure across many sources, metadata parsed out of
filenames, and a destructive rebuild.

### Three decisions to make before you write one

**Which side owns the truth?** The two commands answer this differently on
purpose. `sync_projects_from_smartsheet` refuses to create Projects — an
unmatched row is a logged warning, so a typo upstream cannot invent a project.
`sync_project_snapshots` creates them freely, because there the sheets *are*
the record of which snapshots exist. Decide this first; it determines whether
an unmatched row is an error or an insert.

**What should one bad row cost you?** These commands warn and continue.
Against human-maintained data that is almost always right: you want every
problem surfaced in one run, not a crash at the first bad cell and a blind
re-run. Configuration errors are the exception — a missing sheet ID or lookup
column fails immediately, because nothing downstream can succeed anyway.

**Is a re-run safe?** `sync_project_snapshots` deletes and rebuilds a
snapshot's instances, so pointing it at the wrong folder destroys good data.
That is a real cost, accepted deliberately so a snapshot always mirrors its
source exactly. If you make the same trade, say so loudly in the docstring and
make `--dry-run` genuinely useful.

## Running the Smartsheet examples

They need a Smartsheet account and your own sheet IDs — see the Smartsheet
variables in [`.env.example`](../.env.example). Dry-run first:

```bash
python manage.py sync_projects_from_smartsheet <API_KEY> --dry-run
```

Without configuration, each command exits with a message naming the
environment variable it needs. It will not make a doomed API call.
