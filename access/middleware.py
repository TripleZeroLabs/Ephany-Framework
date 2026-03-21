from django.conf import settings
from django.http import JsonResponse

from .models import APIClient


class APIKeyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def _path_is_protected(self, path: str) -> bool:
        """Check if the current path requires authentication."""
        prefixes = getattr(settings, "API_KEY_PROTECTED_PREFIXES", ["/api/"])
        return any(path.startswith(prefix) for prefix in prefixes)

    def _path_is_exempt(self, path: str) -> bool:
        """Check if the path is explicitly allowed to bypass authentication checks."""
        exempt_paths = getattr(settings, "API_KEY_EXEMPT_PATHS", [])
        return path in exempt_paths

    def __call__(self, request):
        # 1. Bypass if the entire feature is disabled
        if not getattr(settings, "API_KEY_AUTH_ENABLED", False):
            return self.get_response(request)

        # 2. Bypass CORS preflight requests — browsers send OPTIONS with no auth headers
        if request.method == "OPTIONS":
            return self.get_response(request)

        # 3. Bypass if path is not in a protected zone (e.g., admin/, static/)
        if not self._path_is_protected(request.path):
            return self.get_response(request)

        # 3. Bypass if path is explicitly exempt (e.g., login endpoints)
        if self._path_is_exempt(request.path):
            return self.get_response(request)

        # 4. Bypass if using Standard User Authentication (Tokens/Session)
        # If the user provides an 'Authorization' header (for DRF Tokens),
        # we step aside and let DRF's authentication classes handle it.
        if "Authorization" in request.headers:
            return self.get_response(request)

        # 5. API Key Validation Logic
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

        # Attach client info for downstream usage
        request.api_client = client

        return self.get_response(request)