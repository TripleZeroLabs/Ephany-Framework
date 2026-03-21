from django.core.management.base import BaseCommand
from access.models import APIClient


class Command(BaseCommand):
    help = "Create an API key for a client"

    def add_arguments(self, parser):
        parser.add_argument("name", type=str, help="Name for this API client")

    def handle(self, *args, **options):
        name = options["name"]
        client = APIClient.objects.create(name=name)
        self.stdout.write(self.style.SUCCESS(f"Created API client '{name}'"))
        self.stdout.write(self.style.WARNING("API key (store this somewhere safe):"))
        self.stdout.write(client.key)
