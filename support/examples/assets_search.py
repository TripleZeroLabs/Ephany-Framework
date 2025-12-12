import requests
import json
from config import BASE_URL, API_KEY

# Reusable headers for all API calls
HEADERS = {
    "X-API-Key": API_KEY
}


def search_by_type_id(type_id):
    """Search for an asset specifically by its type_id (case-insensitive)."""
    print(f"\n--- Searching for Unique ID: {type_id} ---")

    params = {"type_id__iexact": type_id}
    url = f"{BASE_URL}/assets/"

    try:
        response = requests.get(url, params=params, headers=HEADERS)
        response.raise_for_status()  # handles 401/403 cleanly

        results = response.json()
        if results:
            print(f"Found {len(results)} asset(s):")
            print(json.dumps(results, indent=2))
        else:
            print("No assets found with that ID.")

    except requests.exceptions.HTTPError as e:
        print(f"API error: {e}")
        print("Check your API_KEY in config.py.")
        print(f"\nResponse body:\n{response.text}")

    except Exception as e:
        print(f"Unexpected error: {e}")
