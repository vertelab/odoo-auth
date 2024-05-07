# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2018- Vertel AB (<http://vertel.se>).
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
    'name': 'Check Password Strength',
    'version': '1.0',
    'category': 'Tools',
    'description': """
Check the strength of a given password

* Accepts user data to be added to the dictionaries that are tested against (name, birthdate, etc)
* Gives a score to the password, from 0 (terrible) to 4 (great)
* Provides feedback on the password and ways to improve it
* Returns time estimates on how long it would take to guess the password in different situations

Using the zxcvbn library
https://github.com/dwolfhub/zxcvbn-python

sudo pip install zxcvbn


https://css-tricks.com/password-strength-meter/
https://www.formget.com/password-strength-checker-in-jquery/


""",
    'author': 'Vertel AB',
    'license': 'AGPL-3',
    'maintainer': 'Vertel AB',
    'website': 'http://vertel.se',
    'depends': ['auth_signup'],
    'data': [
        'res_users.xml',
    ],
    'external_dependencies': {
        #~ 'python' : ['pyotp','pyqrcode','pypng'],
        'python' : ['pyotp','pyqrcode'],
    },
    'installable': True,
    'auto_install': False, 
    # ~ "sequence": 5,  # To be installed early
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
