# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
""" Base test class, with an instanciated app.
"""
import os
import unittest
import random
import traceback

from webtest import TestApp

from syncreg.tests.support import initenv
from syncreg.wsgiapp import make_app
from services.user import extract_username
from services.user import User
from services.pluginreg import load_and_configure
from syncreg import logger


class TestWsgiApp(unittest.TestCase):

    def setUp(self):
        # loading the app
        self.appdir, self.config, self.auth = initenv()
        self.sqlfile = self.auth.sqluri.split('sqlite:///')[-1]
        self.app = TestApp(make_app(self.config))

        # adding a user if needed
        self.email = 'test_user%d@mozilla.com' % random.randint(1, 1000)
        self.user_name = extract_username(self.email)
        self.user = User(self.user_name)
        self.user_id = self.auth.get_user_id(self.user)
        self.password = 'x' * 9

        if self.user_id is None:
            self.auth.create_user(self.user_name, self.password, self.email)
            self.user_id = self.auth.get_user_id(self.user)

        # for the ldap backend, filling available_nodes
        if self.auth.__class__.__name__ == 'LDAPAuth':
            query = ('insert into available_nodes (node, ct, actives) values '
                     ' ("weave:localhost", 10, 10)')
            self.auth._engine.execute(query)

        try:
            self.nodes = load_and_configure(self.config, 'nodes')
        except KeyError:
            logger.debug(traceback.format_exc())
            logger.debug("No node library in place")
            self.nodes = None

        try:
            self.reset = load_and_configure(self.config, 'reset_codes')
        except Exception:
            logger.debug(traceback.format_exc())
            logger.debug("No reset code library in place")
            self.reset = None

    def tearDown(self):
        self.auth.delete_user(self.user, self.password)
        cef_logs = os.path.join(self.appdir, 'test_cef.log')
        if os.path.exists(cef_logs):
            os.remove(cef_logs)

        if os.path.exists(self.sqlfile):
            os.remove(self.sqlfile)
        else:
            self.auth._engine.execute('truncate users')
            self.auth._engine.execute('truncate collections')
            self.auth._engine.execute('truncate wbo')
            if self.auth.get_name() == 'ldap':
                self.auth._engine.execute('truncate available_nodes')
