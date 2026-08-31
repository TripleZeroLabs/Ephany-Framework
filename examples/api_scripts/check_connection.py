#!/usr/bin/env python3
"""
Health check: can these scripts reach the API, and are the credentials right?

Run this first. It separates the three things that look identical when a
script fails — server down, wrong URL, and rejected credential — and says which
one you have.

Usage:
    python check_connection.py

(Named check_connection rather than test_api so Django's test runner does not
try to collect it as a test module.)
"""

import requests

import config


def main():
    print(f"Connecting to {config.BASE_URL} ...")
    print("Credential:", "X-API-Key" if config.API_KEY else "none (anonymous)")

    try:
        response = requests.get(f"{config.BASE_URL}/", headers=config.headers(), timeout=5)
    except requests.ConnectionError:
        print("\n[UNREACHABLE] Nothing answered at that address.")
        print("  Start the server with: python manage.py runserver")
        print(f"  Or point EPHANY_BASE_URL somewhere else (currently {config.BASE_URL}).")
        return 1
    except requests.Timeout:
        print("\n[TIMEOUT] The server accepted the connection but did not reply.")
        return 1

    if response.status_code == 200:
        endpoints = response.json()
        print(f"\n[OK] Connected. {len(endpoints)} endpoints available:")
        for name in sorted(endpoints):
            print(f"  {name}")
        print("\nFull documentation: " + config.BASE_URL.rsplit("/api", 1)[0] + "/api/docs/")
        return 0

    if response.status_code == 401:
        print("\n[NO CREDENTIAL] The server is up and requires authentication.")
        print("  This is normal for a deployed server (DJANGO_DEBUG=False).")
        print('  Create a key with: python manage.py create_apikey "Example Scripts"')
        print("  then set API_KEY in config.py or the EPHANY_API_KEY variable.")
        return 1

    if response.status_code == 403:
        print("\n[BAD CREDENTIAL] The server is up, but rejected the key.")
        print("  It may be mistyped, or deactivated in the Django admin.")
        return 1

    print(f"\n[UNEXPECTED] HTTP {response.status_code}")
    print(response.text[:500])
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
