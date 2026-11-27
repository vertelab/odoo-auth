# -*- coding: utf-8 -*-
{
    'name': 'Auth: Apps Access Rights',
    'version': '19.0.1.0.0',
    'license': 'AGPL-3',
    'category': 'Administration',
    'summary': 'Separate Apps installation rights from Settings access.',
    'description': '''
Administrator Apps Security
===========================

    This module creates a strict separation between:
            - Administrator/Settings: Can configure system but NOT install apps
            - Administrator/Apps: Can install and manage applications

    Critical security feature: Settings users cannot grant Apps privileges.

    Features:

        - UI Integration: Extends 2 view(s) in the Odoo interface.
        - Extends Odoo: Builds on existing Odoo models.
    ''',
    'author': 'Your Company',
    'website': 'https://vertel.se/apps/odoo-auth/apps_access_right',
    'depends': ['base', 'base_install_request'],
    'data': [
        # security.xml FORE ir.model.access.csv: CSV-raden refererar
        # group_apps_manager, som definieras i security.xml. Laddas CSV forst
        # faller installationen med "No matching record found for external id".
        'security/security.xml',
        # Odoo 20 bytte form OCH filnamn pa ir.model.access -> ir.access.
        # Filnamnet bestammer modellen, sa ratt fil maste listas per utgave.
        'security/ir.model.access.csv',
        'views/ir_module_module_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
