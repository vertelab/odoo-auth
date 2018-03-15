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


{
    'name': 'PAM Authentification',
    'version': '2.0',
    'category': 'Tools',
    'description': """
        Allow PAM-authentication systems to use
        Odoo user configuration
        
https://www.privacyidea.org/
http://pam-python.sourceforge.net/doc/html/


https://www.privacyidea.org/how-to-install-privacyidea-otp-server-on-ubuntu-14-04/

https://www.privacyidea.org/ssh-keys-and-otp-really-strong-two-factor-authentication/
https://www.howtoforge.com/tutorial/ssh-key-management-with-privacyidea/
https://launchpad.net/~privacyidea/+archive/ubuntu/privacyidea
https://www.linux.com/learn/how-set-2-factor-authentication-login-and-sudo


""",
    'author': 'Vertel AB',
    'license': 'AGPL-3',
    'maintainer': 'Vertel AB',
    'website': 'http://vertel.se',
    'depends': ['base', 'web'],
    'data': [
        'res_users.xml',
    ],
    'external_dependencies': {
        #~ 'python' : ['pyotp','pyqrcode','pypng'],
        'python' : ['pyotp','pyqrcode'],
    },
    'installable': True,
    'auto_install': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
