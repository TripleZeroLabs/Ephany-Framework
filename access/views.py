from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.serializers import AuthTokenSerializer

from .serializers import AuthTokenResponseSerializer


@extend_schema(
    tags=["access"],
    summary="Exchange username and password for an auth token",
    description=(
        '''Returns a DRF auth token for the given credentials. Send it on
subsequent requests as "Authorization: Token <token>".

This endpoint declares AllowAny, so it stays reachable without credentials
even when anonymous access to the rest of the API is closed.'''
    ),
    request=AuthTokenSerializer,
    responses={200: AuthTokenResponseSerializer},
    auth=[],
)
class CustomAuthToken(APIView):
    # 1. Clear Authentication (Don't try to read headers)
    authentication_classes = []
    # 2. Clear Permissions (Don't check for keys/users)
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        # Use the standard serializer to validate user/pass
        serializer = AuthTokenSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)

        return Response({
            'token': token.key,
            'user_id': user.pk,
            'email': user.email
        })