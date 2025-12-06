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

## Available Scripts

### 1. test_api.py
#### Connection Check
A simple health check script. Use this first to ensure your API is online and reachable.
```bash
python examples/test_api.py
```

### 2. users_workflows.py
#### User & Settings Workflow
Demonstrates the complete user lifecycle:
- **Registering a new user** (with custom unit preferences).
- **Authenticating** (Basic Auth).
- **Updating Settings** (e.g., switching from Feet to Millimeters).
- **Listing Users**.

This is a great reference for how to handle authentication and nested JSON data in the API.
```bash
python examples/users_workflows.py
```

### 3. assets_search.py
#### Asset Search
A command-line tool to search for assets and manufacturers using various filters.

**Search by Asset ID:**
```bash
python examples/assets_search.py id "A-001"
```

**Search by Manufacturer & Model:**
```bash
python examples/assets_search.py model "Sony" "X1"
```

**Search Manufacturer by Name:**
```bash
python examples/assets_search.py manufacturer "Sony Corp"
```

### 4. assets_custom_fields.py
#### Unit Conversion CLI Tool
An interactive command-line application that demonstrates the automatic unit conversion logic.

**How it works:**
1.  **Login:** It prompts you for a `Username` and `Password`.
2.  **Context:** It fetches and displays your current unit preferences (e.g., "Inches").
3.  **Asset Selection:** You enter the `Unique ID` of an asset you want to update.
4.  **Update:** You enter a `Field Key` (e.g., `shelf_width`) and a `New Value` **in your preferred units** (e.g., 12.5 inches).
5.  **Conversion:** The system automatically converts your input to Metric (mm) before saving to the database.
6.  **Verification:** The tool reads the value back to confirm it matches your input, and calculates the internal metric value to prove the conversion happened.

**Requirement:** You must define the custom field (e.g., `shelf_width`) as a `Length` attribute in the before running this.

```bash
python examples/assets_custom_fields.py
```

---

## How It Works (Code Breakdown)

The core idea is simple: we send a "Request" to the server, and it sends back "Response" data in JSON format (which looks just like a Python dictionary).

### Fetching Data (`GET`)
Here is how we find an asset by its unique ID.

```python
import requests

url = "http://127.0.0.1:8000/api/assets/"
params = {'unique_id__iexact': "A-001"} # Case-insensitive search

response = requests.get(url, params=params)

if response.status_code == 200:
    data = response.json()
    print("Found Asset:", data)
```

### Creating Data (`POST`)
To add something new, like a User or Asset, we use `requests.post`.

```python
import requests

url = "http://127.0.0.1:8000/api/manufacturers/"
new_data = {"name": "New Corp"}

response = requests.post(url, json=new_data)

if response.status_code == 201: # 201 means "Created"
    print("Success! Created manufacturer.")
```