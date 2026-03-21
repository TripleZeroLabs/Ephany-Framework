from rest_framework import permissions


class HasAPIKeyOrAuthenticated(permissions.BasePermission):
    """
    Custom permission to allow access if the user is authenticated (Session/Token)
    OR if the request has a valid API Key validated by middleware.
    """

    def has_permission(self, request, view):
        # Allow if standard Django User is logged in (e.g. Revit Plugin)
        if request.user and request.user.is_authenticated:
            return True

        # Allow if API Key was validated by our Custom Middleware (e.g. Console App)
        # The middleware sets 'api_client' on the request object.
        if getattr(request, 'api_client', None) is not None:
            return True

        return False