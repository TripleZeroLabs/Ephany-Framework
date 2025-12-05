import requests
import json
from config import BASE_URL, HEADERS


def get_assets():
    """Fetch and print all assets."""
    print("--- Fetching Assets ---")
    response = requests.get(f"{BASE_URL}/assets/")

    if response.status_code == 200:
        assets = response.json()
        print(json.dumps(assets, indent=2))
    else:
        print(f"Error: {response.status_code}")
        print(response.text)


def create_manufacturer(name):
    """Create a new manufacturer."""
    print(f"\n--- Creating Manufacturer: {name} ---")
    payload = {"name": name}
    response = requests.post(f"{BASE_URL}/manufacturers/", json=payload, headers=HEADERS)

    if response.status_code == 201:
        print("Success!")
        return response.json()
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        return None


if __name__ == "__main__":
    # make sure the server is running!
    try:
        get_assets()
        # new_man = create_manufacturer("Example Corp")
    except requests.exceptions.ConnectionError:
        print("Could not connect to server. Is it running on port 8000?")