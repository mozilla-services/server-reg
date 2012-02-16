# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
"""
User controller. Implements all APIs from:

https://wiki.mozilla.org/Labs/Weave/User/1.0/API

"""
import os
import traceback
import simplejson as json

from pyramid.response import Response
from pyramid.httpexceptions import (HTTPServiceUnavailable, HTTPBadRequest,
                                    HTTPInternalServerError, HTTPNotFound,
                                    HTTPUnauthorized)

from recaptcha.client import captcha
from cef import log_cef, AUTH_FAILURE, PASSWD_RESET_CLR

from services import logger
from services.util import HTTPJsonBadRequest, valid_password
from services.emailer import send_email, valid_email
from services.formatters import text_response, json_response
from services.user import extract_username
from services.resetcodes import AlreadySentError
from services.respcodes import (ERROR_MISSING_PASSWORD,
                                ERROR_NO_EMAIL_ADDRESS,
                                ERROR_INVALID_WRITE,
                                ERROR_MALFORMED_JSON,
                                ERROR_WEAK_PASSWORD,
                                ERROR_INVALID_USER,
                                ERROR_INVALID_RESET_CODE,
                                ERROR_INVALID_CAPTCHA,
                                ERROR_USERNAME_EMAIL_MISMATCH)
from syncreg.util import render_mako
from services.user import User

from mozsvc.plugin import load_from_settings

_TPL_DIR = os.path.join(os.path.dirname(__file__), 'templates')


def resp_render_mako(*args, **kwds):
    return Response(render_mako(*args, **kwds))


