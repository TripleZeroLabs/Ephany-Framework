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
        self.user_id = None
        self.user_settings = {}

    def login(self):
        print("\n=== Ephany Asset Manager Login ===")
        username = input("Username: ")
        password = getpass.getpass("Password: ")
        self.auth = (username, password)

        # Verify and get User ID
        try:
            # We filter the list to find ourselves since we don't have /users/me yet
            resp = requests.get(f"{BASE_URL}/users/", auth=self.auth, headers=HEADERS)
            if resp.status_code == 200:
                users = resp.json()
                for u in users:
                    if u['username'] == username:
                        self.user_id = u['id']
                        # Fetch settings specifically if nested or separate
                        self.user_settings = u.get('settings', {})
                        break

                if self.user_id:
                    print(f"\n[SUCCESS] Welcome, {username}!")
                    self.print_user_context()
                    return True

            print(f"[ERROR] Login failed. Status: {resp.status_code}")
            return False

        except requests.exceptions.ConnectionError:
            print("[CRITICAL] Could not connect to API. Is the server running?")
            sys.exit(1)

    def print_user_context(self):
        length_unit = self.user_settings.get('length_unit', 'mm (default)')
        print(f" > Your Unit Preference: {length_unit}")
        print(" > Note: Ephany stores all data internally in METRIC (mm).")
        print(" > We will convert your inputs automatically based on your settings.\n")

    def find_asset(self):
        while True:
            unique_id = input("Enter Asset Unique ID to update (or 'q' to quit): ").strip()
            if unique_id.lower() == 'q':
                sys.exit(0)

            resp = requests.get(f"{BASE_URL}/assets/?unique_id__iexact={unique_id}", auth=self.auth)
            if resp.status_code == 200:
                results = resp.json()
                if results:
                    asset = results[0]
                    print(f"Found: {asset['manufacturer_name']} {asset['model']} (ID: {asset['unique_id']})")
                    return asset
                else:
                    print(f"[404] No asset found with ID '{unique_id}'. Try again.")
            else:
                print(f"[ERROR] API Error: {resp.status_code}")

    def update_field(self, asset):
        print(f"\n--- Update Custom Field for {asset['unique_id']} ---")
        print(f"Current Custom Fields: {json.dumps(asset.get('custom_fields', {}), indent=2)}")

        key = input("Enter Field Key (e.g., shelf_width): ").strip()
        val_str = input(f"Enter New Value for '{key}' (in {self.user_settings.get('length_unit', 'mm')}): ").strip()

        # Simple type inference for the demo
        try:
            val = float(val_str)
        except ValueError:
            val = val_str  # Keep as string if not a number

        patch_data = {
            "custom_fields": {
                key: val
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

            print("\n[SUCCESS] Update Complete!")
            print(f" > You Input:      {val} ({self.user_settings.get('length_unit')})")
            print(f" > API Returned:   {new_val} (Converted back to your preference)")

            # Rough math check for display purposes
            if self.user_settings.get('length_unit') == 'in' and isinstance(val, float):
                mm_val = val * 25.4
                print(f" > Database Store: {mm_val:.2f} mm (Approx)")
            elif self.user_settings.get('length_unit') == 'ft' and isinstance(val, float):
                mm_val = val * 304.8
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