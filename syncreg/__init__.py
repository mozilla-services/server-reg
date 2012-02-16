# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import logging
logger = logging.getLogger('SyncReg')

from mozsvc.config import get_configurator

from syncreg.controllers.user import UserController
from syncreg.controllers.static import StaticController


API_VERSION = '{api:1.0|1}'


def includeme(config):
    config.include("cornice")
    config.include("mozsvc")
    config.include("mozsvc.user.whoauth")
    config.scan("syncreg.views")
    # Create the "controller" objects.  This is a vestiage of the
    # pre-pyramid codebase and will probably go away in the future.
    config.registry["syncreg.controller.user"] = UserController(config)
    config.registry["syncreg.controller.static"] = StaticController(config)


def main(global_config, **settings):
    config = get_configurator(global_config, **settings)
    config.include(includeme)
    return config.make_wsgi_app()
