from odoo import models, fields, api, _


class Project(models.Model):
    _inherit = "res.users"

    date_expire = fields.Date('res.users', string="Date expire")
