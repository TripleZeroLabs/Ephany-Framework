# Example: API scripts

Four short Python files showing how to talk to the API from outside Django.
Read them in this order:

| File | What it shows |
| --- | --- |
| `check_connection.py` | Is the server reachable, and are the credentials right? Run this first. |
| `config.py` | Shared setup, and the pagination helper the others use |
| `assets_get.py` | Listing and searching across every page |
| `assets_search.py` | Django field lookups as query parameters |

They need only `requests`, which is already in `requirements.txt`.

## Running them

From this directory, with the server running:

```
python check_connection.py
```

```
python assets_get.py
python assets_get.py --search stainless
python assets_search.py PUMP-001
```

Point them somewhere else with environment variables, so you never have to edit
a file to switch servers:

```
EPHANY_BASE_URL=https://your-server/api EPHANY_API_KEY=abc123 python assets_get.py
```

## Credentials

On a fresh local install the API answers unauthenticated requests, so these run
with no setup. Once the server is deployed with `DJANGO_DEBUG=False`, they need
a key:

```
python manage.py create_apikey "Example Scripts"
```

Set it as `EPHANY_API_KEY`, or edit `API_KEY` in `config.py`.

API keys are the right credential *here* — a script runs on a machine you
control and can keep a secret. They are the wrong credential for a browser app,
where anything the page can send, a visitor can read.

`check_connection.py` tells the failure modes apart, because they look
identical from the outside:

| Result | Meaning |
| --- | --- |
| `[UNREACHABLE]` | Nothing is listening. Wrong URL, or the server is down. |
| `[NO CREDENTIAL]` (401) | Server is up and wants authentication. |
| `[BAD CREDENTIAL]` (403) | A key was sent and rejected — mistyped or deactivated. |
| `[OK]` | Connected. |

## The thing most worth copying: pagination

List endpoints return one page at a time, wrapped in an envelope:

```json
{"count": 143, "next": "http://.../assets/?page=2", "previous": null, "results": [...]}
```

So this, the obvious thing to write, does not work:

```python
for asset in requests.get(f"{BASE_URL}/assets/").json():
    print(asset["type_id"])          # TypeError: string indices must be integers
```

It iterates the four keys of the envelope, not your data. Read `results`, and
follow `next` until it comes back null — which is what `config.get_all()` does:

```python
import config
for asset in config.get_all("/assets/"):
    print(asset["type_id"], asset["name"])
```

Detail endpoints like `/assets/1/` return a bare object with no envelope.

## Filtering

Any Django field lookup works as a query parameter:

```
/api/assets/?manufacturer__name__icontains=sony
/api/assets/?type_id__iexact=pump-001
/api/assets/?description__icontains=stainless
```

`/api/docs/` lists what each endpoint accepts, generated from the code itself,
so it cannot drift out of date the way a hand-written table would.
