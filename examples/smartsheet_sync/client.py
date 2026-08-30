"""
The Smartsheet-specific half of this example.

Everything that knows Smartsheet exists lives in this file: the base URL, the
auth header, and the awkward shape of a Smartsheet row. The two management
commands next door contain only mapping and write logic, which is the part
worth copying.

## Adapting this to a different source

To retarget the commands at Airtable, a Google Sheet, a CSV export, or an
internal REST API, you only need to reimplement the four functions below.
Keep the signatures and the commands will work unchanged:

    fetch(path, api_key)  -> dict     one HTTP GET, raises on error
    column_map(sheet)     -> dict     {column title: column id}
    cell_value(row, col_map, title)   one cell, by human-readable column name
    rows(sheet)           -> list     the data rows

The indirection through `column_map` exists because Smartsheet addresses cells
by numeric column ID, not by name. A CSV or Airtable adapter can make
`column_map` return `{title: title}` and have `cell_value` do a plain dict
lookup — the commands never inspect what a "column id" actually is.

Rate limiting, retries, and pagination are deliberately absent. Smartsheet
returns a whole sheet in one response, which keeps this example short. A real
importer against a paginated API would loop here, not in the commands.
"""

import requests

# Smartsheet API v2. Every request in this example is a plain GET against it.
SMARTSHEET_BASE = "https://api.smartsheet.com/2.0"


def headers(api_key: str) -> dict:
    """Auth headers for the Smartsheet API."""
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def fetch(path: str, api_key: str) -> dict:
    """
    GET one Smartsheet resource and return the decoded JSON.

    `path` is relative to SMARTSHEET_BASE, e.g. "sheets/123" or "folders/456".
    Raises requests.HTTPError on a non-2xx response; the commands catch that
    and re-raise it as a Django CommandError so the user sees a clean message
    instead of a traceback.
    """
    resp = requests.get(f"{SMARTSHEET_BASE}/{path}", headers=headers(api_key))
    resp.raise_for_status()
    return resp.json()


def column_map(sheet: dict) -> dict:
    """
    Return {column_title: column_id} for a sheet response.

    Smartsheet identifies cells by numeric column ID, but those IDs are
    meaningless to a reader and change between sheets. Building this map once
    per sheet lets the rest of the code address columns by their human-readable
    title, which is what the mapping dicts in the commands are keyed on.
    """
    return {col["title"]: col["id"] for col in sheet.get("columns", [])}


def cell_value(row: dict, col_map: dict, col_title: str):
    """
    Return the raw value of one cell by column title, or None.

    Returns None both when the column does not exist in the sheet and when the
    cell is empty. That is intentional: a missing column should degrade to
    "no value" rather than crash a long import halfway through. The commands
    warn about missing columns up front instead.
    """
    col_id = col_map.get(col_title)
    if col_id is None:
        return None
    cells_by_col = {cell["columnId"]: cell for cell in row.get("cells", [])}
    return cells_by_col.get(col_id, {}).get("value")


def rows(sheet: dict) -> list:
    """Return the data rows of a sheet response."""
    return sheet.get("rows", [])
