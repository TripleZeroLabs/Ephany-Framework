"""
API key authentication.

This is the single place a request's identity is established. It replaces an
earlier middleware that did the same lookup but returned 401/403 itself, which
made it an *authorization* layer sitting in front of DRF's own. Two layers each
deciding half the question is what produced three separate bugs: valid API keys
rejected, logged-in sessions rejected, and anonymous callers rejected against
the documented behavior. See access/tests.py, which pins down every case.

The rule that makes composition work is `return None`: an authenticator that
does not recognise a request declines, and DRF moves to the next one. Middleware
cannot decline — it can only allow or reject — which is why the old one had to
guess (badly) whether a request "looked like" a session request.
"""

from django.contrib.auth.models import AnonymousUser
from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication

from .models import APIClient

API_KEY_HEADER = "X-API-Key"


class APIKeyAuthentication(BaseAuthentication):
    """
    Authenticate a machine client via the `X-API-Key` header.

    Returns `(AnonymousUser, APIClient)`. There is no Django user behind an API
    key by design: keys identify an integration (a Revit plugin, a CLI, a
    frontend build), not a person. Permission checks therefore look at
    `request.auth` rather than `request.user`.

    Because the returned user is anonymous, `IsAuthenticated` will still reject
    an API key caller. That is intentional — use `HasAPIKeyOrAuthenticated`
    (the project default) for views that machine clients should reach.

    If you later need per-key permissions or write attribution, add a nullable
    `user` FK to APIClient and return that user here instead. Nothing else in
    this file would change.
    """

    # Reported in the WWW-Authenticate header of a 401, and what makes DRF
    # answer 401 rather than 403 when no authenticator recognised the request.
    keyword = API_KEY_HEADER

    def authenticate(self, request):
        key = request.headers.get(API_KEY_HEADER)

        # No key present: decline, so session and token auth get their turn.
        # This is the line the old middleware could not express.
        if not key:
            return None

        try:
            client = APIClient.objects.get(key=key, is_active=True)
        except APIClient.DoesNotExist:
            # 403, not 401, to preserve the contract the README has always
            # documented: a *missing* credential is 401, a *bad* one is 403.
            # Strict HTTP semantics would say 401 for both, but the split tells
            # a caller whether to add a key or fix the one they have, and
            # breaking it would silently change behavior for existing clients.
            raise exceptions.PermissionDenied("Invalid or inactive API key.")

        return (AnonymousUser(), client)

    def authenticate_header(self, request):
        return self.keyword
