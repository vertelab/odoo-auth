{
    'name': 'Authentication from HTTP Basic',
    # #if VERSION == "20.0"
    'version': '20.0.1.0.0',
    # #elif VERSION == "19.0"
    'version': '19.0.1.0.0',
    # #elif VERSION == "18.0"
    'version': '18.0.1.0.0',
    # #else
    'version': '20.0.1.0.0',
    # #endif
    'category': 'Authentication',
    'summary': 'Authenticate users via HTTP Basic Authentication headers',
    'description': '''
        This module allows Odoo to authenticate users via HTTP Basic Authentication.
        It extracts username and password from the Authorization header and attempts
        to login to the first available database.
    ''',
    'author': 'Vertel Sverige AB',
    'website': 'https://www.vertel.se',
    'depends': ['base', 'web'],
    'data': [],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
