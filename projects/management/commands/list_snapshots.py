from django.core.management.base import BaseCommand
from projects.models import Snapshot

class Command(BaseCommand):
    help = 'Lists all snapshots'

    def handle(self, *args, **kwargs):
        snapshots = Snapshot.objects.select_related('project').all().order_by('project__unique_id', 'date')

        self.stdout.write(f"Total Snapshots: {snapshots.count()}\n")
        self.stdout.write("-" * 80)
        self.stdout.write(f"{'Project':<20} | {'Snapshot Name':<30} | {'Date'}")
        self.stdout.write("-" * 80)

        for s in snapshots:
            self.stdout.write(
                f"{s.project.unique_id:<20} | {s.name:<30} | {s.date.strftime('%Y-%m-%d')}"
            )