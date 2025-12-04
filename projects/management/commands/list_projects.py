from django.core.management.base import BaseCommand
from projects.models import Project

class Command(BaseCommand):
    help = 'Lists all projects'

    def handle(self, *args, **kwargs):
        projects = Project.objects.all()

        self.stdout.write(f"Total Projects: {projects.count()}\n")
        self.stdout.write("-" * 60)
        self.stdout.write(f"{'ID':<15} | {'Name':<40}")
        self.stdout.write("-" * 60)

        for p in projects:
            self.stdout.write(f"{p.unique_id:<15} | {p.name:<40}")