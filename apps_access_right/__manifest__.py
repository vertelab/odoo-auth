# -*- coding: utf-8 -*-
{
    'name': 'Administrator Apps Security',
    'version': '1.0',
    'license': 'AGPL-3',
    'category': 'Administration',
    'summary': 'Separate Apps installation rights from Settings access',
    'description': """
        This module creates a strict separation between:
        - Administrator/Settings: Can configure system but NOT install apps
        - Administrator/Apps: Can install and manage applications

        Critical security feature: Settings users cannot grant Apps privileges.
    """,
    'author': 'Your Company',
    'depends': ['base', 'base_install_request'],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/ir_module_module_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}