from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class HREmployee(models.Model):
    _inherit = 'hr.employee'

    user_groups = fields.Many2many('res.groups', string="User Groups", compute='_set_user_rights')

    @api.depends('user_id')
    def _set_user_rights(self):
        for rec in self:
            if rec.user_id:
                user_groups = rec.env['res.groups'].search([('users', 'in', rec.user_id.id), ('name', 'ilike', 'DAFA')])
                rec.user_groups = user_groups.ids


class UserAccessRight(models.TransientModel):
    _name = 'hr.employee.user.right'

    employee_id = fields.Many2one('hr.employee', default=lambda self: self.env.context.get('active_id'))

    def _get_user_groups(self):
        active_ids = self.env.context.get('active_ids')
        if active_ids:
            employee_user_id = self.env['hr.employee'].sudo().search([('id', '=', active_ids[0])])
            if employee_user_id.user_id:
                user_groups = self.env['res.groups'].sudo().search([('users', 'in', employee_user_id.user_id.id),
                                                                    ('name', 'ilike', 'DAFA')])
                return user_groups.ids
            else:
                return False

    group_id = fields.Many2many('res.groups', string="Group", domain=[('name', 'ilike', 'DAFA')],
                                default=_get_user_groups)

    def action_assign_rights(self):
        active_ids = self.env.context.get('active_ids')
        if active_ids:
            for _id in active_ids:
                employee_user_id = self.env['hr.employee'].sudo().search([('id', '=', _id)])
                if not employee_user_id.user_id:
                    new_user_id = self.env['res.users'].sudo().create({
                        'name': employee_user_id.name,
                        'login': employee_user_id.work_email,
                        'email': employee_user_id.work_email,
                        "notification_type": "email",
                    })
                    employee_user_id.user_id = new_user_id.id
                if employee_user_id.user_id:
                    for group_rec in self.group_id:
                        group_rec.sudo().write({
                            'users': [(4, employee_user_id.user_id.id)]
                        })

