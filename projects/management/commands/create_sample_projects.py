from django.core.management.base import BaseCommand
from projects.models import Project, Snapshot
from django.utils import timezone
import datetime

class Command(BaseCommand):
    help = 'Creates 5 sample retail construction projects with snapshots'

    def handle(self, *args, **kwargs):
        locations = [
            ("NYC-001", "Flagship Store - 5th Ave"),
            ("CHI-002", "Downtown Chicago Boutique"),
            ("LA-003", "Santa Monica Promenade"),
            ("MIA-004", "Miami Design District"),
            ("AUS-005", "Austin Domain Store"),
        ]

        phases = [
            "Phase 1: Demolition & Prep",
            "Phase 2: Rough-in & Framing",
            "Phase 3: Finishes & Fixtures"
        ]

        for unique_id, name in locations:
            # Create Project
            project, created = Project.objects.get_or_create(
                unique_id=unique_id,
                defaults={
                    'name': name,
                    'description': f"Construction project for {name}"
                }
            )

            if created:
                self.stdout.write(self.style.SUCCESS(f"Created Project: {name}"))
            else:
                self.stdout.write(f"Project already exists: {name}")

            # Create Snapshots
            for i, phase in enumerate(phases):
                # Stagger dates slightly for realism
                snapshot_date = timezone.now() + datetime.timedelta(days=i*30)

                snap, snap_created = Snapshot.objects.get_or_create(
                    project=project,
                    name=phase,
                    defaults={'date': snapshot_date}
                )
                if snap_created:
                    self.stdout.write(f"  - Created Snapshot: {phase}")