# API Examples

This folder contains Python scripts demonstrating how to interact with the Ephany Framework. These scripts show you how to get data out of the system using simple Python code.

## Prerequisites

1. **Run the Server**: Ensure your Django development server is running.
   ```bash
   python manage.py runserver
   ```
2. **Install Dependencies**: The scripts use `requests`, a popular tool for talking to websites and APIs.
   ```bash
   pip install requests
   ```
3. **Configuration**: Check `config.py` to ensure the `BASE_URL` matches your local server (usually `http://127.0.0.1:8000/api`).

---

## How It Works (Code Breakdown)

The core idea is simple: we send a "Request" to the server, and it sends back "Response" data in JSON format (which looks just like a Python dictionary).

### 1. Searching for an Asset

Here is how we find an asset by its unique ID. Notice how we pass the search term in a dictionary called `params`.

```python
import requests

# The endpoint we are talking to
url = "http://127.0.0.1:8000/api/assets/"

# What we are looking for
# 'iexact' means "insensitive exact", so "a-001" finds "A-001"
params = {'unique_id__iexact': "A-001"}

# Ask the server for the data
response = requests.get(url, params=params)

# If the server says "OK" (Status 200), get the JSON data
if response.status_code == 200:
    data = response.json()
    print("Found Asset:", data)
```

### 2. Creating Data

To add something new, like a Manufacturer, we use `requests.post` instead of `get`.

```python
url = "http://127.0.0.1:8000/api/manufacturers/"
new_data = {"name": "New Corp"}

# Send the data to the server
response = requests.post(url, json=new_data)

if response.status_code == 201: # 201 means "Created"
    print("Success! Created manufacturer.")
```

---

## Running the Example Scripts

We have included ready-to-run scripts for you.

### `search_assets.py`

A command-line tool to search for assets and manufacturers.

**Search by Asset ID:**
```bash
python examples/search_assets.py id "A-001"
```

**Search by Manufacturer & Model:**
```bash
python examples/search_assets.py model "Sony" "X1"
```

**Search Manufacturer by Name:**
```bash
python examples/search_assets.py manufacturer "Sony Corp"
```

### `test_api.py`

A simple script to fetch all assets at once.

```bash
python examples/test_api.py
```