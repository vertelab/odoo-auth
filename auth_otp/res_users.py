# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2017- Vertel AB (<http://vertel.se>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


from openerp import models, fields, api, _
from openerp.tools import SUPERUSER_ID

import logging
_logger = logging.getLogger(__name__)

# https://pyotp.readthedocs.io/en/latest/
import pyotp
# http://pythonhosted.org/PyQRCode/rendering.html
import pyqrcode
import io

class res_users(models.Model):
    _inherit = 'res.users'

    otp_type = fields.Selection(selection=[('time',_('Time based')),('count',_('Counter based'))],default='time',string="Type",help="Type of OTP, time = new pin for each period, counter = new pin for each login")
    @api.model
    def _otp_secret(self):
        return pyotp.random_base32()
    otp_secret = fields.Char(string="Secret",size=16,help='16 character base32 secret',default=_otp_secret)
    otp_counter = fields.Integer(string="Counter",default=1)
    otp_digits = fields.Integer(string="Digits",default=6,help="Length of the PIN")
    otp_period = fields.Integer(string="Period",default=30,help="Number seconds PIN is active")
    @api.one
    def _otp_qrcode(self):
        buffer = io.BytesIO()
        qr = pyqrcode.create(self.otp_uri)
        qr.png(buffer,scale=3)    
        self.otp_qrcode = buffer.getvalue().encode('base64')
    otp_qrcode = fields.Binary(compute="_otp_qrcode")
    @api.one
    def _otp_uri(self):
        if self.otp_type == 'time':
            otp = pyotp.TOTP(self.otp_secret)
            otp.period = self.otp_period
            #~ provisioning_uri = otp.provisioning_uri(self.login,issuer_name=self.company_id.name)
            provisioning_uri = otp.provisioning_uri(self.login)
        else:
            otp = pyotp.HOTP(self.otp_secret)
            otp.digits = self.otp_digits
            provisioning_uri = otp.provisioning_uri(self.login,self.otp_counter)
            #~ provisioning_uri = otp.provisioning_uri(self.login,self.otp_counter,issuer_name=self.company_id.name)
        self.otp_uri = provisioning_uri + '&issuer=%s' % self.company_id.name
    otp_uri = fields.Char(compute='_otp_uri',string="URI")

    def check_otp(self,cr,uid,password):
        user = self.pool['res.users'].browse(cr,uid,uid)
        if user.otp_type == 'time':
            totp = pyotp.TOTP(user.otp_secret)
            return totp.verify(password)
        elif user.otp_type == 'count':
            hotp = pyotp.HOTP(user.otp_secret)
            for c in range(user.otp_counter-5,user.otp_counter+5):
                if c > 0 and hotp.verify(password,c):
                    self.pool.get('res.users').write(cr,SUPERUSER_ID,uid,{'otp_counter': c+ 1})
                    return True
        return False

    def check_credentials(self, cr, uid, password):
        if self.check_otp(cr,uid,password):
            return 
        else:
            return super(res_users, self).check_credentials(cr, uid, password)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
