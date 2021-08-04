{
    'name': 'Freja eID Integration',
    'version': '13.0.1.0.3',
    'author': 'Hemangi Rupareliya',
    'maintainer': 'Vertel AB',
    'contributors': 'Hemangi Rupareliya, Fredrik Avas',
    'website': 'https://verified-email.com/',
    'license': 'AGPL-3',
    'category': 'Tools',
    'depends': [
        'auth_oauth', 'partner_ssn', 'portal', 'partner_extenstion_verifiedemail'
    ],
    'data': {
        'views/provider_views.xml',
        'views/portal_templates.xml'
    },
    'application': False,
    'installable': True,
}
