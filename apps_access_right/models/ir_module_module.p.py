# -*- coding: utf-8 -*-
# models/res_users.py

from odoo import models, api, fields, _
from odoo.exceptions import AccessError


class IrModuleModule(models.Model):
    _inherit = 'ir.module.module'

    is_apps_manager = fields.Boolean(compute='_compute_is_apps_manager')

    @api.depends_context('uid')
    def _compute_is_apps_manager(self):
        for record in self:
            record.is_apps_manager = self.env.user.has_group('apps_access_right.group_apps_manager')

    def button_immediate_install(self):
        if not self.env.su and not self.env.user.has_group('apps_access_right.group_apps_manager'):
            raise AccessError(_(
                'You do not have permission to install applications. '
                'This action requires Apps Manager rights.'
            ))
        return super(IrModuleModule, self).button_immediate_install()

    def button_immediate_upgrade(self):
        if not self.env.su and not self.env.user.has_group('apps_access_right.group_apps_manager'):
            raise AccessError(_(
                'You do not have permission to upgrade applications. '
                'This action requires Apps Manager rights.'
            ))
        return super(IrModuleModule, self).button_immediate_upgrade()

    def button_immediate_uninstall(self):
        if not self.env.su and not self.env.user.has_group('apps_access_right.group_apps_manager'):
            raise AccessError(_(
                'You do not have permission to uninstall applications. '
                'This action requires Apps Manager rights.'
            ))
        return super(IrModuleModule, self).button_immediate_uninstall()