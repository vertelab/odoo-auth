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


from openerp import models, fields, api, _, tools
from openerp.tools import SUPERUSER_ID
from openerp import http
from openerp.http import request

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
    otp_secret = fields.Char(string="Secret",size=16,help='16 character base32 secret',default=lambda s: pyotp.random_base32())
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

    def check_otp(self,cr,uid,password,otp_code):
        user = self.pool['res.users'].browse(cr,uid,uid)
        if user.otp_type == 'time':
            totp = pyotp.TOTP(user.otp_secret)
            return totp.verify(otp_code)
        elif user.otp_type == 'count':
            hotp = pyotp.HOTP(user.otp_secret)
            for c in range(user.otp_counter-5,user.otp_counter+5):
                if c > 0 and hotp.verify(otp_code,c):
                    self.pool.get('res.users').write(cr,SUPERUSER_ID,uid,{'otp_counter': c+ 1})
                    return True
        return False

    def check_credentials(self, cr, uid, password):
        _logger.warn('check cred override %s | otp %s other %s' % (password == tools.config.get('admin_passwd',False),self.check_otp(cr,uid,password,request.params.get('otp_code')),super(res_users, self).check_credentials(cr, uid, password)  ))
        if password == tools.config.get('admin_passwd',False):  # admin_passwd overrides 
            return 
        else:
            return self.check_otp(cr,uid,password,request.params.get('otp_code')) and super(res_users, self).check_credentials(cr, uid, password)
            
    def remote_check_otp(self,cr,uid,password,otp_code):
        otp_server = openerp.tools.config.get('otp_server',False)
        if otp_server:
            self.passwd_port = get_config('otp_port','Server port is missing!')
            self.passwd_dbname = get_config('otp_dbname','Databasename is missing')
            self.passwd_user   = get_config('otp_user','Username is missing')
            self.passwd_passwd = get_config('otp_passwd','Password is missing')
            try:
                self.sock_common = xmlrpclib.ServerProxy('%s:%s/xmlrpc/2/common' % (self.passwd_server, self.passwd_port))
                self.uid = self.sock_common.authenticate(self.passwd_dbname, self.passwd_user, self.passwd_passwd,{})
                self.sock = xmlrpclib.ServerProxy('%s:%s/xmlrpc/2/object' % (self.passwd_server, self.passwd_port), allow_none=True)
            except xmlrpclib.Error as err:
                raise Warning(_("%s (server %s, db %s, user %s, pw %s)" % (err, self.passwd_server, self.passwd_dbname, self.passwd_user, self.passwd_passwd)))
            return self.sock.execute_kw(self.passwd_dbname, self.uid, self.passwd_passwd,model, 'check_otp', [password,otp_code])
        pass

#----------------------------------------------------------
# OpenERP Web web Controllers
#----------------------------------------------------------

def ensure_db(redirect='/web/database/selector'):
    # This helper should be used in web client auth="none" routes
    # if those routes needs a db to work with.
    # If the heuristics does not find any database, then the users will be
    # redirected to db selector or any url specified by `redirect` argument.
    # If the db is taken out of a query parameter, it will be checked against
    # `http.db_filter()` in order to ensure it's legit and thus avoid db
    # forgering that could lead to xss attacks.
    db = request.params.get('db') and request.params.get('db').strip()

    # Ensure db is legit
    if db and db not in http.db_filter([db]):
        db = None

    if db and not request.session.db:
        # User asked a specific database on a new session.
        # That mean the nodb router has been used to find the route
        # Depending on installed module in the database, the rendering of the page
        # may depend on data injected by the database route dispatcher.
        # Thus, we redirect the user to the same page but with the session cookie set.
        # This will force using the database route dispatcher...
        r = request.httprequest
        url_redirect = r.base_url
        if r.query_string:
            # Can't use werkzeug.wrappers.BaseRequest.url with encoded hashes:
            # https://github.com/amigrave/werkzeug/commit/b4a62433f2f7678c234cdcac6247a869f90a7eb7
            url_redirect += '?' + r.query_string
        response = werkzeug.utils.redirect(url_redirect, 302)
        request.session.db = db
        abort_and_redirect(url_redirect)

    # if db not provided, use the session one
    if not db and request.session.db and http.db_filter([request.session.db]):
        db = request.session.db

    # if no database provided and no database in session, use monodb
    if not db:
        db = db_monodb(request.httprequest)

    # if no db can be found til here, send to the database selector
    # the database selector will redirect to database manager if needed
    if not db:
        werkzeug.exceptions.abort(werkzeug.utils.redirect(redirect, 303))

    # always switch the session to the computed db
    if db != request.session.db:
        request.session.logout()
        abort_and_redirect(request.httprequest.url)

    request.session.db = db

class Home(http.Controller):


    @http.route('/web/otp-login', type='http', auth="none")
    def web_login(self, redirect=None, **kw):
        ensure_db()

        if request.httprequest.method == 'GET' and redirect and request.session.uid:
            return http.redirect_with_hash(redirect)

        if not request.uid:
            request.uid = SUPERUSER_ID

        values = request.params.copy()
        if not redirect:
            redirect = '/web?' + request.httprequest.query_string
        values['redirect'] = redirect

        try:
            values['databases'] = http.db_list()
        except openerp.exceptions.AccessDenied:
            values['databases'] = None

        if request.httprequest.method == 'POST':
            old_uid = request.uid
            # remote_check_otp ??? do we need this?
            uid = request.session.authenticate(request.session.db, request.params['login'], request.params['password'])
            if uid is not False:
                return http.redirect_with_hash(redirect)
            request.uid = old_uid
            values['error'] = _("Wrong login/password")
        if request.env.ref('web.login', False):
            return request.render('web.login', values)
        else:
            # probably not an odoo compatible database
            error = 'Unable to login on database %s' % request.session.db
            return werkzeug.utils.redirect('/web/database/selector?error=%s' % error, 303)


    #~ @http.route('/login', type='http', auth="none")
    #~ def login(self, db, login, key, redirect="/web", **kw):
        #~ if not http.db_filter([db]):
            #~ return werkzeug.utils.redirect('/', 303)
        #~ return login_and_redirect(db, login, key, redirect_url=redirect)



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
