from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class HREmployee(models.Model):
    _inherit = 'hr.employee'

    user_groups = fields.Many2many('res.groups', string="User Rights", compute='_set_user_rights')

    @api.depends('user_id')
    def _set_user_rights(self):
        for rec in self:
            if rec.user_id:
                user_groups = rec.env['res.groups'].search([('users', 'in', rec.user_id.id), ('name', 'ilike', 'DAFA')])
                rec.user_groups = user_groups.ids


class UserAccessRight(models.TransientModel):
    _name = 'hr.employee.user.right'

    employee_id = fields.Many2one('hr.employee', default=lambda self: self.env.context.get('active_id'))

    user_groups = fields.Many2many('res.groups', string="Existing Groups", compute='_set_user_rights')

    @api.depends('employee_id')
    def _set_user_rights(self):
        for rec in self:
            if rec.employee_id and rec.employee_id.user_id:
                user_groups = rec.env['res.groups'].search([('users', 'in', rec.employee_id.user_id.id), ('name', 'ilike', 'DAFA')])
                rec.user_groups = user_groups.ids
            else:
                rec.user_groups = False

    group_id = fields.Many2many('res.groups', string="Group", domain=[('name', 'ilike', 'DAFA')])

    model_access = fields.Many2many('ir.model.access', string="Access Rights")

    def action_assign_rights(self):
        active_ids = self.env.context.get('active_ids')
        if active_ids:
            for _id in active_ids:
                employee_user_id = self.env['hr.employee'].search([('id', '=', _id)])
                if employee_user_id.user_id:
                    for group_rec in self.group_id:
                        group_rec.write({
                            'users': [(4, employee_user_id.user_id.id)]
                        })

                        for rec in self.model_access:
                            group_rec.write({
                                'model_access': [(4, rec.id)],
                            })
                else:
                    raise ValidationError(_('Employee has no related user'))




