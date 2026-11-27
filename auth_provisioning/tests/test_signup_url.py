# -*- coding: utf-8 -*-
"""Tests for auth_provisioning.

Locks the behaviour the capability signup-url-visibility describes: the
signup_url field is computed for a user, so an administrator can read and
copy the invitation/reset link. Also locks the edition differences that
made the module uninstallable on 20.0 (BinaryValue, get_str).
"""
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestSignupUrl(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = (
            cls.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": "Provisioning Test",
                    "login": "provisioning_test_user",
                    "email": "provisioning_test_user@example.com",
                }
            )
        )

    def test_signup_url_is_computed(self):
        """signup_url is a non-empty link for a user with a partner."""
        self.assertTrue(
            self.user.partner_id,
            "the test user must have a partner for signup_url to compute",
        )
        self.assertTrue(
            self.user.signup_url,
            "signup_url must be computed for a user with a partner",
        )
        # partner._get_signup_url() returns the login link carrying the
        # token; the exact path differs between editions and is not the
        # contract. The contract is: a link the administrator can copy.
        self.assertIn(
            "/web/",
            self.user.signup_url,
            "signup_url must be an Odoo web link",
        )

    def test_base_url_parameter_is_read(self):
        """set_base_url reads web.base.url, not a missing parameter.

        On 20.0 get_param was removed; the module uses get_str. If the
        wrong accessor is used the field falls back to the error string.
        """
        self.env["ir.config_parameter"].sudo().set_param(
            "web.base.url", "https://example.test"
        )
        self.assertEqual(
            self.user.base_url_parameter,
            "https://example.test",
            "base_url_parameter must read web.base.url",
        )

    def test_qrcode_is_produced(self):
        """The QR code field is populated and renders without error.

        On 20.0 the field holds a BinaryValue; on 18.0/19.0 base64 text.
        Reading it back must not raise on any edition.
        """
        self.assertTrue(
            self.user.qrcode_signup_url,
            "qrcode_signup_url must be computed",
        )

    def test_qrcode_data_string_on_20(self):
        """From 20.0 the module also exposes a ready data: string for QWeb.

        QWeb has neither base64 nor __import__, so the template cannot
        encode the BinaryValue itself - the module must.
        """
        if "qrcode_signup_data" not in self.env["res.users"]._fields:
            self.skipTest("qrcode_signup_data exists from 20.0 only")
        data = self.user.qrcode_signup_data
        self.assertTrue(data, "qrcode_signup_data must be computed")
        self.assertTrue(
            data.startswith("data:image/png;base64,"),
            f"qrcode_signup_data must be a data: URL, got {data[:40]!r}",
        )

    def test_invite_template_renders(self):
        """The overridden set_password_email template renders for a user.

        This is the check that caught the get_param/get_int break on 20.0:
        the template is rendered at install time, and a dead accessor takes
        the whole installation down.
        """
        template = self.env.ref("auth_signup.set_password_email")
        # Render through the ORM record so QWeb evaluates `object` - the
        # point is that the overridden body renders at all, which is what
        # broke on 20.0 when get_param disappeared.
        rendered = template._render_template(
            template.body_html, "res.users", [self.user.id]
        )
        body = rendered[self.user.id]
        self.assertTrue(body, "the invitation template must render")
        self.assertIn(
            "Accept invitation",
            body,
            "the rendered invitation must keep its signup button",
        )
