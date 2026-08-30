"""
Tests for the API's single authentication and authorization layer.

Most of these exist because the behavior they assert was once broken. Auth
config fails silently — a request that should have been refused just succeeds,
and a client that should work just gets a 401 — so every combination of
credential and setting is pinned here explicitly rather than spot-checked.

The three regressions that motivated this file, all caused by an API key
middleware that decided access before DRF's own layer could:

  * a valid API key was rejected whenever the middleware was switched off
  * a logged-in session was rejected whenever it was switched on
  * anonymous callers were rejected in development, contradicting the README
"""

from django.contrib.auth import get_user_model
from django.core.checks import Warning as CheckWarning
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.authtoken.models import Token

from access.checks import (
    anonymous_access_in_production,
    removed_api_key_auth_enabled_setting,
)
from access.models import APIClient

User = get_user_model()

# Any DRF route governed by the default permission class works as the probe.
API_URL = "/api/assets/"

CLOSED = {"API_ALLOW_ANONYMOUS": False}
OPEN = {"API_ALLOW_ANONYMOUS": True}


class AuthMatrixTests(TestCase):
    """Every credential type, against both anonymous-access settings."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="tester", password="pw-12345")
        cls.token = Token.objects.create(user=cls.user)
        cls.client_key = APIClient.objects.create(name="test-key")
        cls.inactive_key = APIClient.objects.create(name="revoked-key", is_active=False)

    # -- With anonymous access closed (the deployment default) ---------------

    @override_settings(**CLOSED)
    def test_anonymous_is_refused_when_closed(self):
        self.assertEqual(self.client.get(API_URL).status_code, 401)

    @override_settings(**CLOSED)
    def test_session_is_accepted_when_closed(self):
        """The browsable API and any cookie-authenticated frontend.

        This returned 401 before the refactor: the middleware only stepped
        aside for an Authorization header, so a session cookie never reached
        DRF's SessionAuthentication at all.
        """
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(API_URL).status_code, 200)

    @override_settings(**CLOSED)
    def test_token_is_accepted_when_closed(self):
        response = self.client.get(
            API_URL, headers={"authorization": f"Token {self.token.key}"}
        )
        self.assertEqual(response.status_code, 200)

    @override_settings(**CLOSED)
    def test_api_key_is_accepted_when_closed(self):
        response = self.client.get(API_URL, headers={"x-api-key": self.client_key.key})
        self.assertEqual(response.status_code, 200)

    # -- With anonymous access open (the development default) ----------------

    @override_settings(**OPEN)
    def test_anonymous_is_accepted_when_open(self):
        """The README's headline curl example, on a fresh clone.

        This returned 401 before the refactor, because the permission class
        never consulted the setting that was supposed to control it.
        """
        self.assertEqual(self.client.get(API_URL).status_code, 200)

    @override_settings(**OPEN)
    def test_api_key_still_works_when_open(self):
        """Opening the API must not break clients that do send a key.

        The inverse case was the sharpest of the original bugs: switching the
        old flag off caused valid keys to be rejected, so the setting people
        reached for to *loosen* access silently broke their integrations.
        """
        response = self.client.get(API_URL, headers={"x-api-key": self.client_key.key})
        self.assertEqual(response.status_code, 200)

    @override_settings(**OPEN)
    def test_bad_api_key_is_refused_even_when_open(self):
        """A wrong credential is an error, not a fallback to anonymous.

        Silently downgrading a bad key to anonymous access would turn a typo
        into a request that appears to work while carrying no identity.
        """
        response = self.client.get(API_URL, headers={"x-api-key": "not-a-real-key"})
        self.assertEqual(response.status_code, 403)


class APIKeyAuthenticationTests(TestCase):
    """Behavior specific to the X-API-Key credential."""

    @classmethod
    def setUpTestData(cls):
        cls.active = APIClient.objects.create(name="active")
        cls.inactive = APIClient.objects.create(name="inactive", is_active=False)

    @override_settings(**CLOSED)
    def test_missing_key_is_401_and_bad_key_is_403(self):
        """The distinction the README documents: absent vs. invalid.

        It tells a caller whether to add a credential or fix the one they
        have, so it is preserved deliberately rather than collapsed into 401.
        """
        self.assertEqual(self.client.get(API_URL).status_code, 401)
        self.assertEqual(
            self.client.get(API_URL, headers={"x-api-key": "wrong"}).status_code, 403
        )

    @override_settings(**CLOSED)
    def test_inactive_key_is_refused(self):
        response = self.client.get(API_URL, headers={"x-api-key": self.inactive.key})
        self.assertEqual(response.status_code, 403)

    @override_settings(**CLOSED)
    def test_key_is_not_accepted_from_the_query_string(self):
        """Keys must travel in a header, never a URL.

        The old middleware also accepted ?api_key=, which leaks the credential
        into access logs, browser history, and Referer headers.
        """
        response = self.client.get(f"{API_URL}?api_key={self.active.key}")
        self.assertEqual(response.status_code, 401)

    @override_settings(**CLOSED)
    def test_api_key_caller_has_no_django_user(self):
        """A key identifies an integration, not a person.

        Permission checks must therefore read request.auth; anything relying on
        request.user.is_authenticated will correctly see an anonymous caller.
        """
        from rest_framework.test import APIRequestFactory

        from access.authentication import APIKeyAuthentication

        request = APIRequestFactory().get(API_URL, headers={"x-api-key": self.active.key})
        user, auth = APIKeyAuthentication().authenticate(request)

        self.assertFalse(user.is_authenticated)
        self.assertEqual(auth, self.active)

    def test_declines_when_no_key_present(self):
        """Returning None is what lets session and token auth still run."""
        from rest_framework.test import APIRequestFactory

        from access.authentication import APIKeyAuthentication

        request = APIRequestFactory().get(API_URL)
        self.assertIsNone(APIKeyAuthentication().authenticate(request))


class PublicRouteTests(TestCase):
    """Routes that must stay reachable with anonymous access closed."""

    @override_settings(**CLOSED)
    def test_schema_and_docs_are_public(self):
        for name in ("schema", "swagger-ui", "redoc"):
            with self.subTest(route=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)

    @override_settings(**CLOSED)
    def test_login_is_reachable_and_returns_a_token(self):
        user = User.objects.create_user(username="login-tester", password="pw-12345")
        response = self.client.post(
            reverse("api_token_auth"),
            {"username": "login-tester", "password": "pw-12345"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["token"], Token.objects.get(user=user).key)

    @override_settings(**CLOSED)
    def test_login_rejects_bad_credentials(self):
        User.objects.create_user(username="login-tester", password="pw-12345")
        response = self.client.post(
            reverse("api_token_auth"),
            {"username": "login-tester", "password": "wrong"},
        )
        self.assertEqual(response.status_code, 400)


class DeploymentCheckTests(TestCase):
    """The system checks that make a dangerous config visible."""

    @override_settings(API_ALLOW_ANONYMOUS=True, DEBUG=False)
    def test_warns_when_api_is_public_outside_debug(self):
        warnings = anonymous_access_in_production(None)
        self.assertEqual([w.id for w in warnings], ["access.W001"])
        self.assertIsInstance(warnings[0], CheckWarning)

    @override_settings(API_ALLOW_ANONYMOUS=True, DEBUG=True)
    def test_silent_when_open_in_development(self):
        self.assertEqual(anonymous_access_in_production(None), [])

    @override_settings(API_ALLOW_ANONYMOUS=False, DEBUG=False)
    def test_silent_when_closed_in_production(self):
        self.assertEqual(anonymous_access_in_production(None), [])

    @override_settings(API_KEY_AUTH_ENABLED=True)
    def test_warns_that_the_old_setting_is_ignored(self):
        """Silence here would let someone trust a setting that does nothing."""
        warnings = removed_api_key_auth_enabled_setting(None)
        self.assertEqual([w.id for w in warnings], ["access.W002"])

    def test_silent_when_old_setting_is_absent(self):
        self.assertEqual(removed_api_key_auth_enabled_setting(None), [])
