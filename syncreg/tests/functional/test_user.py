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
Basic tests to verify that the dispatching mechanism works.
"""
import base64
import json
import time
import random
import smtplib
from email import message_from_string

from recaptcha.client import captcha

from syncreg.tests.functional import support
from services.tests.support import get_app
from services.util import extract_username


class FakeSMTP(object):

    msgs = []

    def __init__(self, *args, **kw):
        pass

    def quit(self):
        pass

    def sendmail(self, sender, rcpts, msg):
        self.msgs.append((sender, rcpts, msg))


class FakeCaptchaResponse(object):

    is_valid = True


class TestUser(support.TestWsgiApp):

    def setUp(self):
        super(TestUser, self).setUp()
        # user auth token
        token = base64.encodestring('%s:%s' % (self.user_name, self.password))
        environ = {'HTTP_AUTHORIZATION': 'Basic %s' % token}
        self.app.extra_environ = environ
        self.root = '/user/1.0/%s' % self.user_name
        # we don't want to send emails for real
        self.old = smtplib.SMTP
        smtplib.SMTP = FakeSMTP

        # we don't want to call recaptcha either
        self.old_submit = captcha.submit
        captcha.submit = self._submit

    def tearDown(self):
        # setting back smtp and recaptcha
        smtplib.SMTP = self.old
        captcha.submit = self.old_submit
        FakeSMTP.msgs[:] = []
        super(TestUser, self).tearDown()

    def _submit(self, *args, **kw):
        return FakeCaptchaResponse()

    def test_invalid_token(self):
        environ = {'HTTP_AUTHORIZATION': 'FOooo baar'}
        self.app.extra_environ = environ
        self.app.get(self.root + '/password_reset', status=401)

    def test_user_exists(self):
        res = self.app.get(self.root)
        self.assertTrue(json.loads(res.body))

    def test_user_node(self):
        res = self.app.get(self.root + '/node/weave')
        self.assertTrue(res.body, 'http://localhost')

    def test_password_reset(self):
        # making sure a mail is sent
        res = self.app.get(self.root + '/password_reset')
        self.assertEquals(res.body, 'success')
        self.assertEquals(len(FakeSMTP.msgs), 1)

        # let's try some bad POSTs on weave-password-reset
        self.app.post('/weave-password-reset',
                      params={'username': self.user_name,
                              'boo': 'foo'}, status=400)

        res = self.app.post('/weave-password-reset',
                      params={'username': self.user_name, 'key': 'xxx',
                              'boo': 'foo'})
        self.assertTrue('Password not provided' in res)

        # let's ask via the web form now
        res = self.app.get('/weave-password-reset')
        res.form['username'].value = self.user_name
        res = res.form.submit()
        self.assertTrue('next 6 hours' in res)
        self.assertEquals(len(FakeSMTP.msgs), 2)

        # let's visit the link in the email
        msg = message_from_string(FakeSMTP.msgs[1][2]).get_payload()
        msg = base64.decodestring(msg)
        link = msg.split('\n')[2].strip()

        # let's try some bad links (unknown user)
        badlink = link.replace(self.user_name, 'joe')
        res = self.app.get(badlink)
        res.form['password'].value = 'p' * 8
        res.form['confirm'].value = 'p' * 8
        res = res.form.submit()
        self.assertTrue('unable to locate your account' in res)

        badlink = link.replace('username=%s&' % self.user_name, '')
        res = self.app.get(badlink)
        res.form['password'].value = 'p' * 8
        res.form['confirm'].value = 'p' * 8
        res = res.form.submit()
        self.assertTrue('Username not provided' in res)

        # let's call the real link, it's a form we can fill
        # let's try bad values
        # mismatch
        res = self.app.get(link)
        res.form['password'].value = 'mynewpassword'
        res.form['confirm'].value = 'badconfirmation'
        res = res.form.submit()
        self.assertTrue('do not match' in res)

        # weak password
        res = self.app.get(link)
        res.form['password'].value = 'my'
        res.form['confirm'].value = 'my'
        res = res.form.submit()
        self.assertTrue('at least 8' in res)

        # wrong key
        if link[:-1] != 'X':
            res = self.app.get(link[:-1] + 'X')
        else:
            res = self.app.get(link[:-1] + 'Y')
        res.form['password'].value = 'mynewpassword'
        res.form['confirm'].value = 'mynewpassword'
        res = res.form.submit()
        self.assertTrue('Key does not match with username' in res)

        # all good
        res = self.app.get(link)
        res.form['password'].value = 'mynewpassword'
        res.form['confirm'].value = 'mynewpassword'
        res = res.form.submit()
        self.assertTrue('Password successfully changed' in res)

    def test_reset_email(self):
        # let's try the reset process with an email
        user_name = extract_username('tarek@mozilla.com')
        self.auth.create_user(user_name, self.password,
                              'tarek@mozilla.con')

        res = self.app.get('/weave-password-reset')
        res.form['username'].value = 'tarek@mozilla.com'
        res = res.form.submit()
        self.assertTrue('next 6 hours' in res)
        self.assertEquals(len(FakeSMTP.msgs), 1)

        # let's visit the link in the email
        msg = message_from_string(FakeSMTP.msgs[0][2]).get_payload()
        msg = base64.decodestring(msg)
        link = msg.split('\n')[2].strip()

        # let's call the real link, it's a form we can fill
        res = self.app.get(link)
        res.form['password'].value = 'mynewpassword'
        res.form['confirm'].value = 'mynewpassword'
        res = res.form.submit()
        self.assertTrue('Password successfully changed' in res)

    def test_force_reset(self):
        res = self.app.get(self.root + '/password_reset')
        self.assertEquals(res.body, 'success')
        self.assertEquals(len(FakeSMTP.msgs), 1)

        # let's ask via the web form now
        res = self.app.get('/weave-password-reset')
        res.form['username'].value = self.user_name
        res = res.form.submit()
        self.assertTrue('next 6 hours' in res)
        self.assertEquals(len(FakeSMTP.msgs), 2)

        # let's cancel via the API
        url = self.root + '/password_reset'
        app = get_app(self.app)
        if app.config['captcha.use']:
            url += '?captcha-challenge=xxx&captcha-response=xxx'

        res = self.app.delete(url)
        self.assertEquals(res.body, 'success')

    def test_create_user(self):
        # creating a user
        new = 'test_user%d%d' % (time.time(), random.randint(1, 100))

        try:
            # the user already exists
            payload = {'email': 'tarek@ziade.org', 'password': 'x' * 9}
            payload = json.dumps(payload)
            self.app.put(self.root, params=payload, status=400)

            # missing the password
            payload = {'email': 'tarek@ziade.org'}
            payload = json.dumps(payload)
            self.app.put('/user/1.0/%s' % new, params=payload, status=400)

            # malformed e-mail
            payload = {'email': 'tarekziadeorg', 'password': 'x' * 9}
            payload = json.dumps(payload)
            self.app.put('/user/1.0/%s' % new, params=payload, status=400)

            # weak password
            payload = {'email': 'tarek@ziade.org', 'password': 'x'}
            payload = json.dumps(payload)
            self.app.put('/user/1.0/%s' % new, params=payload, status=400)

            # weak password #2
            payload = {'email': 'tarek@ziade.org', 'password': 'tarek2'}
            payload = json.dumps(payload)
            self.app.put('/user/1.0/%s' % new, params=payload, status=400)

            # everything is there
            res = self.app.get('/user/1.0/%s' % new)
            self.assertFalse(json.loads(res.body))

            payload = {'email': 'tarek@ziade.org', 'password': 'x' * 9,
                    'captcha-challenge': 'xxx',
                    'captcha-response': 'xxx'}
            payload = json.dumps(payload)
            res = self.app.put('/user/1.0/%s' % new, params=payload)
            self.assertEquals(res.body, new)

            res = self.app.get('/user/1.0/%s' % new)
            self.assertTrue(json.loads(res.body))
        finally:
            self.auth.delete_user(new, 'x' * 9)

    def test_change_email(self):
        # bad email
        body = 'newemail.com'
        self.app.post(self.root + '/email', params=body, status=400)

        # good one
        body = 'new@email.com'
        res = self.app.post(self.root + '/email', params=body)
        self.assertEquals(res.body, 'new@email.com')

    def test_change_password(self):
        body = 'newpasswordhere'
        res = self.app.post(self.root + '/password', params=body)
        self.assertEquals(res.body, 'success')
        token = base64.encodestring('%s:%s' % (self.user_name, body))
        environ = {'HTTP_AUTHORIZATION': 'Basic %s' % token}
        self.app.extra_environ = environ
        self.app.post(self.root + '/password', params='short', status=400)
        self.app.post(self.root + '/password', params=self.password)
        token = base64.encodestring('%s:%s' % (self.user_name, self.password))
        environ = {'HTTP_AUTHORIZATION': 'Basic %s' % token}
        self.app.extra_environ = environ

    def test_delete_user(self):
        # creating another user
        res = self.app.get(self.root + '2')
        if not json.loads(res.body):
            payload = {'email': 'tarek@ziade.org',
                       'password': 'x' * 9,
                       'captcha-challenge': 'xxx',
                       'captcha-response': 'xxx'}
            payload = json.dumps(payload)
            self.app.put(self.root + '2', params=payload)

        # trying to suppress 'tarek' with 'tarek2'
        # this should generate a 401
        environ = {'HTTP_AUTHORIZATION': 'Basic %s' % \
                       base64.encodestring('tarek2:xxxxxxxxx')}
        self.app.extra_environ = environ
        self.app.delete(self.root + '', status=401)

        # now using the right credentials
        token = base64.encodestring('%s:%s' % (self.user_name, self.password))
        environ = {'HTTP_AUTHORIZATION': 'Basic %s' % token}
        self.app.extra_environ = environ
        res = self.app.delete(self.root)
        self.assertTrue(json.loads(res.body))

        # tarek should be gone
        res = self.app.get(self.root + '')
        self.assertFalse(json.loads(res.body))

    def test_recaptcha(self):
        # make sre the captcha is rendered
        self.app.get('/misc/1.0/captcha_html', status=200)

    def esting_proxy(self):
        # XXX crazy dive into the middleware stack
        app = get_app(self.app)
        app.config['auth.proxy'] = True
        app.config['auth.proxy_scheme'] = 'http'
        app.config['auth.proxy_location'] = 'localhost:5000'

        # these tests should work fine with a proxy config
        res = self.app.get('/user/1.0/randomdude')
        if not json.loads(res.body):
            self.app.delete('/user/1.0/randomdude')

        self.test_create_user('randomdude')

    def test_fallback_node(self):
        app = get_app(self.app)
        proxy = app.config['auth.fallback_node'] = 'http://myhappy/proxy/'
        url = '/user/1.0/%s/node/weave' % self.user_name
        res = self.app.get(url)
        self.assertEqual(res.body, proxy)

        del app.config['auth.fallback_node']
        res = self.app.get(url)
        self.assertEqual(res.body, 'http://localhost/')

    def test_prevent_bad_node(self):
        app = get_app(self.app)
        old_auth = app.auth.backend.get_user_id
        def _get_id(*args):
            return None
        app.auth.backend.get_user_id = _get_id
        try:
            self.app.get('/user/1.0/%s/node/weave' % self.user_name,
                         status=503)
        finally:
            app.auth.backend.get_user_id = old_auth
