{
    'name': 'Freja eID Integration',
    'version': '14.0.1.0.4',
    'author': 'Verified Email Europe AB',
    'maintainer': 'Verified Email Europe AB',
    'contributors': 'Hemangi Rupareliya, Verified Email Europe AB, Fredrik Arvas',
    'website': 'https://verified-email.com/',
    'license': 'AGPL-3',
    'category': 'Tools',
    'depends': [
        'auth_oauth',  # Odoo SA
        'portal',      # Odoo SA
        'hr',
        'partner_ssn',
        #'partner_extenstion_verifiedemail', # https://github.com/VerifiedEmailEurope/ve-odoo-base/tree/14.0
        #'mail_sender_whitelisting' # https://github.com/VerifiedEmailEurope/ve-odoo-mail/tree/14.0
    ],
    'data': {
        'data/mail_templates.xml',
        'views/provider_views.xml',
        'views/portal_templates.xml',
    },
    'application': False,
    'installable': True,
}
