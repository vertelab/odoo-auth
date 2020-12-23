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
    'name': 'Auth User Rights Wizard Tour',
    'version': '12.0.1.0.3',
    'category': 'Outplacement',
    'license': 'AGPL-3',
    'summary': 'Odoo-tour for the Auth User Rights Wizard Module.',
    'description': """
    This module adds a Odoo-tour for the auth_user_rights_wizard-module AFC-780.\n
    Added version numbering\n
    """,
    'author': 'Vertel AB',
    'website': 'http://www.vertel.se',
    'depends': ['web_tour',
                'auth_user_rights_wizard'],
    'data': [
        'views/assets.xml',
    ],
}
# vim:expandtab:smartindent:tabstop=4s:softtabstop=4:shiftwidth=4:
