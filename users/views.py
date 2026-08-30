from django.shortcuts import render
from rest_framework import viewsets, permissions
from django.contrib.auth.models import User
from .serializers import UserSerializer

class UserViewSet(viewsets.ModelViewSet):
    # Django's own User model has no Meta.ordering; set one here so
    # pagination is stable.
    queryset = User.objects.all().order_by('id')
    serializer_class = UserSerializer
    # Typically, you want to restrict user management to admins or the user themselves
    # For now, we'll default to IsAuthenticated, but you might want IsAdminUser for listing all
    permission_classes = [permissions.IsAuthenticated] 

    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        if self.action == 'create':
            # Allow anyone to register (POST)
            permission_classes = [permissions.AllowAny]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]
