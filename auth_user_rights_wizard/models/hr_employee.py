from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class HREmployee(models.Model):
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
        res = super(HREmployee, self).create(vals)
        if res.user_groups:
            res.update_group()
        return res

    def _create_user(self):
        new_user_id = self.env['res.users'].sudo().create({
            'name': self.name,
            'login': self.work_email,
            'email': self.work_email,
            "notification_type": "email",
        })
        self.sudo().user_id = new_user_id.id

    @api.one
    def update_group(self):
        permission_check = self.env.user._is_system() or self.env.user.has_group('base_user_groups_dafa.group_dafa_superadmin')
        if not permission_check:
            raise ValidationError(_("You are not permitted to do this"))
        if not self.work_email:
            raise ValidationError(_("Kindly Enter an email for employee"))
        if not self.user_id:
            self._create_user()
        if self.user_id:
            if self.env.user._is_system():
                user_sudo = self.user_id
            else:
                user_sudo = self.user_id.sudo()
            groups_id = []
            # Check all DAFA groups and add/remove them
            for group in self.env['res.groups'].search([('is_dafa', '=', True)]):
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

    @api.multi
    def write(self, vals):
        res = super(HREmployee, self).write(vals)
        if 'user_groups' in vals:
            self.update_group()
        return res
