import base64
import json
import functools

import werkzeug.urls
import werkzeug.utils
from werkzeug.exceptions import BadRequest

from odoo import api, http, SUPERUSER_ID, _
from odoo.exceptions import AccessDenied
from odoo.http import request
from odoo import registry as registry_get

import logging
_logger = logging.getLogger(__name__)

from odoo.addons.auth_oauth.controllers.main import OAuthLogin as OAuthLogin
from odoo.addons.auth_oauth.controllers.main import OAuthController as OAuthController
from odoo.addons.web.controllers.main import db_monodb, ensure_db, set_cookie_and_redirect, login_and_redirect
from odoo.addons.portal.controllers.portal import CustomerPortal as CP

class CustomerPortal(CP):

    def __init__(self, **args):
        self.OPTIONAL_BILLING_FIELDS.extend((
            'social_sec_nr',
        ))
        super(CustomerPortal, self).__init__(**args)

def fragment_to_query_string(func):
    @functools.wraps(func)
    def wrapper(self, *a, **kw):
        kw.pop('debug', False)
        if not kw:
            return """<html><head><script>
                var l = window.location;
                var q = l.hash.substring(1);
                var r = l.pathname + l.search;
                if(q.length !== 0) {
                    var s = l.search ? (l.search === '?' ? '' : '&') : '?';
                    r = l.pathname + l.search + s + q;
                }
                if (r == l.pathname) {
                    r = '/';
                }
                window.location = r;
            </script></head><body></body></html>"""
        return func(self, *a, **kw)
    return wrapper

class OAuthLoginFrejaeID(OAuthLogin):
    def list_providers(self):
        try:
            providers = request.env['auth.oauth.provider'].sudo().search_read([('enabled', '=', True)])
        except Exception:
            providers = []
        for provider in providers:
            return_url = request.httprequest.url_root + 'auth_oauth/signin'
            state = self.get_state(provider)
            params = dict(
                response_type='code', # old way was: response_type='token' if provider['name'] != 'Freja eID' else 'code',
                client_id=provider['client_id'],
                redirect_uri=return_url,
                scope=provider['scope'],
                state=json.dumps(state) if provider['name'] != 'Freja eID' else state,
            )
            provider['auth_link'] = "%s?%s" % (provider['auth_endpoint'], werkzeug.url_encode(params))
        return providers

    def get_state(self, provider):
        redirect = request.params.get('redirect') or 'web'
        if not redirect.startswith(('//', 'http://', 'https://')):
            redirect = '%s%s' % (request.httprequest.url_root, redirect[1:] if redirect[0] == '/' else redirect)
        state = dict(
            d=request.session.db,
            p=provider['id'],
            r=werkzeug.url_quote_plus(redirect),
        )
        token = request.params.get('token')
        if token:
            state['t'] = token
        if provider['name'] == 'Freja eID':
            _logger.error("inside get state ---")
            _logger.error(type(state))
            sample_string_bytes = str(state).encode("ascii")
            base64_bytes = base64.b64encode(sample_string_bytes)
            state = base64_bytes.decode("ascii")
            _logger.error("state now")
            _logger.error(state)
        return state

class OAuthControllerFrejaeID(OAuthController):

    @http.route('/auth_oauth/signin', type='http', auth='none')
    @fragment_to_query_string
    def signin(self, **kw):
        _logger.error(kw)
        if isinstance(kw['state'], str):
            _logger.error("Inside If ====")
            base64_string = kw['state']
            base64_bytes = base64_string.encode("ascii")
            sample_string_bytes = base64.b64decode(base64_bytes)
            sample_string = sample_string_bytes.decode("ascii")
            _logger.error(sample_string)
            sample_string = sample_string.replace('+', '')
            _logger.error(sample_string)
            _logger.error(type(sample_string))
            sample_string = sample_string.replace("\'", "\"")
            kw['state'] = sample_string
            _logger.error(kw)
        state = json.loads(kw['state'])
        dbname = state['d']
        if not http.db_filter([dbname]):
            return BadRequest()
        provider = state['p']
        context = state.get('c', {})
        registry = registry_get(dbname)
        with registry.cursor() as cr:
            try:
                env = api.Environment(cr, SUPERUSER_ID, context)
                credentials = env['res.users'].sudo().auth_oauth(provider, kw)
                cr.commit()
                action = state.get('a')
                menu = state.get('m')
                redirect = werkzeug.url_unquote_plus(state['r']) if state.get('r') else False
                url = '/web'
                if redirect:
                    url = redirect
                elif action:
                    url = '/web#action=%s' % action
                elif menu:
                    url = '/web#menu_id=%s' % menu
                resp = login_and_redirect(*credentials, redirect_url=url)
                # Since /web is hardcoded, verify user has right to land on it
                if werkzeug.urls.url_parse(resp.location).path == '/web' and not request.env.user.has_group(
                        'base.group_user'):
                    resp.location = '/'
                return resp
            except AttributeError as e:
                # auth_signup is not installed
                _logger.error("auth_signup not installed on database %s: oauth sign up cancelled." % (dbname,))
                _logger.error(str(e))
                url = "/web/login?oauth_error=1"
            except AccessDenied as e:
                # oauth credentials not valid, user could be on a temporary session
                _logger.info(
                    'OAuth2: access denied, redirect to main page in case a valid session exists, without setting cookies')
                _logger.error(str(e))
                url = "/web/login?oauth_error=3"
                redirect = werkzeug.utils.redirect(url, 303)
                redirect.autocorrect_location_header = False
                return redirect
            except Exception as e:
                # signup error
                _logger.exception("OAuth2: %s" % str(e))
                url = "/web/login?oauth_error=2"

        return set_cookie_and_redirect(url)
