from django.core.management.base import BaseCommand
from assets.models import Asset, Manufacturer


class Command(BaseCommand):
    help = 'Creates sample assets for the manufacturer Sloan'

    def handle(self, *args, **kwargs):
        manufacturer_name = "Sloan"

        self.stdout.write(f"Searching for manufacturer: {manufacturer_name}...")

        # Search for the Manufacturer
        try:
            manufacturer = Manufacturer.objects.get(name=manufacturer_name)
            self.stdout.write(
                self.style.SUCCESS(f"Found existing manufacturer: {manufacturer.name} (ID: {manufacturer.id})"))
        except Manufacturer.DoesNotExist:
            self.stdout.write(f"Manufacturer '{manufacturer_name}' not found. Creating it now...")
            manufacturer = Manufacturer.objects.create(name=manufacturer_name)
            self.stdout.write(
                self.style.SUCCESS(f"Created new manufacturer: {manufacturer.name} (ID: {manufacturer.id})"))

        # Define the assets to create
        assets_to_create = [
            {
                "unique_id": "SLOAN-VALVE-001",
                "model": "Royal 111",
                "description": "Exposed Flushometer for Water Closets"
            },
            {
                "unique_id": "SLOAN-SINK-002",
                "model": "AER-DEC",
                "description": "Integrated Sink System with Soap Dispenser"
            },
            {
                "unique_id": "SLOAN-SENSOR-003",
                "model": "EBF-85",
                "description": "Sensor Activated Electronic Hand Washing Faucet"
            }
        ]

        # Create the assets
        self.stdout.write("\nCreating assets...")
        for item in assets_to_create:
            asset, created = Asset.objects.get_or_create(
                unique_id=item['unique_id'],
                defaults={
                    'manufacturer': manufacturer,
                    'model': item['model'],
                    'description': item['description']
                }
            )

            if created:
                self.stdout.write(
                    self.style.SUCCESS(f" [SUCCESS] Created Asset: {item['model']} ({item['unique_id']})"))
            else:
                self.stdout.write(self.style.WARNING(f" [SKIPPED] Asset already exists: {item['unique_id']}"))