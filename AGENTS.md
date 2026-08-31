# AGENTS.md

Context for coding agents working in this repository. Humans may find it a
faster orientation than the README, which is written for people setting the
project up.

## What this is

A Django REST Framework backend for tracking a **standard kit of parts across a
portfolio of sites** — data centres, coworking floors, retail stores. Anywhere
the same catalog of assets is installed at many locations and someone needs to
know what is actually where.

It is API-only. There is no server-rendered UI beyond the Django admin.

## Getting oriented fast

```bash
pip install -r requirements.txt
cp .env.example .env          # set DJANGO_SECRET_KEY
python manage.py migrate
python manage.py seed_demo    # 15 sites, 20 assets, ~4000 instances
python manage.py runserver
```

Then read [`openapi.yaml`](openapi.yaml), or browse `/api/docs/`. The schema is
generated from the code and committed, so it is the authoritative description
of every endpoint — prefer it over reading serializers to work out response
shapes.

## Architecture

Four first-party apps, plus examples that are not part of the framework:

| App | Owns |
| --- | --- |
| `assets` | The catalog: what a thing *is*, independent of where it is installed |
| `projects` | The portfolio: sites, projects, snapshots, and installed instances |
| `access` | Authentication, API keys, permissions, deploy checks |
| `users` | User accounts and per-user unit preferences |
| `examples/` | Sample integrations and scripts. Nothing in the core depends on these. |

### The domain spine

```
Asset  (catalog definition, e.g. "42U Server Rack", type_id RK-4200)
  └── AssetComponent      assemblies: a rack ships with 2 PDUs and a fan tray
        │
Project (one site's fit-out)
  └── Snapshot            a point in time: design intent, procurement, as-built
        └── AssetInstance one physical occurrence of a catalog Asset
              └── AssetComponentInstance   optional components actually included
```

`assets/summary.py` aggregates across that spine: `GET /api/assets/{id}/summary/`
reports where one catalog asset is installed across the whole portfolio, with
replacement cost.

`Site` groups projects at the same physical location. An `AssetInstance` is one
unit — a row with `Quantity: 12` in a source spreadsheet becomes twelve
instances, because each can carry its own location, tag, and custom fields.

## Rules that are easy to break

These are enforced by tests. Breaking one usually fails CI rather than
misbehaving quietly, but knowing them saves a round trip.

**Regenerate the schema after touching any serializer, viewset, or route.**

```bash
python manage.py spectacular --file openapi.yaml --validate --fail-on-warn
```

`--fail-on-warn` is not optional politeness: it fails when an endpoint cannot be
described accurately, which is how the committed spec stays honest. CI checks
that `openapi.yaml` matches the code.

**Every paginated list must have a total order.** Model `Meta.ordering` must end
in a unique field, or pagination can repeat and skip rows while the count still
looks right. `assets/tests.py` walks the router and fails on any endpoint that
breaks this. Client-supplied `?ordering=` is handled by `StableOrderingFilter`
in `ephany_framework/filters.py`, which appends the primary key.

**`Asset.custom_fields` is validated against `AssetAttribute`.** Keys must be
defined there first, values must match the declared `data_type`, and choice
fields must use a defined `AssetAttributeChoice`. Adding an ad-hoc key raises
`ValidationError` in `Asset.clean()`.

**Unit conversion happens in the serializer layer**, not middleware — see
`UnitConverter` in `ephany_framework/utils.py`. Values are stored in base metric
(mm, kg, m²) and converted to the requesting user's preference on read and
write. Direct ORM writes bypass this, so seed and migrate in base metric. API
key requests have no user and therefore no preference: they read and write base
metric.

**Anything that aggregates across projects must pick one snapshot per project.**
A project holds several snapshots of the same physical installation, so summing
across all of them multiplies every unit by the snapshot count and returns a
wrong number in a correct-looking response. `assets/summary.py` takes the
newest per project and states that in `totals.basis`. `assets/test_summary.py`
pins it - that test is the only thing standing between this endpoint and a
plausible lie.

**Meta option changes need a migration.** `makemigrations` produces an
`AlterModelOptions` with no schema change, but Django will complain about
missing migrations without it.

## Authentication

One layer. `access/authentication.py` establishes identity; a single permission
class in `access/permissions.py` decides access. Three credentials, all
composable:

| Credential | Header | For |
| --- | --- | --- |
| API key | `X-API-Key: <key>` | Machine clients: plugins, CLIs, sync jobs |
| Auth token | `Authorization: Token <token>` | User-scoped clients |
| Session | cookie | Browser: admin and browsable API |

`API_ALLOW_ANONYMOUS` defaults to `DEBUG`, so local development is open and a
deployment with `DEBUG=False` is closed. 401 means no credential was sent, 403
means one was sent and rejected — keep that distinction if you touch this code.

Do not reintroduce an auth check in middleware. Splitting the decision across
two layers is what caused three separate bugs; `access/tests.py` pins the full
credential matrix.

## Commands

```bash
python manage.py test                    # full suite
python manage.py check                   # config sanity
python manage.py check --deploy          # pre-release checks, incl. access.W001
python manage.py seed_demo --flush       # reload demo data
python manage.py create_apikey "Name"    # mint an API key
```

## Conventions

- New sample integrations go in `examples/`, as their own directory with a
  README. Do not add to the core apps.
- Scripts in `examples/api_scripts/` must not be named `test_*.py` — Django's
  test runner would try to collect them.
- List endpoints are paginated: `{count, next, previous, results}`. Detail
  endpoints return a bare object.
- Secrets come from the environment via `.env`. Never commit a real key, and
  never put one in a `VITE_*` variable in the frontend repo — those are inlined
  into the browser bundle.

## Related

- Frontend: [Ephany-UI-React](https://github.com/TripleZeroLabs/Ephany-UI-React)
- [BIM integration and units](docs/bim-integration.md)
- [Contributing](CONTRIBUTING.md)
