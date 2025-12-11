import requests
import json
import getpass
import sys
from config import BASE_URL

# Configuration
HEADERS = {"Content-Type": "application/json"}


class EphanyCLI:
    def __init__(self):
        self.auth = None

    def login(self):
        print("\n=== Ephany Asset Manager Login ===")
        username = input("Username: ")
        password = getpass.getpass("Password: ")
        self.auth = (username, password)
        return True

    def find_asset(self):
        while True:
            type_id = input("Enter Asset Unique ID to update (or 'q' to quit): ").strip()
            if type_id.lower() == 'q':
                sys.exit(0)

            resp = requests.get(f"{BASE_URL}/assets/?type_id__iexact={type_id}", auth=self.auth)
            if resp.status_code == 200:
                results = resp.json()
                if results:
                    asset = results[0]
                    print(f"Found: {asset['manufacturer_name']} {asset['model']} (ID: {asset['type_id']})")
                    return asset
                else:
                    print(f"[404] No asset found with ID '{type_id}'. Try again.")
            else:
                print(f"[ERROR] API Error: {resp.status_code}")

    def update_field(self, asset):
        print(f"\n--- Update Custom Field for {asset['type_id']} ---")
        print(f"Current Custom Fields: {json.dumps(asset.get('custom_fields', {}), indent=2)}")

        key = input("Enter Field Key (e.g., shelf_width): ").strip()
        unit = input("Enter Unit (e.g., mm, in, ft): ").strip()
        val_str = input(f"Enter New Value for '{key}' (in {unit}): ").strip()

        # Simple type inference for the demo
        try:
            val = round(float(val_str), 2)
        except ValueError:
            val = val_str  # Keep as string if not a number

        patch_data = {
            "custom_fields": {
                key: val
            },
            "input_units": {
                "length": unit
            }
        }

        print("\nSending Update...")
        resp = requests.patch(
            f"{BASE_URL}/assets/{asset['id']}/",
            json=patch_data,
            auth=self.auth,
            headers=HEADERS
        )

        if resp.status_code == 200:
            updated_asset = resp.json()
            new_val = updated_asset['custom_fields'].get(key)
            display_unit = updated_asset.get('_display_units', {}).get('length', 'unknown')

            print("\n[SUCCESS] Update Complete!")
            print(f" > You Input:      {val} ({unit})")
            print(f" > API Returned:   {new_val} ({display_unit})")

            # Rough math check for display purposes
            if isinstance(val, (int, float)):
                mm_val = val
                if unit == 'in':
                    mm_val = val * 25.4
                elif unit == 'ft':
                    mm_val = val * 304.8
                elif unit == 'cm':
                    mm_val = val * 10.0

                print(f" > Database Store: {mm_val:.2f} mm (Approx)")

        else:
            print(f"[FAIL] Update failed: {resp.text}")


def run():
    app = EphanyCLI()
    if app.login():
        while True:
            asset = app.find_asset()
            app.update_field(asset)
            print("\n" + "-" * 40 + "\n")


if __name__ == "__main__":
    run()