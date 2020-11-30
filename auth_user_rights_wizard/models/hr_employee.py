from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class HREmployee(models.Model):
    _inherit = 'hr.employee'

    user_rights = fields.Many2many('ir.model.access', string="User Rights", compute='_set_user_rights')

    @api.depends('user_id')
    def _set_user_rights(self):
        for rec in self:
            if rec.user_id:
                user_groups = rec.env['res.groups'].search([('users', 'in', rec.user_id.id), ('name', 'ilike', 'DAFA')])
                for _rec in user_groups:
                    rec.user_rights = _rec.model_access.ids


class UserAccessRight(models.TransientModel):
    _name = 'hr.employee.user.right'

    group_id = fields.Many2one('res.groups', string="Group", domain=[('name', 'ilike', 'DAFA')])

    model_access = fields.Many2many('ir.model.access', string="Access Rights")

    @api.onchange('group_id')
    def get_group_access_rights(self):
        self.model_access = False
        if self.group_id:
            self.model_access = self.group_id.model_access.ids

    def action_assign_rights(self):
        active_ids = self.env.context.get('active_ids')
        if active_ids:
            for _id in active_ids:
                employee_user_id = self.env['hr.employee'].search([('id', '=', _id)])
                if employee_user_id.user_id:
                    self.group_id.write({
                        'users': [(4, employee_user_id.user_id.id)]
                    })
                    for rec in self.model_access:
                        self.group_id.write({
                            'model_access': [(4, rec.id)],
                        })
                else:
                    raise ValidationError(_('Employee has no related user'))




