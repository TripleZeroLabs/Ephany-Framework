# Ephany Framework

Ephany Framework is an open-source Asset and Project management system built with Django. It serves as a robust backend 
API designed to be consumed by modern frontend applications (desktop, web, mobile, or even CLI).

## Features

*   **Asset Management:** Track building assets (fixtures, equipment, components, and more) with metadata that is relevant to the design, construction, and procurement process.
*   **Project Tracking:** Manage projects in respect to their relevant assets (per milestone).
*   **API First:** Fully decoupled architecture using Django REST Framework.

## Tech Stack

*   **Language:** Python 3.12+
*   **Framework:** Django 6.0
*   **API:** Django REST Framework (DRF)
*   **Database:** SQLite (default for Dev), extensible to PostgreSQL/MySQL.

## Installation & Setup

Follow these steps to set up the development environment locally.

### 1. Clone the Repository

```
git clone https://github.com/TripleZeroLabs/Ephany-Framework.git
cd Ephany-Framework
```

### 2. Create a Virtual Environment

```
python -m venv .venv
    
# Activate it
# Windows:
.venv\Scripts\activate
# Mac/Linux:
source .venv/bin/activate
```

### 3. Install Dependencies

```
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the root directory (copy from `.env.example` if available, or use the template below):

```
DJANGO_SECRET_KEY=your-secret-key-here
DJANGO_DEBUG=True
```

### 5. Run Migrations & Server

```
python manage.py migrate
```

### 6. Create Superuser (Admin Access)

Since the database is local to your environment, you need to create your own administrative account to access the Django Admin panel.

```
python manage.py createsuperuser
```

Follow the prompts to set your username, email, and password.

### 7. Run the Server

```
python manage.py runserver
```

By default, the API will be available at `http://127.0.0.1:8000/api`.  
The Admin panel is at `http://127.0.0.1:8000/admin/`.

---

## API Key Authentication

Ephany Framework includes a lightweight API key authentication layer that is **disabled by default** for easy development and onboarding.  
When enabled, any request to protected API routes (such as `/api/...`) must include a valid API key.

### Enabling API Key Authentication

Set the environment variable:

```
API_KEY_AUTH_ENABLED=true
```

(When absent or set to `false`, the API is open for development.)

### Creating an API Key

Use the built-in management command:

```
python manage.py create_apikey "Local Dev"
```

This will output a new key, for example:

```
API key (store this somewhere safe):
abc123xyz...
```

### Using the API Key

All clients must send the key using the HTTP header:

```
X-API-Key: <your-key>
```

Example using `curl`:

```
curl -H "X-API-Key: abc123xyz" http://127.0.0.1:8000/api/assets/
```

### Authentication Errors

If authentication is required but missing or invalid, the API returns:

* `401 Unauthorized` – API key is missing  
* `403 Forbidden` – API key is invalid or inactive  

---

## API Usage Example

The framework exposes a powerful REST API. Below is an example of how to search for assets by **Manufacturer Name** using a standard HTTP GET request.

Full API Documentation (in progress): https://documenter.getpostman.com/view/37222443/2sB3dVNnDe

### Request

**Endpoint:** `GET /api/assets/`  
**Filter:** `?manufacturer__name__icontains=Sony`

```
curl -X GET "http://127.0.0.1:8000/api/assets/?manufacturer__name__icontains=Sony" -H "Content-Type: application/json"
```

If API key authentication is enabled, add:

```
-H "X-API-Key: <your-key>"
```

### Response

```json
[
  {
    "id": 1,
    "type_id": "A-001",
    "manufacturer": 1,
    "manufacturer_name": "Sony Corp",
    "model": "Bravia X1",
    "description": "55 inch 4K TV",
    "url": "https://electronics.sony.com/tv",
    "files": [
      {
        "id": 5,
        "file": "/media/assets/files/manual.pdf",
        "category": "PDS",
        "category_display": "Cut Sheet",
        "uploaded_at": "2023-10-27T14:30:00Z"
      }
    ],
    "file_ids": [5]
  }
]
```

For executable Python scripts and more advanced usage, check out the `support/examples` folder.

---

## Additional Notes

### Media and File Uploads

This project handles user-uploaded files (e.g., PDFs and Revit Families for Assets) in the `media/` directory.

- **Development:** The project is configured to serve media files automatically when `DEBUG=True`.  
- **Git:** The `media/` directory is ignored by version control to prevent user data from being committed.  
- **Production:** When deploying, configure your web server (Nginx, Apache) or a storage service (S3, etc.) to serve files from `MEDIA_ROOT`.

---

## Contributing

We welcome contributions! Please see `CONTRIBUTING.md` (coming soon) for details on how to submit pull requests, report issues, or request features.

## License

This project is licensed under the [GNU Affero General Public License v3.0 (AGPL-3.0)](LICENSE).
