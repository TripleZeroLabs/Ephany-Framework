from django.conf import settings
from django.http import JsonResponse

from .models import APIClient


class APIKeyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def _path_is_protected(self, path: str) -> bool:
        prefixes = getattr(settings, "API_KEY_PROTECTED_PREFIXES", ["/api/"])
        return any(path.startswith(prefix) for prefix in prefixes)

    def __call__(self, request):
        # If feature is disabled, do nothing
        if not getattr(settings, "API_KEY_AUTH_ENABLED", False):
            return self.get_response(request)

        # Only protect configured prefixes
        if not self._path_is_protected(request.path):
            return self.get_response(request)

        # Get key from header or query string
        key = (
            request.headers.get("X-API-Key")
            or request.META.get("HTTP_X_API_KEY")
            or request.GET.get("api_key")
        )

        if not key:
            return JsonResponse({"detail": "API key required."}, status=401)

        try:
            client = APIClient.objects.get(key=key, is_active=True)
        except APIClient.DoesNotExist:
            return JsonResponse(
                {"detail": "Invalid or inactive API key."},
                status=403,
            )

        # Attach for downstream use (logging, rate limiting, etc.)
        request.api_client = client

        return self.get_response(request)
