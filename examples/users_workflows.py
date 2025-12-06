import requests
import json
from config import BASE_URL


# Helper to print nicely
def print_response(response, title):
    print(f"\n--- {title} ---")
    print(f"Status Code: {response.status_code}")
    try:
        # Try to parse JSON
        print(json.dumps(response.json(), indent=2))
    except json.JSONDecodeError:
        # If it's HTML, print a preview (first 500 chars) to see what's wrong
        print("Response was not JSON. Preview:")
        print(response.text[:500])

def run():
    # Standard headers to ensure we get JSON, not HTML
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    # 1. Create a New User
    print("\n[1] Creating a new user...")
    new_user_data = {
        "username": "architect_bob",
        "email": "bob@example.com",
        "password": "StrongPassword123!",
        "first_name": "Bob",
        "last_name": "Builder",
        "settings": {
            "length_unit": "ft"
        }
    }
    
    response = requests.post(f"{BASE_URL}/users/", json=new_user_data, headers=headers)
    print_response(response, "Create User Response")
    
    if response.status_code != 201:
        print("Failed to create user. Exiting.")
        return

    user_id = response.json()['id']
    username = response.json()['username']

    # Auth for subsequent requests
    auth = (username, "StrongPassword123!")

    # 2. Update User Settings
    print(f"\n[2] Updating settings for user {username}...")
    update_data = {
        "settings": {
            "length_unit": "mm"
        }
    }
    response = requests.patch(f"{BASE_URL}/users/{user_id}/", json=update_data, headers=headers, auth=auth)
    print_response(response, "Update Settings Response")

    # 3. List Users
    print("\n[3] Listing all users...")
    response = requests.get(f"{BASE_URL}/users/", headers=headers, auth=auth)
    print_response(response, "List Users Response")

if __name__ == "__main__":
    run()