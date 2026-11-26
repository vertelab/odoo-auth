from odoo import models, fields, api, _
# #if VERSION >= "20.0"
from odoo.tools import BinaryBytes
# #endif
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
    # #if VERSION >= "20.0"
    # 20.0: Binary-faltet haller ett BinaryValue. Mallen behover base64-text,
    # och QWeb-kontexten har varken base64 eller __import__ - sa modulen
    # lamnar en fardig datastrang sjalv.
    qrcode_signup_data = fields.Char(compute="create_url_qrcode", store=False)
    # #endif

    @api.depends('partner_id')
    def _compute_signup_url(self):
        for rec in self:
            if rec.partner_id and rec.partner_id._origin:
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
            # #if VERSION >= "20.0"
            # 20.0: Binary-faltet tar ett BinaryValue, inte base64-text och
            # inte rå bytes ("use BinaryValue instead of bytes"). Skickas
            # base64-strangen lagras den som binardata och avkodningen ger
            # UnicodeDecodeError: 'utf-8' codec can't decode byte 0x89.
            record.qrcode_signup_url = BinaryBytes(buffer.getvalue(), 'qrcode.png')
            record.qrcode_signup_data = 'data:image/png;base64,' + base64.b64encode(buffer.getvalue()).decode()
            # #else
            record.qrcode_signup_url = base64.b64encode(buffer.getvalue()).decode('utf-8')  # Encode to base64 and decode to string
            # #endif
            
 
    def set_base_url(self):
        for record in self:
            # #if VERSION >= "20.0"
            # get_param togs bort i 20.0; get_str ar dess ersattare.
            record.base_url_parameter = self.env['ir.config_parameter'].sudo().get_str(
                'web.base.url', 'Hittade inte web.base.url'
            )
            # #else
            record.base_url_parameter = self.env['ir.config_parameter'].sudo().get_param(
                'web.base.url', 'Hittade inte web.base.url'
            )
            # #endif
