import json
import logging
import requests
from odoo.addons.auth_signup.models.res_users import SignupError
from odoo.exceptions import AccessDenied, UserError

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class AuthProvider(models.Model):
    _inherit = 'auth.oauth.provider'

    client_secret = fields.Char("Client Secret")

class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def _auth_oauth_rpc(self, provider, endpoint, access_token):
        if provider and provider.name != 'Freja eID':
            return requests.get(endpoint, params={'access_token': access_token}).json()
        else:
            _logger.error("inside auth outh rpc ===")
            _logger.error(endpoint)
            _logger.error(access_token)
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            data_user_info = {
                'grant_type': 'authorization_code',
                'client_id': provider.client_id,
                'client_secret': provider.client_secret,
                'redirect_uri': base_url + '/auth_oauth/signin',
                'code': access_token
            }
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
            }
            response = requests.post(endpoint, data=data_user_info, headers=headers)
            _logger.error("Response")
            _logger.error(response)
            return json.loads(response.text)

    @api.model
    def _auth_oauth_validate(self, provider, access_token):
        """ return the validation data corresponding to the access token """
        oauth_provider = self.env['auth.oauth.provider'].browse(provider)
        validation = self._auth_oauth_rpc(oauth_provider, oauth_provider.validation_endpoint, access_token)
        if validation.get("error"):
            raise Exception(validation['error'])
        if oauth_provider.data_endpoint:
            if oauth_provider.name != 'Freja eID':
                data = self._auth_oauth_rpc(oauth_provider, oauth_provider.data_endpoint, access_token)
                validation.update(data)
            else:
                _logger.error(self)
                _logger.error("Insdide if datapoint")
                access_token = validation.get('access_token')
                response = requests.get(oauth_provider.data_endpoint,
                                        params={'access_token': access_token})                
                _logger.error(response.url)
                _logger.error(response.text)
                _logger.error(response.request)
                _logger.error(json.loads(response.text))
                validation.update(json.loads(response.text))
        return validation

    @api.model
    def _generate_signup_values(self, provider, validation, params):
        oauth_uid = validation['user_id'] if 'user_id' in validation else ''
        oauth_provider = self.env['auth.oauth.provider'].browse(provider)
        if not oauth_uid and oauth_provider.name == 'Freja eID' and 'sub' in validation:
            oauth_uid = validation.get('sub')
        email = validation.get('email', 'provider_%s_user_%s' % (provider, oauth_uid))
        name = validation.get('name', email)
        country_id = False
        if 'https://frejaeid.com/oidc/claims/country' in validation:
            country = self.env['res.country'].search(
                [('code', '=', validation.get('https://frejaeid.com/oidc/claims/country'))])
            if country:
                country_id = country.id
        return {
            'name': name,
            'login': email,
            'email': email,
            'oauth_provider_id': provider,
            'oauth_uid': oauth_uid,
            'oauth_access_token': params['access_token'] if oauth_provider.name != 'Freja eID' else params['code'],
            'active': True,
            'social_sec_nr': validation.get('https://frejaeid.com/oidc/claims/personalIdentityNumber') if \
                'https://frejaeid.com/oidc/claims/personalIdentityNumber' in validation else '',
            'country_id': country_id,
        }

    @api.model
    def _auth_oauth_signin(self, provider, validation, params):
        """ retrieve and sign in the user corresponding to provider and validated access token
            :param provider: oauth provider id (int)
            :param validation: result of validation of access token (dict)
            :param params: oauth parameters (dict)
            :return: user login (str)
            :raise: AccessDenied if signin failed

            This method can be overridden to add alternative signin methods.
        """
        oauth_uid = validation['user_id'] if 'user_id' in validation else ''
        oauth_user = self.search([("login", "=", validation.get('email'))], limit=1)
        try:
            if oauth_uid:
                oauth_user = self.search([("oauth_uid", "=", oauth_uid), ('oauth_provider_id', '=', provider)])
                if not oauth_user:
                    raise AccessDenied()
                assert len(oauth_user) == 1
                oauth_user.write({'oauth_access_token': params['access_token']})
                return oauth_user.login
            elif oauth_user:
                _logger.error("Oauth User")
                _logger.error(oauth_user)
                _logger.error(oauth_user.partner_id)
                oauth_user.write({'oauth_access_token': params['code']})
                try:
                    _logger.error(oauth_user.login)
                    if oauth_user and oauth_user.partner_id:
                        if not oauth_user.partner_id.social_sec_nr and \
                            'https://frejaeid.com/oidc/claims/personalIdentityNumber' in validation:
                            oauth_user.partner_id.social_sec_nr = validation.get(
                                'https://frejaeid.com/oidc/claims/personalIdentityNumber')
                        if not oauth_user.partner_id.country_id and \
                            'https://frejaeid.com/oidc/claims/country' in validation:
                            country = self.env['res.country'].search(
                                [('code', '=', validation.get('https://frejaeid.com/oidc/claims/country'))])
                            if country:
                                oauth_user.partner_id.country_id = country.id
                    return oauth_user.login
                except Exception as e:
                    _logger.error(str(e))
            else:
                raise AccessDenied()
        except AccessDenied as access_denied_exception:
            if self.env.context.get('no_user_creation'):
                return None
            state = json.loads(params['state'])
            token = state.get('t')
            values = self._generate_signup_values(provider, validation, params)
            try:
                _, login, _ = self.signup(values, token)
                return login
            except (SignupError, UserError) as e:
                _logger.error(str(e))
                raise access_denied_exception

    @api.model
    def auth_oauth(self, provider, params):
        # Advice by Google (to avoid Confused Deputy Problem)
        # if validation.audience != OUR_CLIENT_ID:
        #   abort()
        # else:
        #   continue with the process
        oauth_provider = self.env['auth.oauth.provider'].browse(provider)
        access_token = params.get('code') # old way: access_token = params.get('access_token') if oauth_provider.name != 'Freja eID' else params.get('code')
        validation = self._auth_oauth_validate(provider, access_token)
        # required check
        if oauth_provider.name != 'Freja eID':
            if not validation.get('user_id'):
                # Workaround: facebook does not send 'user_id' in Open Graph Api
                if validation.get('id'):
                    validation['user_id'] = validation['id']
                else:
                    raise AccessDenied()

        # retrieve and sign in user
        login = self._auth_oauth_signin(provider, validation, params)
        _logger.error("Login ========")
        _logger.error(login)
        if not login:
            raise AccessDenied()
        # return user credentials
        return (self.env.cr.dbname, login, access_token)
