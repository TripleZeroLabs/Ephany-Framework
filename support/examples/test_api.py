import requests
import json
from config import BASE_URL, API_KEY

# Reusable headers for all API calls
HEADERS = {
    "X-API-Key": API_KEY
}


def check_connection():
    """
    Simple health check to see if the API is reachable.
    We ping the API root endpoint WITH the required API key.
    """
    print(f"Connecting to {BASE_URL}...")

    try:
        response = requests.get(BASE_URL, headers=HEADERS, timeout=5)

        if response.status_code == 200:
            print(f"\n[SUCCESS] Connected to API!")
            print(f"Status: {response.status_code} OK")
            print("Server is online and responding.")

        elif response.status_code in (401, 403):
            print(f"\n[AUTH ERROR] {response.status_code}")
            print("The server is reachable, but authentication failed.")
            print("Double-check your API_KEY value in config.py.")
            print(f"\nServer response:\n{response.text}")

        else:
            print(f"\n[WARNING] Server responded with status code: {response.status_code}")
            print("Response content:")
            print(response.text)

    except requests.exceptions.ConnectionError:
        print("\n[ERROR] Could not connect to server.")
        print("Is it running on port 8000?")
        print("Try running: python manage.py runserver")

    except Exception as e:
        print(f"\n[UNEXPECTED ERROR] {e}")


if __name__ == "__main__":
    check_connection()
