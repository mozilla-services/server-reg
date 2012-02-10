# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
"""
Application entry point.
"""
from services.baseapp import set_app
from services.wsgiauth import Authentication

from syncreg.controllers.user import UserController
from syncreg.controllers.static import StaticController


_EXTRAS = {'auth': True}


def _url(url):
    for pattern, replacer in (('_API_', '{api:1.0|1}'),
                              ('_USERNAME_',
                               '{username:[a-zA-Z0-9._-]+}')):
        url = url.replace(pattern, replacer)
    return url


urls = [('GET', _url('/user/_API_/_USERNAME_'), 'user', 'user_exists'),
        ('PUT', _url('/user/_API_/_USERNAME_'), 'user', 'create_user'),
        ('DELETE', _url('/user/_API_/_USERNAME_'), 'user', 'delete_user',
         _EXTRAS),
        ('GET', _url('/user/_API_/_USERNAME_/node/weave'), 'user',
         'user_node'),
        ('GET', _url('/user/_API_/_USERNAME_/password_reset'), 'user',
         'password_reset'),
        ('DELETE', _url('/user/_API_/_USERNAME_/password_reset'), 'user',
         'delete_password_reset', _EXTRAS),
        ('POST', _url('/user/_API_/_USERNAME_/email'), 'user', 'change_email',
         _EXTRAS),
        ('POST', _url('/user/_API_/_USERNAME_/password'), 'user',
         'change_password'),

        # UI
        ('GET', '/weave-password-reset', 'user', 'password_reset_form'),
        ('POST', '/weave-password-reset', 'user', 'do_password_reset'),
        (('GET', 'POST'), _url('/misc/_API_/captcha_html'), 'user',
         'captcha_form'),
        # media   XXX served by Apache in real production
        ('GET', '/media/{filename}', 'static', 'get_file')]


controllers = {'user': UserController, 'static': StaticController}
make_app = set_app(urls, controllers, auth_class=Authentication)
