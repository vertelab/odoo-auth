{
    'name': 'Auth: HTTP Basic Authentication',
    'version': '18.0.1.0.0',
    'category': 'Authentication',
    'summary': 'Authenticate users via HTTP Basic Authentication headers.',
    'description': '''
Authentication from HTTP Basic
==============================

    This module allows Odoo to authenticate users via HTTP Basic Authentication.
            It extracts username and password from the Authorization header and attempts
            to login to the first available database.

    Features:

        - Focused Fix: A small, targeted improvement to standard Odoo behaviour.
    ''',
    'author': 'Vertel AB',
    'website': 'https://vertel.se/apps/odoo-auth/auth_from_basic_http',
    'depends': ['base', 'web'],
    'data': [],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}