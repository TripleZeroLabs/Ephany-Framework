from django.apps import AppConfig


class AccessConfig(AppConfig):
    name = 'access'

    def ready(self):
        # Both modules register things as a side effect of import: the system
        # checks below, and the drf-spectacular auth extension. Neither is
        # referenced by name anywhere else, so without these imports they are
        # silently inert.
        from . import checks  # noqa: F401
        from . import schema  # noqa: F401
