# Contributing

Thanks for your interest. This project is early, so the most useful
contributions are usually small and concrete: a bug with a reproduction, a
missing test, a doc correction.

## Setting up

```bash
git clone https://github.com/TripleZeroLabs/Ephany-Framework.git
cd Ephany-Framework
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

`seed_demo` loads 15 sites across three verticals so there is something to look
at. `python manage.py seed_demo --flush` reloads it without touching records you
created yourself.

## Before opening a pull request

Three commands. All of them run in CI, so running them locally saves a round
trip:

```bash
python manage.py test
```

```bash
python manage.py check
```

```bash
python manage.py spectacular --file openapi.yaml --validate --fail-on-warn
```

That last one matters more than it looks. `openapi.yaml` is generated from the
code and committed, so it is what clients and coding agents read instead of your
serializers. **If you touch a serializer, viewset, or route, regenerate it and
commit the result.** CI fails if the committed spec does not match the code.

`--fail-on-warn` fails when an endpoint cannot be described accurately —
typically an untyped `SerializerMethodField` or an `@action` whose response
does not match its viewset's serializer. Fix it with `@extend_schema` rather
than suppressing the warning; the point is that the schema does not lie.

## Things worth knowing before you change them

[AGENTS.md](AGENTS.md) has the full list. The three that catch people:

- **Ordering.** Every paginated list needs an ordering that ends in a unique
  field, or pages can repeat and skip rows. A test walks the router and fails
  otherwise.
- **`custom_fields`.** Keys must exist in `AssetAttribute` and match its
  declared type. This is deliberate: it is what keeps a field meaning the same
  thing across an entire fleet.
- **Authentication is one layer.** `access/authentication.py` establishes
  identity, `access/permissions.py` decides access. Please do not add checks in
  middleware — the split is what caused the bugs `access/tests.py` now pins.

## Tests

Not everything is covered yet, so new tests are welcome on their own. Worth
knowing what the existing ones are for:

- `access/tests.py` — the credential matrix. Auth fails silently, so every
  combination is pinned rather than spot-checked.
- `assets/tests.py` — pagination stability, plus a structural test that fails
  when any new endpoint can return unstable pages.

## Style

Match the surrounding code. Comments should explain why something is the way it
is, not restate what the line does — a reader can see the code.

## Reporting bugs

Include what you ran, what happened, and what you expected. For API issues, the
request and the full response body help most. If it involves data, `seed_demo`
gives everyone the same starting point to reproduce against.
