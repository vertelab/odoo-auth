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

{
    'name': 'Login timeout',
    'version': '12.0.1',
    'category': 'other',
    'license': 'AGPL-3',
    'summary': 'Adds a simple timeout for users after repeated failed logins in too short a time.',
    'description': """Two new settings are added under Global Settings > Users > Login timeout.""",
    'author': 'Vertel AB',
    'website': 'http://www.vertel.se',
    'depends': ['base_setup', 'auth_signup'],
    'data': ['views/res_users_views.xml','views/res_config_settings_views.xml'],
    'auto_install': False,
}
# vim:expandtab:smartindent:tabstop=4s:softtabstop=4:shiftwidth=4:
