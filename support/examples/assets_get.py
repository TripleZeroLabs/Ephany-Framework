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
from config import BASE_URL


def get_all_assets():
    """Fetch all assets from the API."""
    response = requests.get(f"{BASE_URL}/assets/")
    return response.json()


def search_assets_by_description(keyword):
    """Search for assets where description contains the keyword."""
    params = {'description__icontains': keyword}
    response = requests.get(f"{BASE_URL}/assets/", params=params)
    return response.json()


def main():
    parser = argparse.ArgumentParser(description="Get or search assets via the API.")
    parser.add_argument('--search', '-s', type=str, help='Search keyword for description')

    args = parser.parse_args()

    if args.search:
        print(f"Assets with '{args.search}' in description:")
        assets = search_assets_by_description(args.search)
    else:
        print("All Assets:")
        assets = get_all_assets()

    if assets:
        for asset in assets:
            print(f"  - {asset['unique_id']}: {asset['name']}")
    else:
        print("  No assets found.")


if __name__ == "__main__":
    main()