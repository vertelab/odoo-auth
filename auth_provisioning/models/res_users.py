from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError, ValidationError
import logging

import pyqrcode
import io
import base64

class ResUsers(models.Model):
    _inherit = 'res.users'

     
    base_url_parameter = fields.Char(compute="set_base_url")
    qrcode_base_url = fields.Binary(compute="create_url_qrcode", store=False, readonly=False)
    qrcode_signup_url = fields.Binary(compute="create_url_qrcode", store=False, readonly=False)

    @api.depends('partner_id')
    def _compute_signup_url(self):
        for rec in self:
            if rec.partner_id and rec.partner_id._origin:
                print("---", rec.partner_id)
                print("---", rec.partner_id._origin)
                print("---", rec.partner_id._get_signup_url())
                rec.signup_url = rec.partner_id._get_signup_url()
            else:
                rec.signup_url = False

    signup_url = fields.Char(string="Signup URL", compute=_compute_signup_url)

    def create_url_qrcode(self):
        for record in self:
            buffer = io.BytesIO()
            qr = pyqrcode.create(record.base_url_parameter)
            qr.png(buffer, scale=3)
            record.qrcode_base_url = base64.b64encode(buffer.getvalue()).decode('utf-8')  # Encode to base64 and decode to string
            logging.warning(f"{record=}")
            logging.warning(f"{record.partner_id=}")
            
            sign_up_link = record.partner_id._get_signup_url()
            logging.warning(f"{sign_up_link=}")

            
            buffer = io.BytesIO()
            qr = pyqrcode.create(sign_up_link) #getsignupurl
            qr.png(buffer, scale=3)
            record.qrcode_signup_url = base64.b64encode(buffer.getvalue()).decode('utf-8')  # Encode to base64 and decode to string
            
 
    def set_base_url(self):
        for record in self:
            record.base_url_parameter = self.env['ir.config_parameter'].get_param(
                'web.base.url', 'Hittade inte web.base.url'
            )
