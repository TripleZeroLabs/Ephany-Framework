from django.core.management.base import BaseCommand
from assets.models import Asset


class Command(BaseCommand):
    help = 'Lists all assets currently in the database'

    def handle(self, *args, **kwargs):
        assets = Asset.objects.select_related('manufacturer').all()

        if not assets.exists():
            self.stdout.write(self.style.WARNING("No assets found in the database."))
            return

        self.stdout.write(f"Found {assets.count()} assets:\n")
        self.stdout.write("-" * 80)
        self.stdout.write(f"{'Asset ID':<20} | {'Manufacturer':<20} | {'Model':<20}")
        self.stdout.write("-" * 80)

        for asset in assets:
            self.stdout.write(
                f"{asset.unique_id:<20} | "
                f"{asset.manufacturer.name:<20} | "
                f"{asset.model:<20}"
            )

        self.stdout.write("-" * 80)