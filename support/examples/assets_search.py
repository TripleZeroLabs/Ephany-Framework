import requests
import json
import argparse
from config import BASE_URL


def search_by_type_id(type_id):
    """Search for an asset specifically by its type_id (case-insensitive)."""
    print(f"\n--- Searching for Unique ID: {type_id} ---")

    # Changed from 'type_id' to 'type_id__iexact'
    params = {'type_id__iexact': type_id}
    response = requests.get(f"{BASE_URL}/assets/", params=params)

    if response.status_code == 200:
        results = response.json()
        if results:
            print(f"Found {len(results)} asset(s):")
            print(json.dumps(results, indent=2))
        else:
            print("No assets found with that ID.")
    else:
        print(f"Error: {response.status_code} - {response.text}")


def search_by_manufacturer_and_model(manufacturer_name, model_name):
    print(f"\n--- Searching for Manufacturer: '{manufacturer_name}' AND Model: '{model_name}' ---")

    params = {
        'manufacturer__name__icontains': manufacturer_name,
        'model__icontains': model_name
    }
    response = requests.get(f"{BASE_URL}/assets/", params=params)

    if response.status_code == 200:
        results = response.json()
        if results:
            print(f"Found {len(results)} match(es):")
            for asset in results:
                print(f"- {asset['manufacturer_name']} {asset['model']} (ID: {asset['type_id']})")
        else:
            print("No matching assets found.")
    else:
        print(f"Error: {response.status_code}")


def search_manufacturer_by_name(name):
    """Search for a manufacturer by name (case-insensitive) and return JSON."""
    print(f"\n--- Searching for Manufacturer: '{name}' ---")

    # Changed from 'name' to 'name__iexact' (or use name__icontains for partial)
    params = {'name__iexact': name}
    response = requests.get(f"{BASE_URL}/manufacturers/", params=params)

    if response.status_code == 200:
        results = response.json()
        if results:
            print(json.dumps(results[0], indent=2))
        else:
            print("Manufacturer not found.")
    else:
        print(f"Error: {response.status_code}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Search for assets or manufacturers via the API.")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Command: id <type_id>
    parser_id = subparsers.add_parser('id', help='Search asset by Unique ID')
    parser_id.add_argument('type_id', type=str, help='The Unique ID of the asset')

    # Command: model <manufacturer> <model>
    parser_model = subparsers.add_parser('model', help='Search asset by Manufacturer and Model')
    parser_model.add_argument('manufacturer', type=str, help='Manufacturer name (partial)')
    parser_model.add_argument('model_name', type=str, help='Model name (partial)')

    # Command: manufacturer <name>
    parser_man = subparsers.add_parser('manufacturer', help='Search manufacturer by exact name')
    parser_man.add_argument('name', type=str, help='Exact manufacturer name')

    args = parser.parse_args()

    if args.command == 'id':
        search_by_type_id(args.type_id)
    elif args.command == 'model':
        search_by_manufacturer_and_model(args.manufacturer, args.model_name)
    elif args.command == 'manufacturer':
        search_manufacturer_by_name(args.name)
    else:
        parser.print_help()