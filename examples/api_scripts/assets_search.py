#!/usr/bin/env python3
"""
Look up a single asset by its Type ID.

Usage:
    python assets_search.py PUMP-001

Shows how Django field lookups map onto query parameters. `type_id__iexact`
matches case-insensitively; swap in `__icontains` for a partial match, or
`__in` for several at once. The same pattern works on any filterable field.
"""

import argparse
import json

import requests

import config


def find_by_type_id(type_id):
    """Return assets whose type_id matches, ignoring case."""
    return config.get_all("/assets/", {"type_id__iexact": type_id})


def main():
    parser = argparse.ArgumentParser(description="Find an asset by its Type ID.")
    parser.add_argument("type_id", help="Type ID to look up, e.g. PUMP-001")
    parser.add_argument("--json", action="store_true", help="Print the full records")
    args = parser.parse_args()

    try:
        matches = find_by_type_id(args.type_id)
    except requests.HTTPError as error:
        print(config.explain_http_error(error))
        return 1
    except requests.ConnectionError:
        print(f"Could not reach {config.BASE_URL}. Is the server running?")
        return 1

    if not matches:
        # type_id is unique, so this means it does not exist rather than
        # that the search was too narrow.
        print(f"No asset with type_id '{args.type_id}'.")
        return 1

    print(f"Found {len(matches)}:")
    if args.json:
        print(json.dumps(matches, indent=2))
    else:
        for asset in matches:
            print(f"  {asset['type_id']:<16} {asset['name']}")
            print(f"  {'':<16} {asset.get('manufacturer_name', '')} {asset.get('model', '')}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
