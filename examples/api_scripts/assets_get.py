#!/usr/bin/env python3
"""
List assets, or search them by a keyword in the description.

Usage:
    python assets_get.py                     # every asset
    python assets_get.py --search stainless  # description contains "stainless"
    python assets_get.py --limit 10          # stop after 10

The point of this one is pagination. /api/assets/ returns a page at a time
wrapped in a {count, next, previous, results} envelope, so a naive
`for asset in response.json()` iterates those four keys instead of your data.
config.get_all() follows `next` and returns the rows.
"""

import argparse

import requests

import config


def main():
    parser = argparse.ArgumentParser(description="List or search assets.")
    parser.add_argument("--search", "-s", help="Keyword to look for in the description")
    parser.add_argument("--limit", "-n", type=int, help="Stop after this many results")
    args = parser.parse_args()

    # Any Django field lookup works as a query parameter. See the filters on
    # AssetViewSet, or /api/docs/ for the full list.
    params = {"description__icontains": args.search} if args.search else None

    try:
        assets = config.get_all("/assets/", params)
    except requests.HTTPError as error:
        print(config.explain_http_error(error))
        return 1
    except requests.ConnectionError:
        print(f"Could not reach {config.BASE_URL}. Is the server running?")
        return 1

    if args.search:
        print(f"Assets matching '{args.search}': {len(assets)}")
    else:
        print(f"All assets: {len(assets)}")

    for asset in assets[: args.limit]:
        print(f"  {asset['type_id']:<16} {asset['name']}")

    if args.limit and len(assets) > args.limit:
        print(f"  ... and {len(assets) - args.limit} more")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
