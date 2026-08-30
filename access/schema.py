"""
Teaches drf-spectacular about API key authentication.

Registering the extension here means the X-API-Key scheme is derived from the
authentication class itself, so the schema cannot drift from the code. It
previously had to be hand-declared in SPECTACULAR_SETTINGS, because the key was
checked by middleware that drf-spectacular had no way to see.
"""

from drf_spectacular.extensions import OpenApiAuthenticationExtension

from .authentication import API_KEY_HEADER


class APIKeyAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = "access.authentication.APIKeyAuthentication"
    name = "ApiKeyAuth"

    def get_security_definition(self, auto_schema):
        return {
            "type": "apiKey",
            "in": "header",
            "name": API_KEY_HEADER,
            "description": (
                "Identifies a machine client (a plugin, a CLI, a frontend "
                "build) rather than a person. Create one with: "
                "python manage.py create_apikey \"Local Dev\""
            ),
        }