class UserController(object):

    def __init__(self, config):
        settings = config.registry.settings
        self.strict_usernames = settings.get('auth.strict_usernames', True)
        self.shared_secret = settings.get('global.shared_secret')
        if "auth" not in config.registry:
            config.registry["auth"] = load_from_settings("auth", settings)
        self.fallback_node = \
                    self.clean_location(settings.get('nodes.fallback_node'))
        self._captcha_public_key = settings.get("captcha.public_key")
        self._captcha_private_key = settings.get("captcha.private_key")
        self._captcha_use_ssl = settings.get("captcha.use_ssl")

        try:
            self.reset = load_from_settings('reset_codes', settings)
        except Exception:
            logger.debug(traceback.format_exc())
            logger.debug("No reset code library in place")
            self.reset = None

    def user_exists(self, request):
        username = request.matchdict.get("username")
        if username is None:
            raise HTTPNotFound()
        uid = request.registry["auth"].get_user_id({"username": username})
        return text_response(int(uid is not None))

    def return_fallback(self):
        if self.fallback_node is None:
            return json_response(None)
        return text_response(self.fallback_node)

    def clean_location(self, location):
        if location is None:
            return None
        if not location.endswith('/'):
            location += '/'
        if not location.startswith('http'):
            location = 'https://%s' % location
        return location

    def user_node(self, request):
        """Returns the storage node root for the user"""
        # warning:
        # the client expects a string body not a json body
        # except when the node is 'null'

        # IF YOU ARE USING ACTUAL NODE ASSIGNMENT (odds are you're not)
        # There is now a separate assignment module:
        # http://hg.mozilla.org/services/server-node-assignment
        # Install that and point your server at it for
        # the node assignment call

        username = request.matchdict.get("username")
        if username is None:
            raise HTTPNotFound()

        if not request.registry["auth"].get_user_id({"username": username}):
            raise HTTPNotFound()

        return self.return_fallback()

    def password_reset(self, request, **data):
        """Sends an e-mail for a password reset request."""
        if self.reset is None:
            logger.debug('reset attempted, but no resetcode library installed')
            raise HTTPServiceUnavailable()

        user = {"username": request.matchdict["username"]}
        user_id = request.registry["auth"].get_user_id(user)
        if user_id is None:
            # user not found
            raise HTTPJsonBadRequest(ERROR_INVALID_USER)

        request.registry["auth"].get_user_info(user, ['mail'])
        if user.get('mail') is None:
            raise HTTPJsonBadRequest(ERROR_NO_EMAIL_ADDRESS)

        self._check_captcha(request, data)

        try:
            # the request looks fine, let's generate the reset code
            code = self.reset.generate_reset_code(user)

            data = {'host': request.host_url,
                    'user_name': user['username'], 'code': code}
            body = render_mako('password_reset_mail.mako', **data)

            sender = request.registry.settings['smtp.sender']
            host = request.registry.settings['smtp.host']
            port = int(request.registry.settings['smtp.port'])
            mailuser = request.registry.settings.get('smtp.user')
            password = request.registry.settings.get('smtp.password')

            subject = 'Resetting your Services password'
            res, msg = send_email(sender, user['mail'], subject, body,
                                  host, port, mailuser, password)

            if not res:
                raise HTTPServiceUnavailable(msg)
        except AlreadySentError:
            #backend handled the reset code email. Keep going
            pass

        return text_response('success')

    def delete_password_reset(self, request, **data):
        """Forces a password reset clear"""
        if self.reset is None:
            logger.debug('reset attempted, but no resetcode library installed')
            raise HTTPServiceUnavailable()

        self._check_captcha(request, data)
        request.registry["auth"].get_user_id(request.user)
        self.reset.clear_reset_code(request.user)
        log_cef("User requested password reset clear", 9, request.environ,
                request.registry.settings, request.user.get('username'),
                PASSWD_RESET_CLR)
        return text_response('success')

    def _check_captcha(self, request, data):
        # check if captcha info are provided
        if not request.registry.settings.get('captcha.use'):
            return

        challenge = data.get('captcha-challenge')
        response = data.get('captcha-response')

        if challenge is not None and response is not None:
            resp = captcha.submit(challenge, response,
                                  self._captcha_private_key,
                                  remoteip=request.remote_addr)
            if not resp.is_valid:
                raise HTTPJsonBadRequest(ERROR_INVALID_CAPTCHA)
        else:
            raise HTTPJsonBadRequest(ERROR_INVALID_CAPTCHA)

    def create_user(self, request):
        """Creates a user."""
        username = request.matchdict["username"]
        if request.registry["auth"].get_user_id({"username": username}):
            raise HTTPJsonBadRequest(ERROR_INVALID_WRITE)

        try:
            data = json.loads(request.body)
        except ValueError:
            raise HTTPJsonBadRequest(ERROR_MALFORMED_JSON)

        email = data.get('email')
        if email and not valid_email(email):
            raise HTTPJsonBadRequest(ERROR_NO_EMAIL_ADDRESS)

        # checking that the e-mail matches the username
        munged_email = extract_username(email)
        if munged_email != username and self.strict_usernames:
            raise HTTPJsonBadRequest(ERROR_USERNAME_EMAIL_MISMATCH)

        password = data.get('password')
        if not password:
            raise HTTPJsonBadRequest(ERROR_MISSING_PASSWORD)

        if not valid_password(username, password):
            raise HTTPJsonBadRequest(ERROR_WEAK_PASSWORD)

        # check if captcha info are provided or if we bypass it
        if (self.shared_secret is None or
            request.headers.get('X-Weave-Secret') != self.shared_secret):
            self._check_captcha(request, data)

        # all looks good, let's create the user
        if not request.registry["auth"].create_user(username, password, email):
            raise HTTPInternalServerError('User creation failed.')

        return text_response(username)

    def change_email(self, request):
        """Changes the user e-mail"""
        # the body is in plain text
        email = request.body

        if not valid_email(email):
            raise HTTPJsonBadRequest(ERROR_NO_EMAIL_ADDRESS)

        if not request.user or "password" not in request.user:
            raise HTTPBadRequest()

        if not request.registry["auth"].update_field(request.user,
                                                     request.user["password"],
                                                     'mail', email):
            raise HTTPInternalServerError('User update failed.')

        return text_response(email)

    def change_password(self, request):
        """Changes the user's password

        Takes a classical authentication or a reset code
        """
        username = request.matchdict["username"]
        # the body is in plain text utf8 string
        new_password = request.body.decode('utf8')

        if not valid_password(username, new_password):
            raise HTTPBadRequest('Password should be at least 8 '
                                 'characters and not the same as your '
                                 'username')

        key = request.headers.get('X-Weave-Password-Reset')

        if key is not None:
            user = {"username": username}
            user_id = request.registry["auth"].get_user_id(user)

            if user_id is None:
                raise HTTPNotFound()

            if not self.reset.verify_reset_code(user, key):
                log_cef('Invalid Reset Code submitted', 5, request.environ,
                        request.registry.settings, username,
                        'InvalidResetCode', submitedtoken=key)

                raise HTTPJsonBadRequest(ERROR_INVALID_RESET_CODE)

            if not request.registry["auth"].admin_update_password(user,
                                                   new_password, key):
                raise HTTPInternalServerError('Password change failed '
                                              'unexpectedly.')
        else:
            # classical auth, authenticate by accessing request.user.
            user = request.user

            if user['userid'] is None:
                log_cef('User Authentication Failed', 5, request.environ,
                        request.registry.settings, username,
                        AUTH_FAILURE)
                raise HTTPUnauthorized()

            if not request.registry["auth"].update_password(user,
                                                            user["password"],
                                                            new_password):
                raise HTTPInternalServerError('Password change failed '
                                              'unexpectedly.')

        return text_response('success')

    def password_reset_form(self, request, **kw):
        """Returns a form for resetting the password"""
        if not kw:
            kw = request.GET
        if 'key' in kw or 'error' in kw:
            # we have a key, let's display the key controlling form
            return resp_render_mako('password_reset_form.mako', **kw)
        elif not request.POST and not request.GET:
            # asking for the first time
            return resp_render_mako('password_ask_reset_form.mako')

        raise HTTPBadRequest()

    def _repost(self, request, error):
        request.POST['error'] = error
        return self.password_reset_form(request, **dict(request.POST))

    def do_password_reset(self, request):
        """Do a password reset."""
        if self.reset is None:
            logger.debug('reset attempted, but no resetcode library installed')
            raise HTTPServiceUnavailable()

        user_name = request.POST.get('username')
        if user_name is not None:
            user_name = extract_username(user_name)

        if request.POST.keys() == ['username']:
            # setting up a password reset
            # XXX add support for captcha here via **data
            request.matchdict = {"username": user_name}
            try:
                self.password_reset(request)
            except (HTTPServiceUnavailable, HTTPJsonBadRequest), e:
                return resp_render_mako('password_failure.mako',
                                        error=e.detail)
            else:
                return resp_render_mako('password_key_sent.mako')

            raise HTTPJsonBadRequest()

        # full form, the actual password reset
        password = request.POST.get('password')
        confirm = request.POST.get('confirm')
        key = request.POST.get('key')

        if key is None:
            raise HTTPJsonBadRequest()

        if user_name is None:
            return self._repost(request,
                                'Username not provided. Please check '
                                'the link you used.')

        user = User(user_name)
        user_id = request.registry["auth"].get_user_id(user)
        if user_id is None:
            return self._repost(request, 'We are unable to locate your '
                                'account')

        if password is None:
            return self._repost(request, 'Password not provided. '
                                'Please check the link you used.')

        if password != confirm:
            return self._repost(request, 'Password and confirmation do '
                                'not match')

        if not valid_password(user_name, password):
            return self._repost(request, 'Password should be at least 8 '
                                'characters and not the same as your '
                                'username')

        if not self.reset.verify_reset_code(user, key):
            return self._repost(request, 'Key does not match with username. '
                                'Please request a new key.')

        # everything looks fine
        if not request.registry["auth"].admin_update_password(user, 'password',
                                                              password):
            return self._repost(request, 'Password change failed '
                                         'unexpectedly.')

        self.reset.clear_reset_code(user)
        return resp_render_mako('password_changed.mako')

    def delete_user(self, request):
        """Deletes the user."""

        if not request.user or "password" not in request.user:
            raise HTTPBadRequest()

        res = request.registry["auth"].delete_user(request.user,
                                                   request.user["password"])
        return text_response(int(res))

    def _captcha(self):
        """Return HTML string for inserting recaptcha into a form."""
        return captcha.displayhtml(self._captcha_public_key,
                                   self._captcha_use_ssl)

    def captcha_form(self, request):
        """Renders the captcha form"""
        if not request.registry.settings.get('captcha.use'):
            raise HTTPNotFound('No captcha configured')

        return resp_render_mako('captcha.mako', captcha=self._captcha())
