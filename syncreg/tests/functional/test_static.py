# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
"""
Basic tests to verify that the dispatching mechanism works.
"""
from syncreg.tests.functional import support


class TestUser(support.TestWsgiApp):

    def test_file(self):
        # make sure we can get files
        self.app.get('/media/nothere', status=404)

        res = self.app.get('/media/forgot_password.css')
        self.assertEquals(res.headers['Content-Type'],
                          'text/html; charset=UTF-8')
