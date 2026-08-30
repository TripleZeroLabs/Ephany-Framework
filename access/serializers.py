from rest_framework import serializers


class AuthTokenResponseSerializer(serializers.Serializer):
    """
    Shape of a successful POST /api/login/ response.

    Documentation only — the view builds this payload directly. It exists so
    the OpenAPI schema describes the login response instead of reporting
    "no response body".
    """
    token = serializers.CharField(
        help_text='Send as "Authorization: Token <token>" on subsequent requests.'
    )
    user_id = serializers.IntegerField()
    email = serializers.EmailField()
