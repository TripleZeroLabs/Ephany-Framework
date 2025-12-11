#!/usr/bin/env python3
"""
Demo: Import Assets from JSON

This script demonstrates how to bulk import assets from a JSON file
using the Ephany Framework API.

Prerequisites:
    1. Create the manufacturer in Django Admin first and note the ID
    2. Create AssetAttributes for 'door_type' (str) and 'door_quantity' (int)

Usage:
    python assets_import_from_json.py
"""

import json
import requests
from config import BASE_URL

# Configuration
JSON_FILE = "avantco_refrigerators.json"
ID_PREFIX = "AVN"


def load_json_data(filepath):
    """Load and return JSON data from file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def create_asset(item, sequence_number):
    """Create a single asset via the API."""

    # Build the payload
    payload = {
        'type_id': f"{ID_PREFIX}-{sequence_number}",
        'manufacturer': item['manufacturer_id'],
        'model': item['model'],
        'name': item['name'],
        'description': item['description_short'],
        'url': item['product_url'],
        'overall_width': item['dimensions']['width'],
        'overall_depth': item['dimensions']['depth'],
        'overall_height': item['dimensions']['height'],
        'custom_fields': {
            'door_type': item['doors']['type'],
            'door_quantity': item['doors']['quantity'],
        },
        'input_units': {
            'length': 'in'
        }
    }

    response = requests.post(f"{BASE_URL}/assets/", json=payload)
    return response


def format_error(response):
    """Extract a readable error message from the API response."""
    try:
        error_data = response.json()
        if isinstance(error_data, dict):
            messages = []
            for field, errors in error_data.items():
                if isinstance(errors, list):
                    messages.append(f"{field}: {', '.join(str(e) for e in errors)}")
                else:
                    messages.append(f"{field}: {errors}")
            return "; ".join(messages)
        return str(error_data)
    except Exception:
        # If response is HTML or not JSON, return a generic message
        return f"HTTP {response.status_code} error"


def main():
    print("=" * 60)
    print("Ephany Framework - Asset Import Demo")
    print("=" * 60)
    
    # Load JSON data
    data = load_json_data(JSON_FILE)
    print(f"\nLoaded {len(data)} items from {JSON_FILE}")
    
    # Import each item
    created = 0
    failed = 0
    
    for i, item in enumerate(data, start=1):
        response = create_asset(item, i)
        
        if response.status_code == 201:
            result = response.json()
            print(f"[OK] {i:02d}. {result['type_id']} - {result['name'][:50]}")
            created += 1
        else:
            error_msg = format_error(response)
            print(f"[FAIL] {i:02d}. {item['model']} - {error_msg}")
            failed += 1
    
    # Summary
    print("\n" + "=" * 60)
    print(f"Import Complete: {created} created, {failed} failed")
    print("=" * 60)


if __name__ == "__main__":
    main()