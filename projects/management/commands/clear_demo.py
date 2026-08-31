"""
Remove the demo dataset, leaving everything else alone.

The counterpart to `seed_demo`. Useful once you have finished exploring and
want your own records on a clean board, without dropping the database and
losing them too.

Safety is the whole point of this command, so it is worth knowing what it will
not do. The naive teardown - delete everything whose name matches the demo
lists - destroys user data, because `Asset.manufacturer` is a CASCADE foreign
key: removing the demo manufacturer "Aurora Systems" would take any asset you
built on it with it, without a word.

So shared records - manufacturers, categories, vendors, attributes - are
reference counted, and kept if anything outside the demo still points at them.
Whatever is kept is reported, with the reason.

Usage:
    python manage.py clear_demo --dry-run   # show what would happen
    python manage.py clear_demo
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from projects.demo_data import clear_demo_data


class Command(BaseCommand):
    help = (
        "Remove the seed_demo dataset. Records you created are kept, including "
        "shared manufacturers and categories that your own assets rely on."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would be removed and kept, then roll back.",
        )

    def say(self, message="", style=None):
        """Write unless the caller asked for silence (verbosity 0)."""
        if self.verbosity:
            self.stdout.write(style(message) if style else message)

    def handle(self, *args, **options):
        self.verbosity = options["verbosity"]
        dry_run = options["dry_run"]

        if dry_run:
            self.say("DRY RUN - nothing will be deleted.\n", self.style.WARNING)

        # The dry run does the real work inside a transaction and rolls it
        # back, so the report reflects what would actually happen rather than a
        # separate guess that could disagree with it.
        try:
            with transaction.atomic():
                deleted, kept = clear_demo_data()
                if dry_run:
                    raise _Rollback(deleted, kept)
        except _Rollback as rollback:
            deleted, kept = rollback.deleted, rollback.kept

        if not deleted and not kept:
            self.say("No demo data found. Nothing to do.")
            return

        if deleted:
            verb = "Would remove" if dry_run else "Removed"
            self.say(f"{verb}:", self.style.SUCCESS)
            for label, count in sorted(deleted.items()):
                self.say(f"  {count:>6}  {label}")

        if kept:
            self.say("\nKept, because your data depends on them:", self.style.WARNING)
            for reason in kept:
                self.say(f"  {reason}")

        if dry_run:
            self.say("\nDRY RUN - nothing was deleted.", self.style.WARNING)


class _Rollback(Exception):
    """Aborts the transaction after a dry run, carrying the report out with it."""

    def __init__(self, deleted, kept):
        super().__init__("dry run")
        self.deleted = deleted
        self.kept = kept
