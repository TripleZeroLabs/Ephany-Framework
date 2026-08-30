"""
The project-wide default permission.

Authentication (who is calling) happens in access/authentication.py and DRF's
built-in classes. This file answers the separate question of whether that
caller may proceed. Keeping the two apart is what lets session, token, and API
key credentials compose instead of competing.
"""

from django.conf import settings
from rest_framework import permissions

from .models import APIClient


class HasAPIKeyOrAuthenticated(permissions.BasePermission):
    """
    Allow a request that carries any valid credential.

    Three ways to pass:

      1. A logged-in Django user — session cookie (the browsable API and the
         admin) or a DRF token in an `Authorization: Token <key>` header.
      2. A valid `X-API-Key` header, resolved to an APIClient by
         APIKeyAuthentication.
      3. Nothing at all, when API_ALLOW_ANONYMOUS is on.

    API_ALLOW_ANONYMOUS defaults to DEBUG, so a fresh clone is browsable
    immediately and a deployment with DEBUG=False is closed by default. Tying
    it to DEBUG rather than to a standalone flag means the open case cannot be
    reached by *forgetting* to set something — you have to have DEBUG on, which
    is already unsafe for other reasons. Setting it explicitly is still
    supported for a genuinely public API; access.checks warns when that is
    combined with DEBUG=False so the choice is visible rather than accidental.
    """

    def has_permission(self, request, view):
        if getattr(settings, "API_ALLOW_ANONYMOUS", False):
            return True

        # Session or token auth: a real Django user is behind this request.
        if request.user and request.user.is_authenticated:
            return True

        # API key auth: no user, but a known integration. APIKeyAuthentication
        # only ever puts an active APIClient here, so reaching this line means
        # the key was present and valid.
        return isinstance(request.auth, APIClient)
