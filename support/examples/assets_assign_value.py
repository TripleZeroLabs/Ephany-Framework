#!/usr/bin/env python3
"""
Demo: Bulk assign category to assets by manufacturer.

Sets category=1 for all assets where manufacturer=3.
"""

import requests
from config import BASE_URL

MANUFACTURER_PK = 3
CATEGORY_PK = 1


def main():
    # Get all assets for this manufacturer
    response = requests.get(f"{BASE_URL}/assets/", params={"manufacturer": MANUFACTURER_PK})
    assets = response.json()

    print(f"Found {len(assets)} assets for manufacturer {MANUFACTURER_PK}")

    # Update each asset
    updated = 0
    for asset in assets:
        resp = requests.patch(
            f"{BASE_URL}/assets/{asset['id']}/",
            json={"category": CATEGORY_PK}
        )
        if resp.status_code == 200:
            print(f"[OK] {asset['unique_id']}")
            updated += 1
        else:
            print(f"[FAIL] {asset['unique_id']} - {resp.status_code}")

    print(f"\nUpdated {updated}/{len(assets)} assets")


if __name__ == "__main__":
    main()