from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.serializers import AuthTokenSerializer


class CustomAuthToken(APIView):
    # 1. Clear Authentication (Don't try to read headers)
    authentication_classes = []
    # 2. Clear Permissions (Don't check for keys/users)
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        print("DEBUG: Login View was hit!")  # <--- Check your console for this!

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