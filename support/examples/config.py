# Shared configuration for example scripts

# You can change this to your production URL or a different port
BASE_URL = "http://127.0.0.1:8000/api"

# Your API key (create using: python manage.py create_apikey "<name>")
API_KEY = "YOUR_API_KEY"

# Common headers
HEADERS = {
    "Content-Type": "application/json",
    "X-API-Key": API_KEY
}