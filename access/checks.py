"""
Deployment checks for the API's auth configuration.

W002 runs on every `manage.py` command, because a setting that silently stopped
working should surface the next time you touch the project.

W001 is registered as a deploy check, so it runs under `manage.py check
--deploy`. Make that part of your release step.
"""

import os

from django.conf import settings
from django.core.checks import Tags, Warning as CheckWarning, register


# deploy=True so this runs under `manage.py check --deploy` rather than on
# every command. The test runner forces DEBUG=False, so an always-on version
# would fire on every test run of a perfectly fine development config, and a
# check that cries wolf is a check people learn to skip.
@register(Tags.security, deploy=True)
def anonymous_access_in_production(app_configs, **kwargs):
    """
    Warn when the API is open to the world outside development.

    API_ALLOW_ANONYMOUS defaults to DEBUG, so hitting this means someone set it
    explicitly. That is a legitimate choice for a genuinely public read API —
    hence a warning rather than an error — but it should never be a surprise.

    Run `python manage.py check --deploy` before deploying.
    """
    if getattr(settings, "API_ALLOW_ANONYMOUS", False) and not settings.DEBUG:
        return [
            CheckWarning(
                "The API is readable and writable without any credentials.",
                hint=(
                    "API_ALLOW_ANONYMOUS is on while DEBUG is off, so every "
                    "/api/ route is open to anyone who can reach this server. "
                    "Unset API_ALLOW_ANONYMOUS to require a credential. If a "
                    "public API is what you want, silence this with "
                    "SILENCED_SYSTEM_CHECKS = ['access.W001']."
                ),
                id="access.W001",
            )
        ]
    return []


@register()
def removed_api_key_auth_enabled_setting(app_configs, **kwargs):
    """
    Tell anyone still setting API_KEY_AUTH_ENABLED that it no longer does
    anything, and what replaced it.

    The old flag gated the API key *middleware*. With authentication unified
    into a DRF authentication class, API keys are always accepted, and the only
    remaining question — may anonymous callers in? — is API_ALLOW_ANONYMOUS.
    Failing silently here would leave someone believing their API is locked
    down by a setting that is no longer read.
    """
    if "API_KEY_AUTH_ENABLED" in os.environ or hasattr(settings, "API_KEY_AUTH_ENABLED"):
        return [
            CheckWarning(
                "API_KEY_AUTH_ENABLED is set but no longer has any effect.",
                hint=(
                    "API keys are now always accepted via the X-API-Key "
                    "header. Anonymous access is controlled by "
                    "API_ALLOW_ANONYMOUS, which defaults to DEBUG. Remove "
                    "API_KEY_AUTH_ENABLED from your environment and .env."
                ),
                id="access.W002",
            )
        ]
    return []
