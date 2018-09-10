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
    'name': 'OTP Authentification',
    'version': '2.0',
    'category': 'Tools',
    'description': """
Allow users to login using one time password (OTP)
and two-factor authentication (2FA).

This module adds a verification code to the 
login form. The user has to know his password and
have a piece of hardware storing a shared secret, usually
a smartphone. If there is other autentications modules
installed then this method will be the second instead of password.

The shared sectret are provisioned using QR-code in the password 
reminder mail, along with QR-codes for Android and IOS apps (FreeOTP).

* OTPs involve a shared secret, stored both on the phone and the server
* OTPs can be generated on a phone without internet connectivity
* OTPs are combined with your password so if your phone is lost, your account is still secure

After the module is installed, all users have to login using OTP verification code. There fore 
its recommended to send out a password reminder mail (server action) to every user after installing
this module.

To override OTP-authentication, if something gone wrong, you can add "otp_override = True" in
the server config file. Then the system will only check password again.

Open MFA standards are defined in RFC 4226 (HOTP: An HMAC-Based One-Time Password Algorithm) 
and in RFC 6238 (TOTP: Time-Based One-Time Password Algorithm). 

* https://freeotp.github.io/
* https://authy.com/
* https://play.google.com/store/apps/details?id=com.google.android.apps.authenticator2

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
    "sequence": 5,  # To be installed early
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
