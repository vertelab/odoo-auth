from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import re


def validate_personnummer(ssnid):
    control_digit = int(ssnid[-1])
    tot = 0
    multiplicator = 2
    for digit in ssnid[:-1]:
        res = int(digit) * multiplicator
        if res > 9:
            res = 1 + res % 10
        tot += res
        multiplicator = (multiplicator % 2) + 1
    return (10 - (tot % 10)) % 10 == control_digit


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    def _get_employee_groups(self):
        if self.user_id:
            user_groups = self.env['res.groups'].sudo().search([('users', 'in', self.user_id.id),
                                                                ('name', 'ilike', 'DAFA')])
            return user_groups.ids
        else:
            return False

    user_groups = fields.Many2many('res.groups', string="User Groups", domain=[('is_dafa', '=', 'True')],
                                   default=_get_employee_groups)

    @api.model
    def create(self, vals):
        res = super(HrEmployee, self).create(vals)
        if res.user_groups:
            res.update_group()
        return res

    def _create_user(self):
        new_user_id = self.env['res.users'].sudo().create({
            'name': self.name,
            'login': self.work_email,
            'email': self.work_email,
            "notification_type": "email",
            'saml_provider_id': self.env.ref('auth_saml_dafa.provider_ciam').id,
            'saml_uid': self.ssnid,
        })
        self.sudo().user_id = new_user_id.id

    def _update_user(self):
        self.sudo().user_id.write({
            'login': self.work_email,
            'email': self.work_email,
            'saml_uid': self.ssnid,
        })
    
    @api.one
    def update_user(self):
        permission_lvl = (self.env.user._is_system() or self.env.user.has_group(
            'base_user_groups_dafa.group_dafa_org_admin_write')) and 2
        permission_lvl = permission_lvl or (
                self.env.user.has_group('base_user_groups_dafa.group_dafa_employees_write') and 1)
        if not permission_lvl:
            raise ValidationError(_("You are not permitted to do this."))
        self._update_user()

    @api.one
    def update_group(self):
        permission_lvl = (self.env.user._is_system() or self.env.user.has_group(
            'base_user_groups_dafa.group_dafa_org_admin_write')) and 2
        permission_lvl = permission_lvl or (self.env.user.has_group(
            'base_user_groups_dafa.group_dafa_employees_write') and 1)
        if not permission_lvl:
            raise ValidationError(_("You are not permitted to do this."))
        if not self.work_email:
            raise ValidationError(_("Kindly Enter an email for employee."))
        if not self.ssnid:
            raise ValidationError(_("Kindly Enter a social security number for employee."))
        # Validate personnummer
        if not re.match('^[0-9]{12}$', self.ssnid):
            raise ValidationError(_("Wrong SSN format. Should be 12 numbers (199010241234)."))
        if not validate_personnummer(self.ssnid[2:]):
            raise ValidationError(_("Wrong SSN format. Control digit does not validate."))
        if not self.user_id:
            self._create_user()
        else:
            self._update_user()
        if self.user_id:
            if self.env.user._is_system():
                user_sudo = self.user_id
            else:
                user_sudo = self.user_id.sudo()
            groups_id = []
            lvl2_groups = self.env.ref('base_user_groups_dafa.group_dafa_org_admin_write')
            # Check all DAFA groups and add/remove them
            for group in self.env['res.groups'].search([('is_dafa', '=', True)]):
                if permission_lvl < 2 and group in lvl2_groups:
                    # Level 1 is not permitted to change level 2 group membership
                    continue
                if group in user_sudo.groups_id:
                    if group not in self.user_groups:
                        groups_id.append((3, group.id))
                else:
                    if group in self.user_groups:
                        groups_id.append((4, group.id))
            if groups_id:
                user_sudo.write({
                    'groups_id': groups_id
                })
            updated_groups = user_sudo.groups_id.filtered('is_dafa') & self.user_groups
            super(HrEmployee, self).write({
                'user_groups': [(6, 0, updated_groups._ids)]})

    @api.multi
    def write(self, vals):
        res = super(HrEmployee, self).write(vals)
        if 'user_groups' in vals:
            self.update_group()
        elif 'work_email' in vals or 'ssnid' in vals:
            self.update_user()
        return res
