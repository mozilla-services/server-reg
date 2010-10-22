# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is Sync Server
#
# The Initial Developer of the Original Code is the Mozilla Foundation.
# Portions created by the Initial Developer are Copyright (C) 2010
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   Tarek Ziade (tarek@mozilla.com)
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****
"""
Application entry point.
"""
from synccore.baseapp import set_app

from syncreg.controllers.user import UserController
from syncreg.controllers.static import StaticController

urls = [('GET', '/user/_API_/_USERNAME_', 'user', 'user_exists', False),
        ('PUT', '/user/_API_/_USERNAME_', 'user', 'create_user', False),
        ('DELETE', '/user/_API_/_USERNAME_', 'user', 'delete_user', True),
        ('GET', '/user/_API_/_USERNAME_/node/weave', 'user', 'user_node',
         False),
        ('GET', '/user/_API_/_USERNAME_/password_reset', 'user',
         'password_reset', True),
        ('DELETE', '/user/_API_/_USERNAME_/password_reset', 'user',
         'delete_password_reset', True),
        ('POST', '/user/_API_/_USERNAME_/email', 'user', 'change_email',
         True),
        ('GET', '/weave-password-reset', 'user', 'password_reset_form', False),
        ('POST', '/weave-password-reset', 'user', 'do_password_reset', False),
        (('GET', 'POST'), '/misc/_API_/captcha_html', 'user', 'captcha_form',
         False),
        # media   XXX served by Apache in real production
        ('GET', '/media/{filename}', 'static', 'get_file', False)]


controllers = {'user': UserController, 'static': StaticController}
make_app = set_app(urls, controllers)
