# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Management Solution, third party addon
#    Copyright (C) 2020 Vertel AB (<http://vertel.se>).
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
    "name": "DAFA SAML Settings",
    "version": "12.0.1.0.1",
    "author": "Vertel AB",
    "license": "AGPL-3",
    "description": "SAML Settings for Arbetsförmedlingen. \n
    Added maintained url for the modules.",
    "website": "https://vertel.se/",
    "category": "Tools",
    "depends": [
        "auth_saml_ol_create_user", # https://github.com/vertelab/server-auth/tree/Dev-12.0-Fenix-Sprint-02/auth_saml_ol_create_user
        "auth_saml_ol_groups",      # https://github.com/vertelab/server-auth/tree/Dev-12.0-Fenix-Sprint-02/auth_saml_ol_groups
        "base_user_groups_dafa",    # https://github.com/vertelab/odoo-base/tree/Dev-12.0-Fenix-Sprint-02
        ],
    "data": [
        "data/af_saml.xml",
        "views/web_login.xml",
    ],
    "application": True,
    "installable": True,
}
