import base64
import logging
from odoo.modules.registry import Registry
from odoo.http import request, Response
from odoo.tools.config import config

_logger = logging.getLogger(__name__)

def domain_requires_basic_auth():
    """Check if current domain requires Basic Auth"""
    basic_auth_domains = config.get('basic_auth_domains')
    if not basic_auth_domains:
        return False

    # Get the current request host
    current_host = request.httprequest.host
    # Parse configured domains (comma-separated)
    configured_domains = [domain.strip() for domain in basic_auth_domains.split(',')]

    # Check if current host matches any configured domain
    for domain in configured_domains:
        # Handle wildcard patterns like *.domain.com
        if domain.startswith('*.'):
            # Remove the *. prefix to get the base domain
            base_domain = domain[2:]  # *.domain.com → domain.com

            # Check if current host is a subdomain of base_domain
            if current_host == base_domain or current_host.endswith('.' + base_domain):
                return True

        if domain and current_host == domain:
            return True

    return False


def get_basic_auth_credentials():
    """Get username/password from Authorization header"""
    auth = request.httprequest.headers.get('Authorization', '')
    if not auth.startswith('Basic '):
        return None, None

    try:
        decoded = base64.b64decode(auth[6:]).decode('utf-8')
        return decoded.split(':', 1)
    except:
        return None, None


def send_auth_challenge():
    """Send 401 to trigger browser Basic Auth popup"""
    return Response('Login Required', status=401, headers={
        'WWW-Authenticate': 'Basic realm="Odoo"'
    })


# Patch the session setup.
#
# 18.0/19.0: Request._get_session_and_dbname() är en metod på Request.
# 20.0:      router._set_session_and_dbname(request) är en modulnivå-funktion
#            som sätter request.session och request.db. Metoden finns inte
#            kvar, så patchen måste läggas på funktionen i stället.
try:
    # #if VERSION >= "20.0"
    from odoo.http import router as _http_router

    _original_set_session_and_dbname = _http_router._set_session_and_dbname

    def _patched_set_session_and_dbname(req):
        _original_set_session_and_dbname(req)
        _basic_auth_after_session(req)
        return None
    # #else
    from odoo.http import Request

    _original_set_session_and_dbname = Request._get_session_and_dbname

    def _patched_set_session_and_dbname(req):
        session, dbname = _original_set_session_and_dbname(req)
        _basic_auth_after_session(req)
        return session, dbname
    # #endif


    def _basic_auth_after_session(req):
        # Skip for static files
        if '/static/' in req.httprequest.path:
            return

        # Check if this domain requires Basic Auth
        if not domain_requires_basic_auth():
            return

        # If not logged in and have database
        if not req.session.uid and req.db:
            username, password = get_basic_auth_credentials()

            if not username:
                # No auth header - challenge for Basic Auth
                from werkzeug.exceptions import Unauthorized
                raise Unauthorized(response=send_auth_challenge())

            # Try to login using res.users.authenticate (the correct way)
            try:
                _logger.info(f"Attempting Basic Auth login for user: {username}")

                # Use the correct credentials format for authenticate
                credential = {'login': username, 'password': password, 'type': 'password'}
                registry = Registry(req.db)
                user_agent_env = {}
                # #if VERSION >= "20.0"
                # 20.0: authenticate(credential, user_agent_env) — db läses ur
                # registryt, inte ur ett argument.
                auth_info = registry['res.users'].authenticate(credential, {**user_agent_env, 'interactive': False})
                # #else
                auth_info = registry['res.users'].authenticate(req.db, credential, {**user_agent_env, 'interactive': False})
                # #endif
                uid = auth_info and auth_info.get('uid')

                if uid:
                    _logger.info(f"Basic Auth login successful: {username}")
                else:
                    _logger.warning(f"Basic Auth login failed: {username} - Invalid credentials")
                    from werkzeug.exceptions import Unauthorized
                    raise Unauthorized(response=send_auth_challenge())

            except Exception as e:
                _logger.warning(f"Basic Auth login failed: {username} - {e}")
                from werkzeug.exceptions import Unauthorized
                raise Unauthorized(response=send_auth_challenge())

    # #if VERSION >= "20.0"
    _http_router._set_session_and_dbname = _patched_set_session_and_dbname
    # #else
    Request._get_session_and_dbname = _patched_set_session_and_dbname
    # #endif
    _logger.info("Basic Auth module loaded successfully")

except Exception as e:
    _logger.error(f"Failed to load Basic Auth module: {e}")