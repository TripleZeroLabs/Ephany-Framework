# Ephany Framework API Documentation

Welcome to the developer documentation for the Ephany Framework. This guide covers the data structure, API endpoints, and common usage patterns.

> **Note:** The Ephany Framework is built on top of [Django](https://www.djangoproject.com/) and the [Django REST Framework](https://www.django-rest-framework.org/). While this documentation covers the specifics of our API, having a foundational understanding of Django models, views, and ORM is highly recommended before starting development. If you are new to Django, we suggest starting with the [official Django tutorial](https://docs.djangoproject.com/en/stable/intro/tutorial01/) or the [MDN Django Guide](https://developer.mozilla.org/en-US/docs/Learn/Server-side/Django).

---

## 📚 Table of Contents

1.  [**Data Models**](#1-data-models)
    *   [Assets & Attributes](#assets--attributes)
    *   [Projects & Snapshots](#projects--snapshots)
    *   [Users & Settings](#users--settings)
2.  [**API Reference**](#2-api-endpoints)
    *   [Authentication](#authentication)
    *   [Endpoints Overview](#endpoints-overview)
3.  [**Cookbook (Sample Calls)**](#3-sample-api-calls)
    *   [Creating a User](#creating-a-user)
    *   [Searching for Assets](#searching-for-assets)
    *   [Updating Custom Fields](#updating-custom-fields-unit-aware)

---

<a name="1-data-models"></a>
## 1. Data Models

The framework is divided into three main domains:

### Assets & Attributes
The core of the system. Assets represent physical objects (pumps, valves, furniture) that have standard dimensions and infinite custom properties.

| Model | Description | Key Fields |
| :--- | :--- | :--- |
| **Asset** | A physical product or component. | `unique_id`, `model`, `manufacturer`, `height`, `width`, `depth`, `custom_fields` (JSON) |
| **Manufacturer** | The maker of the asset. | `name`, `url` |
| **AssetFile** | Attachments like PDFs or CAD files. | `file`, `category` (Cut Sheet, Revit Family, etc.) |
| **AssetAttribute** | Schema definition for custom fields. | `name` (key), `data_type` (int/str), `unit_type` (Length, Area, etc.) |

### Projects & Snapshots
Used for tracking the usage or state of assets over time.

| Model | Description | Key Fields |
| :--- | :--- | :--- |
| **Project** | A construction or design project. | `unique_id`, `name`, `description` |
| **Snapshot** | A frozen state of a project at a specific date. | `project`, `name`, `date`, `data` (JSON) |

### Users & Settings
Handles authentication and user-specific preferences (like Unit Systems).

| Model | Description | Key Fields |
| :--- | :--- | :--- |
| **User** | Standard Django User. | `username`, `email`, `password` |
| **UserSettings** | User preferences (Metric vs Imperial). | `length_unit` (mm/ft), `mass_unit` (kg/lb), `area_unit` |

---

<a name="2-api-endpoints"></a>
## 2. API Endpoints

The API is built with **Django Rest Framework**. All endpoints accept and return JSON.

### Authentication
*   **Basic Auth:** Supports standard Username/Password (great for scripts).
*   **Session Auth:** Uses cookies (great for browsers).

### Endpoints Overview
Base URL: `http://localhost:8000/api/`

| Endpoint | Methods | Description |
| :--- | :--- | :--- |
| `/assets/` | `GET`, `POST` | List or create assets. Supports filtering. |
| `/assets/{id}/` | `GET`, `PATCH`, `DELETE` | Retrieve or update a specific asset. |
| `/manufacturers/` | `GET`, `POST` | Manage manufacturers. |
| `/files/` | `GET`, `POST` | Upload or list files. |
| `/projects/` | `GET`, `POST` | Manage projects. |
| `/users/` | `GET`, `POST` | Register new users or list existing ones. |

---

<a name="3-sample-api-calls"></a>
## 3. Sample API Calls

Examples using Python `requests`.

### Creating a User
Registers a new user and sets their preferred units to **Inches**.

```python
import requests

url = "http://localhost:8000/api/users/"
payload = {
    "username": "architect_jane",
    "email": "jane@example.com",
    "password": "SecurePassword123!",
    "settings": {
        "length_unit": "in"  # User prefers Inches
    }
}

response = requests.post(url, json=payload)
print(response.json())
```

### Searching for Assets
Find an asset by its unique ID (case-insensitive).

```python
url = "http://localhost:8000/api/assets/"
params = {"unique_id__iexact": "PUMP-001"}

response = requests.get(url, params=params)
# Returns a list of matching assets
```

### Updating Custom Fields (Unit Aware)
When updating an asset, the API automatically converts your input to Metric based on your user settings.

**Scenario:** User settings are set to **Inches**. User updates `shelf_width` to **10**.

```python
# 1. Authenticate as 'architect_jane' (who uses Inches)
auth = ("architect_jane", "SecurePassword123!")

# 2. Patch the Asset
url = "http://localhost:8000/api/assets/1/"
payload = {
    "custom_fields": {
        "shelf_width": 10  # System interprets this as 10 INCHES
    }
}

response = requests.patch(url, json=payload, auth=auth)

# 3. Verification
# The database now stores this as 254.0 mm.
# But when 'architect_jane' reads it back, she sees 10.
print(response.json()['custom_fields']['shelf_width']) # Output: 10.0
```