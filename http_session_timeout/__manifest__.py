{
    'name': 'Configurable session timeout',
    'version': '12.0.0.1',
    'category': '',
    'description': """
Sets the timout for session to 16 hours by default.
Can be overridden using odoo config "session_timeout", value in seconds.
This module must be loaded server wide through the config file.

Example:
server_wide_modules = base,web,http_session_timeout
""",
    'author': 'Vertel AB',
    'license': 'AGPL-3',
    'website': 'http://www.vertel.se',
    'depends': [],
    'data': [],
    'application': False,
    'installable': False,
}
