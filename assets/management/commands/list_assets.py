from django.core.management.base import BaseCommand
from assets.models import Asset


class Command(BaseCommand):
    help = 'Lists all assets'

    def handle(self, *args, **kwargs):
        assets = Asset.objects.all()
        for asset in assets:
            self.stdout.write(f"{asset.unique_id}: {asset.manufacturer.name} - {asset.model}")
            
            files = asset.files.all()
            if files:
                self.stdout.write("  Files:")
                for f in files:
                    self.stdout.write(f"    - [{f.get_category_display()}] {f.file.name}")
            else:
                self.stdout.write("  (No files attached)")
            
            self.stdout.write("-" * 40)