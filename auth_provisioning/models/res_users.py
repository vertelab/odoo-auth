from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError, ValidationError
import logging

import pyqrcode
import io
import base64

class ResUsers(models.Model):
    _inherit = 'res.users'

    
    base_url_parameter = fields.Char(compute="set_base_url")
    qrcode = fields.Binary(compute="create_url_qrcode", store=False, readonly=False)

    def create_url_qrcode(self):
        for record in self:
            buffer = io.BytesIO()
            qr = pyqrcode.create(record.base_url_parameter)
            qr.png(buffer, scale=3)
            record.qrcode = base64.b64encode(buffer.getvalue()).decode('utf-8')  # Encode to base64 and decode to string

 
    def set_base_url(self):
        for record in self:
            record.base_url_parameter = self.env['ir.config_parameter'].get_param(
                'web.base.url', 'Hittade inte web.base.url'
            )
