import base64
import logging
from odoo.modules.registry import Registry
from odoo.http import db_list, request, Response

_logger = logging.getLogger(__name__)


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


# Patch the session setup
try:
    from odoo.http import Request

    original_get_session = Request._get_session_and_dbname


    def patched_get_session_and_dbname(self):
        session, dbname = original_get_session(self)

        # Skip for static files
        if '/static/' in self.httprequest.path:
            return session, dbname

        # Ensure request object has session available for get_basic_auth_credentials()
        request.session = session

        # If not logged in and have database
        if not session.uid and dbname:
            username, password = get_basic_auth_credentials()

            if not username:
                # No auth header - challenge for Basic Auth
                from werkzeug.exceptions import Unauthorized
                raise Unauthorized(response=send_auth_challenge())

            # Try to login using session.authenticate (the correct way)
            try:
                _logger.info(f"Attempting Basic Auth login for user: {username}")

                # Use the correct credentials format for session.authenticate
                credential = {'login': username, 'password': password, 'type': 'password'}
                registry = Registry(dbname)
                user_agent_env = {}
                uid = registry['res.users'].authenticate(dbname, credential, {**user_agent_env, 'interactive': False})

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

        return session, dbname


    Request._get_session_and_dbname = patched_get_session_and_dbname
    _logger.info("Basic Auth module loaded successfully")

except Exception as e:
    _logger.error(f"Failed to load Basic Auth module: {e}")