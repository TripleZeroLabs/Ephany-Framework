"""
Shared configuration and helpers for the example scripts.

Edit BASE_URL and API_KEY to match your server, or set the matching environment
variables. Nothing else in the framework imports this file.
"""

import os

import requests

# Where the API lives. Point this at your own server when you have one.
BASE_URL = os.getenv("EPHANY_BASE_URL", "http://127.0.0.1:8000/api")

# Optional. On a fresh local install with DEBUG on, the API answers
# unauthenticated requests and you can leave this empty. Once the server is
# deployed with DJANGO_DEBUG=False, requests need a credential:
#
#     python manage.py create_apikey "Example Scripts"
#
# API keys suit scripts like these, which run on a machine you control. They do
# not suit a browser app, which cannot keep the key secret.
API_KEY = os.getenv("EPHANY_API_KEY", "")


def headers():
    """Auth headers for an API request, or an empty dict if no key is set."""
    return {"X-API-Key": API_KEY} if API_KEY else {}


def get_page(path, params=None):
    """
    GET one page from a list endpoint and return the decoded JSON.

    Raises requests.HTTPError on 4xx/5xx so a missing or rejected credential
    surfaces immediately rather than looking like an empty result.
    """
    response = requests.get(f"{BASE_URL}{path}", params=params, headers=headers())
    response.raise_for_status()
    return response.json()


def get_all(path, params=None):
    """
    Follow pagination and return every row from a list endpoint.

    List endpoints are paginated. A response looks like:

        {"count": 143, "next": "...?page=2", "previous": null, "results": [...]}

    so iterating the response directly walks the four keys of that envelope,
    not your data. Read `results`, and follow `next` until it is null.

    Detail endpoints such as /assets/1/ return a bare object with no envelope.
    """
    rows = []
    payload = get_page(path, params)

    while True:
        rows.extend(payload["results"])
        next_url = payload.get("next")
        if not next_url:
            return rows
        # `next` is an absolute URL already carrying the page and any filters.
        response = requests.get(next_url, headers=headers())
        response.raise_for_status()
        payload = response.json()


def explain_http_error(error):
    """Turn an HTTPError into advice, since the status codes are meaningful."""
    status = error.response.status_code
    if status == 401:
        return (
            "401 Unauthorized: the server wants a credential and none was sent.\n"
            "Set API_KEY in config.py (or the EPHANY_API_KEY environment\n"
            'variable). Create one with: python manage.py create_apikey "Scripts"'
        )
    if status == 403:
        return (
            "403 Forbidden: a key was sent but the server rejected it.\n"
            "It may be mistyped, or deactivated in the Django admin."
        )
    return f"{status} {error.response.reason}: {error.response.text[:300]}"
