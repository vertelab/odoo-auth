from odoo import models, fields, api, _


class Project(models.Model):
    _inherit = "res.users"

    date_expire = odoo.fields.Datetime.to_string(value)
