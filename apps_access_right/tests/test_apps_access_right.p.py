# -*- coding: utf-8 -*-
"""Tests for apps_access_right.

The module's whole point is that a Settings administrator who is NOT an
Apps manager cannot install, upgrade or uninstall applications. That
separation is what these tests lock: without them the module can install
cleanly and still be pointless.
"""
from odoo.exceptions import AccessError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestAppsAccessRight(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group_apps = cls.env.ref("apps_access_right.group_apps_manager")
        # A Settings user without the Apps group.
        cls.settings_only = (
            cls.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": "Settings Only",
                    "login": "settings_only_test",
                    "groups_id" if "groups_id" in cls.env["res.users"]._fields else "group_ids": [
                        (6, 0, [cls.env.ref("base.group_system").id])
                    ],
                }
            )
        )
        # A user who IS an Apps manager.
        cls.apps_manager = (
            cls.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": "Apps Manager",
                    "login": "apps_manager_test",
                    "groups_id" if "groups_id" in cls.env["res.users"]._fields else "group_ids": [
                        (6, 0, [cls.group_apps.id])
                    ],
                }
            )
        )

    def test_group_exists(self):
        """The Apps manager group is defined and implies Settings + User."""
        self.assertTrue(self.group_apps, "group_apps_manager must exist")
        implied = self.group_apps.implied_ids
        self.assertIn(
            self.env.ref("base.group_system"),
            implied,
            "Apps manager must imply base.group_system",
        )
        self.assertIn(
            self.env.ref("base.group_user"),
            implied,
            "Apps manager must imply base.group_user",
        )

    def test_is_apps_manager_compute(self):
        """is_apps_manager is True only for members of the Apps group."""
        module = self.env["ir.module.module"].search(
            [("name", "=", "apps_access_right")], limit=1
        )
        self.assertTrue(
            module.with_user(self.apps_manager).is_apps_manager,
            "an Apps manager must read is_apps_manager == True",
        )
        self.assertFalse(
            module.with_user(self.settings_only).is_apps_manager,
            "a Settings-only user must read is_apps_manager == False",
        )

    def test_settings_only_cannot_install(self):
        """A Settings user without the Apps group is refused on install."""
        module = self.env["ir.module.module"].search(
            [("state", "=", "uninstalled")], limit=1
        )
        if not module:
            self.skipTest("no uninstalled module available to attempt")
        with self.assertRaises(AccessError):
            module.with_user(self.settings_only).button_immediate_install()

    def test_settings_only_cannot_upgrade(self):
        """A Settings user without the Apps group is refused on upgrade."""
        module = self.env["ir.module.module"].search(
            [("name", "=", "apps_access_right")], limit=1
        )
        with self.assertRaises(AccessError):
            module.with_user(self.settings_only).button_immediate_upgrade()

    def test_settings_only_cannot_uninstall(self):
        """A Settings user without the Apps group is refused on uninstall."""
        module = self.env["ir.module.module"].search(
            [("name", "=", "auth_from_basic_http")], limit=1
        )
        if not module or module.state != "installed":
            self.skipTest("auth_from_basic_http is not installed")
        with self.assertRaises(AccessError):
            module.with_user(self.settings_only).button_immediate_uninstall()

    def test_menu_restricted_to_apps_group(self):
        """Both menus are restricted to the Apps group.

        The field is groups_id on 18.0 and group_ids from 19.0 - the test
        reads whichever the edition has, so it holds on all three.
        """
        field = (
            "group_ids"
            if "group_ids" in self.env["ir.ui.menu"]._fields
            else "groups_id"
        )
        for xmlid in ("base.menu_management", "base.menu_apps"):
            menu = self.env.ref(xmlid)
            groups = menu[field]
            self.assertIn(
                self.group_apps,
                groups,
                f"{xmlid} must be restricted to group_apps_manager",
            )
