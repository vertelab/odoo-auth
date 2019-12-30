# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution, third party addon
#    Copyright (C) 2019 Vertel AB (<http://vertel.se>).
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

from odoo import models, fields, api, _, registry
from odoo.exceptions import AccessDenied, UserError
import datetime

import logging
_logger = logging.getLogger(__name__)

class ResUsers(models.Model):
	_inherit = "res.users"

	last_fail = fields.Datetime(string='Last failed login', help="Date and time for this users last failed login")
	no_fail = fields.Integer(string='Number of failed logins', help="Number of failed logins in a row since last successful login for user")

	def _check_credentials(self, password):
		max_tries = api_profile = int(self.env['ir.config_parameter'].sudo().get_param('auth_timeout.max_tries'))
		timeout_param = api_profile = int(self.env['ir.config_parameter'].sudo().get_param('auth_timeout.cooldown_time'))
		timeout = datetime.timedelta(seconds=timeout_param)
		time_now = datetime.datetime.now()

		# timeout check
		if self.no_fail >= max_tries:
			if (time_now - self.last_fail) > timeout:
				# timeout completed, reset tries.
				self.sudo().no_fail = 0
			else:
				# if timeout still active, refuse access
				# There is no use trying to add to n.o. failed logins since an exception 
				# is raised and the pointer is rolled back. We could create a new pointer
				# similar to how we do it later if it is really neccessary.
				raise AccessDenied()

		# try login
		try:
			res = super(ResUsers, self)._check_credentials(password)
			# reset counter on successful login
			self.sudo().no_fail = 0
		except AccessDenied:
			# create new cursor in order to be able to commit in an exception 
			new_cr = registry(self.env.cr.dbname).cursor()
			uid, context = self.env.uid, self.env.context
			with api.Environment.manage():
				self.env = api.Environment(new_cr, uid, context)
				
				# log failure
				self.sudo().no_fail = self.no_fail + 1
				self.sudo().last_fail = time_now
				self.partner_id.sudo().message_post(body='User failed login, failures in row: %s' % self.no_fail, subject='Failed login', message_type='notification')				
	
				# commit and close new cursor
				self.env.cr.commit()
				self.env.cr.close()

			# raise error
			raise

		# self.no_fail = 0
		# return res