import requests
from config import BASE_URL

def check_connection():
    """
    Simple health check to see if the API is reachable.
    We ping the API root endpoint.
    """
    print(f"Connecting to {BASE_URL}...")
    
    try:
        response = requests.get(BASE_URL, timeout=5)
        
        if response.status_code == 200:
            print(f"\n[SUCCESS] Connected to API!")
            print(f"Status: {response.status_code} OK")
            print("Server is online and responding.")
        else:
            print(f"\n[WARNING] Server responded with status code: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("\n[ERROR] Could not connect to server.")
        print("Is it running on port 8000?")
        print("Try running: python manage.py runserver")

if __name__ == "__main__":
    check_connection()