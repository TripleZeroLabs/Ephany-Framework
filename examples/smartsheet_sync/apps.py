from django.apps import AppConfig


class SmartsheetSyncConfig(AppConfig):
    """
    An example integration, not part of the core framework.

    Installing this app adds two management commands that import projects and
    snapshots from Smartsheet. Nothing in `assets`, `projects`, `access`, or
    `users` depends on it — remove it from INSTALLED_APPS and the rest of the
    framework is unaffected.

    It ships enabled so the commands show up in `manage.py help`, where people
    are most likely to find them and read the code.
    """
    name = "examples.smartsheet_sync"
    label = "smartsheet_sync"
    verbose_name = "Example: Smartsheet Sync"
