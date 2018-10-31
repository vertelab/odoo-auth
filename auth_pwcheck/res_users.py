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
from openerp.tools import SUPERUSER_ID,config
from openerp import http
from openerp.http import request
from openerp.exceptions import except_orm, Warning, RedirectWarning
import datetime

import logging
_logger = logging.getLogger(__name__)

from zxcvbn import zxcvbn

PWCHECK_STRENGTH = {
    0: u"Worst ☹",
    1: u"Bad ☹",
    2: u"Weak ☹",
    3: u"Good ☺",
    4: u"Strong ☻"
}

class res_users(models.Model):
    _inherit = 'res.users'

    @api.model
    def change_password(self,old_passwd, new_passwd):
        _logger.warn('before chanmge_password %s' % self)
        super(res_users, self).change_password(old_passwd,new_passwd)
        # ~ result = zxcvbn(new_passwd)
        # ~ _logger.warn('%s' % result)
        # ~ if result.get('score',0) < 3:
            # ~ raise Warning('\n'.join(result['feedback']['suggestions']+[_('Crack time'),result['crack_times_display']['offline_fast_hashing_1e10_per_second']]))


class change_password_user(models.TransientModel):
    _inherit = 'change.password.user'

    @api.multi
    def change_password_button(self):
        for line in self:
            result = zxcvbn(line.new_passwd)
            _logger.warn('%s' % result)
            if result.get('score',0) < 3:
                raise Warning('\n'.join([_('Password too weak')]+result['feedback']['suggestions']+[_('Crack time %s') % result['crack_times_display']['offline_fast_hashing_1e10_per_second']]))
        super(change_password_user,self).change_password_button()


# ~ class change_password_wizard(models.TransientModel):
    # ~ _inherit = "change.password.wizard"

    # ~ @api.multi
    # ~ def change_password_button(self):
        # ~ for line in self:
            # ~ result = zxcvbn(line.new_passwd)
            # ~ _logger.warn('%s' % result)
            # ~ if result.get('score',0) < 3:
                # ~ raise Warning('\n'.join(result['feedback']['suggestions']+[_('Crack time'),result['crack_times_display']['offline_fast_hashing_1e10_per_second']]))
        # ~ super(change_password_user,self).change_password_button()


#----------------------------------------------------------
# OpenERP Web web Controllers
#----------------------------------------------------------
class AuthPwcheck(http.Controller):

    @http.route(['/auth/pwform'], type='http', auth="public", website=True)
    def auth_pwform(self,**kwargs):
        return request.website.render("auth_pwcheck.form", {})

    @http.route(['/auth_pwcheck'], type='json', auth='public', website=True)
    def auth_pwcheck(self, passwd='', **kw):
        _logger.warn('begin')
        result = zxcvbn(passwd)
        # ~ time_delta = result.get('calc_time')
        # ~ result['calc_time'] = '%s microseconds' %time_delta.microseconds
        score = result['score']
        feedback = ''
        if score < 3:
            feedback = '\n'.join(result['feedback']['suggestions']+[_('Crack time'),result['crack_times_display']['offline_fast_hashing_1e10_per_second']])
        return {'score': score, 'score_text': PWCHECK_STRENGTH.get(score), 'feedback': feedback}


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
