# Ephany Framework

Ephany Framework is an open-source Asset and Project management system built with Django. It serves as a robust backend 
API designed to be consumed by modern frontend applications (desktop, web, mobile, or even CLI).

## Features

*   **Asset Management:** Track building assets (fixtures, equipment, components, and more) with metadata that is relevant to the design, construction, and procurement process.
*   **Project Tracking:** Manage projects in respect to their relevant assets (per milestone).
*   **API First:** Fully decoupled architecture using Django REST Framework.
*   **Built-in Admin Panel:** Easily manage users, assets, and projects from the default Django admin panel.

## Tech Stack

*   **Language:** Python 3.12+
*   **Framework:** Django 6.0
*   **API:** Django REST Framework (DRF)
*   **Database:** SQLite (default for Dev), extensible to PostgreSQL/MySQL.

## Installation & Setup

Follow these steps to set up the development environment locally.

### 1. Clone the Repository

    git clone https://github.com/XXXX.git
    cd ephany-framework

### 2. Create a Virtual Environment

    python -m venv .venv
    
    # Activate it
    # Windows:
    .venv\Scripts\activate
    # Mac/Linux:
    source .venv/bin/activate

### 3. Install Dependencies

    pip install -r requirements.txt

### 4. Configure Environment Variables

Create a `.env` file in the root directory (copy from `.env.example` if available, or use the template below):

    DJANGO_SECRET_KEY=your-secret-key-here
    DJANGO_DEBUG=True

### 5. Run Migrations & Server

    python manage.py migrate

### 6. Create Superuser (Admin Access)

Since the database is local to your environment, you need to create your own administrative account to access the Django Admin panel.

    python manage.py createsuperuser

Follow the prompts to set your username, email, and password.

### 7. Run the Server

    python manage.py runserver

By default, the API will be available at `http://127.0.0.1:8000/api`.
The Admin panel is at `http://127.0.0.1:8000/admin/`.

## 🤝 Contributing

We welcome contributions! Please see `CONTRIBUTING.md` (coming soon) for details on how to submit pull requests, report issues, or request features.

## 📄 License

This project is licensed under the [GNU Affero General Public License v3.0 (AGPL-3.0)](LICENSE).