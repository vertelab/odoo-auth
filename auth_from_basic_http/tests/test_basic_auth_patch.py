# -*- coding: utf-8 -*-
"""Tests for auth_from_basic_http.

The module works by patching Odoo's session setup. If the patch point
disappears (it moved between 19.0 and 20.0) the module still imports and
still installs - it just stops doing anything. That is the failure these
tests are here to catch.
"""
import base64

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestBasicAuthPatch(TransactionCase):
    def test_patch_is_installed(self):
        """The session-setup patch is in place for this edition.

        On 18.0/19.0 the patch point is Request._get_session_and_dbname; on
        20.0 it is router._set_session_and_dbname. Whichever exists must be
        the module's own function, not the original.
        """
        from odoo.http import Request

        patched = getattr(Request, "_get_session_and_dbname", None)
        if patched is not None:
            self.assertEqual(
                patched.__name__,
                "_patched_set_session_and_dbname",
                "18.0/19.0: Request._get_session_and_dbname must be patched",
            )
            return

        from odoo.http import router

        self.assertTrue(
            hasattr(router, "_set_session_and_dbname"),
            "20.0: router._set_session_and_dbname must exist",
        )
        self.assertEqual(
            router._set_session_and_dbname.__name__,
            "_patched_set_session_and_dbname",
            "20.0: router._set_session_and_dbname must be patched",
        )

    def test_helper_functions_are_callable(self):
        """The module's public helpers import and are callable."""
        from odoo.addons.auth_from_basic_http import (
            domain_requires_basic_auth,
            get_basic_auth_credentials,
            send_auth_challenge,
        )

        self.assertTrue(callable(domain_requires_basic_auth))
        self.assertTrue(callable(get_basic_auth_credentials))
        self.assertTrue(callable(send_auth_challenge))

    def test_domain_match_exact_and_wildcard(self):
        """domain_requires_basic_auth() matches exactly and by wildcard."""
        from unittest.mock import patch

        from odoo.addons.auth_from_basic_http import domain_requires_basic_auth

        class FakeRequest:
            class httprequest:
                host = "app.example.com"

        cases = [
            ("", False, "no domains configured -> no basic auth"),
            ("app.example.com", True, "exact match"),
            ("*.example.com", True, "wildcard matches subdomain"),
            ("example.com", False, "bare domain is not a subdomain match"),
            ("other.example.com", False, "different subdomain -> no match"),
        ]
        for configured, expected, label in cases:
            with patch(
                "odoo.addons.auth_from_basic_http.config.get",
                return_value=configured,
            ), patch("odoo.addons.auth_from_basic_http.request", FakeRequest, create=True):
                self.assertEqual(
                    domain_requires_basic_auth(),
                    expected,
                    f"{label} (configured={configured!r})",
                )

    def test_credentials_parsed_from_header(self):
        """get_basic_auth_credentials() decodes user:password."""
        from unittest.mock import patch

        from odoo.addons.auth_from_basic_http import get_basic_auth_credentials

        token = base64.b64encode(b"alice:s3cret").decode()

        class FakeRequest:
            class httprequest:
                headers = {"Authorization": f"Basic {token}"}

        with patch("odoo.addons.auth_from_basic_http.request", FakeRequest, create=True):
            user, password = get_basic_auth_credentials()
        self.assertEqual((user, password), ("alice", "s3cret"))

    def test_credentials_absent_or_malformed(self):
        """No header, wrong scheme or broken base64 give (None, None)."""
        from unittest.mock import patch

        from odoo.addons.auth_from_basic_http import get_basic_auth_credentials

        for header in ("", "Bearer abc", "Basic !!!notbase64!!!"):
            class FakeRequest:
                class httprequest:
                    headers = {"Authorization": header} if header else {}

            with patch(
                "odoo.addons.auth_from_basic_http.request", FakeRequest, create=True
            ):
                self.assertEqual(
                    get_basic_auth_credentials(),
                    (None, None),
                    f"header={header!r} must not yield credentials",
                )

    def test_challenge_is_401(self):
        """send_auth_challenge() returns a 401 with a Basic realm."""
        from odoo.addons.auth_from_basic_http import send_auth_challenge

        response = send_auth_challenge()
        self.assertEqual(response.status_code, 401)
        self.assertIn("Basic realm=", response.headers.get("WWW-Authenticate", ""))
