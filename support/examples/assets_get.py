#!/usr/bin/env python3
"""
Simple API Demo: Get Assets

Two basic functions demonstrating the Ephany Framework API:
1. Get all assets
2. Search assets by keyword in description

Usage:
    python assets_get.py                     # Get all assets
    python assets_get.py --search stainless  # Search by description keyword
"""

import argparse
import requests
from config import BASE_URL, API_KEY

# Reusable headers for all API calls
HEADERS = {
    "X-API-Key": API_KEY
}


def get_all_assets():
    """Fetch all assets from the API."""
    url = f"{BASE_URL}/assets/"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()  # surface 401 or 403 immediately
    return response.json()


def search_assets_by_description(keyword):
    """Search for assets where description contains the keyword."""
    url = f"{BASE_URL}/assets/"
    params = {"description__icontains": keyword}
    response = requests.get(url, params=params, headers=HEADERS)
    response.raise_for_status()
    return response.json()


def main():
    parser = argparse.ArgumentParser(description="Get or search assets via the API.")
    parser.add_argument("--search", "-s", type=str, help="Search keyword for description")

    args = parser.parse_args()

    try:
        if args.search:
            print(f"Assets with '{args.search}' in description:")
            assets = search_assets_by_description(args.search)
        else:
            print("All Assets:")
            assets = get_all_assets()

        if assets:
            for asset in assets:
                # Adjust dict keys depending on your API output
                print(f"  - {asset['type_id']}: {asset['name']}")
        else:
            print("  No assets found.")

    except requests.exceptions.HTTPError as e:
        print(f"API error: {e}")
        print("Check that your API_KEY in config.py is correct.")
    except Exception as e:
        print(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()
