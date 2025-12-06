# Ephany Framework API Documentation

Welcome to the developer documentation for the Ephany Framework. This guide covers the data structure, API endpoints, and common usage patterns.

> **Note:** The Ephany Framework is built on top of [Django](https://www.djangoproject.com/) and the [Django REST Framework](https://www.django-rest-framework.org/). While this documentation covers the specifics of our API, having a foundational understanding of Django models, views, and ORM is highly recommended before starting development. If you are new to Django, we suggest starting with the [official Django tutorial](https://docs.djangoproject.com/en/stable/intro/tutorial01/) or the [MDN Django Guide](https://developer.mozilla.org/en-US/docs/Learn/Server-side/Django).

---

## 📚 Table of Contents

1.  [**Data Models**](#1-data-models)
    *   [Assets & Attributes](#assets--attributes)
    *   [Projects & Snapshots](#projects--snapshots)
    *   [Users & Settings](#users--settings)
2.  [**Revit & BIM Integration**](#2-revit--bim-integration)
    *   [Autodesk ForgeTypeId](#autodesk-forgetypeid-mapping)
    *   [Future Roadmap](#future-roadmap-deep-parameter-integration)
3.  [**API Reference**](#3-api-reference)
    *   [Authentication](#authentication)
    *   [Endpoints Overview](#endpoints-overview)
4.  [**Cookbook (Sample Calls)**](#4-sample-api-calls)
    *   [Creating a User](#creating-a-user)
    *   [Searching for Assets](#searching-for-assets)
    *   [Updating Custom Fields](#updating-custom-fields-unit-aware)

---

<a name="1-data-models"></a>
## 1. Data Models

The framework is divided into three main domains:

### Assets & Attributes
The core of the system. Assets represent physical objects (pumps, valves, furniture) that have standard dimensions and infinite custom properties.

**Asset Attributes & Intelligent Units**
The `AssetAttribute` model acts as a strict schema registry for the open-ended `custom_fields` JSON attached to every Asset. This allows the system to support **infinite custom fields** without requiring database schema migrations for every new property (e.g., `flange_rating`, `voltage`, `material_finish`).

Crucially, this model powers Ephany's **Automatic Unit Conversion** engine:
*   **Metric Storage (Single Source of Truth):** To maintain engineering integrity, Ephany stores all physical values in the database in **Base Metric Units** (Millimeters for length, Kilograms for mass, Square Meters for area).
*   **User-Centric IO:** The API middleware intercepts all reads and writes. It checks the logged-in user's `UserSettings` to determine their preferred unit system (e.g., Imperial/Feet).
*   **Seamless Conversion:** If a user (who prefers Inches) saves a `shelf_width` of `10`, the system converts and saves it as `254.0` (mm). When retrieved, it converts back to `10.0`.

| Model | Description | Key Fields |
| :--- | :--- | :--- |
| **Asset** | A physical product or component. | `unique_id`, `model`, `manufacturer`, `height`, `width`, `depth`, `custom_fields` (JSON) |
| **Manufacturer** | The maker of the asset. | `name`, `url` |
| **AssetFile** | Attachments like PDFs or CAD files. | `file`, `category` (Cut Sheet, Revit Family, etc.) |
| **AssetAttribute** | Schema definition for custom fields. | `name` (key), `data_type` (int/str), `unit_type` (Length, Area, etc.) |

### Projects & Snapshots
Used for tracking the usage or state of assets over time.

| Model | Description | Key Fields                                 |
| :--- | :--- |:-------------------------------------------|
| **Project** | A construction or design project. | `unique_id`, `name`, `description` |
| **Snapshot** | A frozen state of a project at a specific date. | `project`, `name`, `date`, `assets` (JSON) |

### Users & Settings
Handles authentication and user-specific preferences (like Unit Systems).

| Model | Description | Key Fields |
| :--- | :--- | :--- |
| **User** | Standard Django User. | `username`, `email`, `password` |
| **UserSettings** | User preferences (Metric vs Imperial). | `length_unit` (mm/ft), `mass_unit` (kg/lb), `area_unit` |

---

<a name="2-revit--bim-integration"></a>
## 2. Revit & BIM Integration

Ephany is designed from the ground up for interoperability with Building Information Modeling (BIM) workflows.

### Autodesk ForgeTypeId Mapping
The unit types in `AssetAttribute` (e.g., `autodesk.spec.aec:length-2.0.0`) map directly to **Autodesk's ForgeTypeId schemas**. This ensures that data extracted from Ephany can be injected directly into Revit or Forge APIs without complicated mapping.
*   [Autodesk ForgeTypeId Documentation](https://www.revitapidocs.com/2024/e895e206-7654-445f-27a7-669df676df21.htm)

### Future Roadmap: Deep BIM Data Integration
Upcoming releases will expand this mapping to include:
*   **Revit Built-in Parameters:** Direct mapping to hardcoded standard Revit data. ([Docs](https://www.revitapidocs.com/2024/fb011c91-be7e-f737-28c7-3f1e1917a0e0.htm))
*   **Shared Parameters:** Support for loading GUID-based Shared Parameter files (`.txt`) to sync definitions across projects. ([Docs](https://help.autodesk.com/view/RVT/2024/ENU/?guid=GUID-91270D94-D66A-4973-8AB6-CB697424992A))
*   **IFC Property Sets:** Standardization for OpenBIM exports using IFC4/IFC2x3 Property Sets (`Pset_WallCommon`). ([buildingSMART IFC Documentation](https://standards.buildingsmart.org/IFC/RELEASE/IFC4/ADD2_TC1/HTML/))

---

<a name="3-api-reference"></a>
## 3. API Reference

The API is built with **Django Rest Framework**. All endpoints accept and return JSON.

### Authentication
*   **Basic Auth:** Supports standard Username/Password (great for scripts).
    *   Header: `Authorization: Basic <base64_credentials>`
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

<a name="4-sample-api-calls"></a>
## 4. Sample API Calls

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