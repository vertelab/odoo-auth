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

    user_groups = fields.Many2many('res.groups', string="User Groups", domain=[('name', 'ilike', 'DAFA')],
                                   default=_get_employee_groups)

    @api.model
    def create(self, vals):
        res = super(HREmployee, self).create(vals)
        if res.user_groups:
            self.update_group(res)
        return res

    def create_user(self, value):
        new_user_id = self.env['res.users'].sudo().create({
            'name': value.name,
            'login': value.work_email,
            'email': value.work_email,
            "notification_type": "email",
        })
        value.sudo().user_id = new_user_id.id

    def update_group(self, value):
        permission_check = self.env.user.has_group('base_user_groups_dafa.group_dafa_superadmin')
        if not permission_check:
            raise ValidationError(_("You are not permitted to do this"))
        if permission_check and not value.work_email:
            raise ValidationError(_("Kindly Enter an email for employee"))

        if not value.user_id:
            self.create_user(value)
        if value.user_id:
            for group_rec in value.user_groups:
                group_rec.sudo().write({
                    'users': [(4, value.user_id.id)]
                })

    @api.multi
    def write(self, vals):
        res = super(HREmployee, self).write(vals)
        if self.user_groups:
            self.update_group(self)
        return res
