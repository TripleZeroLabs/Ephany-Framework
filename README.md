# Ephany Framework

Ephany Framework is an open-source Asset and Project management system built with Django. It serves as a robust backend 
API designed to be consumed by modern frontend applications (desktop, web, mobile, or even CLI).

## Features

*   **Asset Management:** Track building assets (fixtures, equipment, components, and more) with metadata that is relevant to the design, construction, and procurement process.
*   **Project Tracking:** Manage projects in respect to their relevant assets (per milestone).
*   **API First:** Fully decoupled architecture using Django REST Framework.
*   **Self-Describing:** A complete OpenAPI 3 schema is served at `/api/schema/` and committed to the repo as `openapi.yaml`, so clients, SDKs, and coding agents can discover the API without reading the source.
*   **Worked Examples:** The [`examples/`](examples/) folder ships readable, runnable integrations you can copy and point at your own systems.

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

Enter the Django shell with the following command:
`python manage.py shell`

Execute the following commands to generate a new secret key:

`from django.core.management.utils import get_random_secret_key`  
`get_random_secret_key()`

Save this key for used in the next step.

Exit the shell with `exit()`. 

Copy `.env.example` to `.env` and fill in the secret key you just generated. Note that this file must be encoded as UTF-8.

```
cp .env.example .env
```

At minimum, `.env` needs:

```
DJANGO_SECRET_KEY=your-secret-key-here
DJANGO_DEBUG=True
```

See `.env.example` for the full list of supported variables, including the optional Smartsheet sync settings.

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

## API Documentation

The API describes itself. Once the server is running:

| URL | What it is |
| --- | --- |
| `http://127.0.0.1:8000/api/docs/` | Swagger UI — browse and try every endpoint |
| `http://127.0.0.1:8000/api/redoc/` | ReDoc — the same schema, reference-style |
| `http://127.0.0.1:8000/api/schema/` | The raw OpenAPI 3 document |

These three routes stay reachable even when API key authentication is enabled,
since the schema describes the API's shape without exposing any records. If you
would rather keep them private, remove them from `API_KEY_EXEMPT_PATHS` in
`ephany_framework/settings/base.py`.

### Using the schema without running the server

The generated spec is committed at [`openapi.yaml`](openapi.yaml) in the repo
root. Point a code generator, an HTTP client, or a coding agent at it directly:

```
https://raw.githubusercontent.com/TripleZeroLabs/Ephany-Framework/master/openapi.yaml
```

Regenerate it after changing any serializer, viewset, or route:

```
python manage.py spectacular --file openapi.yaml --validate --fail-on-warn
```

`--fail-on-warn` makes the command exit non-zero if any endpoint cannot be
described accurately, which keeps the committed spec honest.

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

For worked examples — including importing a whole fleet of projects from an external system of record — see the [`examples/`](examples/) folder.

---

## Examples

The [`examples/`](examples/) folder holds complete, runnable integrations that
exist to be read and copied. Nothing in the core apps depends on them.

`examples/smartsheet_sync/` imports a fleet of projects and their asset
snapshots from Smartsheet. Smartsheet is incidental — the code is split so that
one small module knows the external API and everything else is mapping and
write logic, which is the part that transfers to Airtable, a Google Sheet, a
nightly CSV drop, or an internal REST API.

Both commands are annotated with `STEP` banners walking through the shape every
importer of this kind shares: declare the mapping, fetch, diff, write only what
changed. See [`examples/README.md`](examples/README.md) for the recipe and the
design decisions worth copying.

```
python manage.py sync_projects_from_smartsheet <API_KEY> --dry-run
```

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
