{
    'name': 'Limit Signup without Auth Providers',
    'version': '14.0.1.0.0',
    'author': 'Verified Email Europe AB',
    'maintainer': 'Verified Email Europe AB',
    'contributors': 'Hemangi Rupareliya, Verified Email Europe AB, Fredrik Arvas',
    'website': 'https://verified-email.com/',
    'license': 'AGPL-3',
    'category': 'Tools',
    'depends': [
        'auth_signup',  # Odoo SA
        'auth_oauth',  # Odoo SA
    ],
    'data': {
        'views/auth_signup_login_tem.xml',
    },
    'application': False,
    'installable': True,
}
