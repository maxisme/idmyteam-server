import os
import smtplib
import time
import urllib

import tornado
from tornado import escape
from tornado.testing import AsyncHTTPTestCase
from tornado.web import RequestHandler, decode_signed_value

import authed
import forms
import server
from settings import functions, config
from tests import DBHelper
import mock
from faker import Factory
from http.cookies import SimpleCookie


class TeamGenerator(object):
    def __init__(self):
        fake = Factory.create()
        self.username = fake.user_name()
        self.email = fake.email()
        self.password = fake.password()
        self.allow_storage = fake.boolean()


class LoginTest(tornado.testing.AsyncHTTPTestCase):
    def __init__(self, *rest):
        self.cookies = SimpleCookie()
        tornado.testing.AsyncHTTPTestCase.__init__(self, *rest)

    def get_app(self):
        server.server_settings['debug'] = False
        server.server_settings['xsrf_cookies'] = False
        return tornado.web.Application(server.web_urls.www_urls, **server.server_settings)

    def _update_cookies(self, headers):
        cs = str(headers['Set-Cookie'])
        cs = escape.native_str(cs)
        cookies = cs.split(',')
        for cookie in cookies:
            self.cookies.update(SimpleCookie(cookie))

    def fetch(self, url, *r, **kw):
        if 'follow_redirects' not in kw:
            kw['follow_redirects'] = False

        header = {
            'Cookie': '',
        }
        for cookie in self.cookies:
            header['Cookie'] += cookie + '=' + self.cookies[cookie].value + '; '

        resp = tornado.testing.AsyncHTTPTestCase.fetch(self, url, headers=header, *r, **kw)
        self._update_cookies(resp.headers)
        return resp

    def post(self, url, data, *r, **kw):
        body = urllib.parse.urlencode(data)
        return self.fetch(url, body=body, method='POST', *r, **kw)

    def get_cookie(self, name):
        return decode_signed_value(config.COOKIE_SECRET, name, self.cookies[name].value).decode()

class TestWebApp(LoginTest):
    url_blacklist = [
        '/socket',
        '/local',
        '/upload',
        '/profile'
    ]

    def test_urls(self):
        for url in server.web_urls.www_urls:
            if url[1].__module__ != 'events' and url[0] not in self.url_blacklist:
                response = self.fetch(url[0], follow_redirects=False)
                assert response.code == 200, url[0]

    @mock.patch('smtplib.SMTP')
    def test_email_confirmation_flow(self, *args):
        # init db
        sql_helper = DBHelper()
        sql_helper.init_schema(config.ROOT)
        conn = sql_helper.conn

        # gen fake team
        team = TeamGenerator()

        # signup functions from SignUpHandler
        functions.Team.sign_up(conn=conn, key=config.CRYPTO_KEY, **team.__dict__)
        email_token = functions.Team.ConfirmEmail.send_confirmation(conn,
                                                                    email=team.email,
                                                                    username=team.username,
                                                                    email_config=config.EMAIL_CONFIG,
                                                                    root=config.ROOT)

        # test no token
        self.fetch('/confirm?email={email}&username={username}'.format(token=email_token, **team.__dict__))
        assert self.fetch('/profile', follow_redirects=False).code == 302, 'no token'

        # test no username
        self.fetch('/confirm?email={email}&token={token}'.format(token=email_token, **team.__dict__))
        assert self.fetch('/profile', follow_redirects=False).code == 302, 'no username'

        # test no email
        self.fetch('/confirm?username={username}&token={token}'.format(token=email_token, **team.__dict__))
        assert self.fetch('/profile', follow_redirects=False).code == 302, 'no email'

        self.fetch('/confirm?email={email}&username={username}&token={token}'.format(token=email_token, **team.__dict__))
        assert self.fetch('/profile', follow_redirects=False).code == 200, 'correct details'  # successfully logged in

    @mock.patch('authed.LoginHandler._is_valid_captcha', return_value=True)
    @mock.patch('smtplib.SMTP')
    def test_signup_flow(self, smtp, _):
        # init db
        sql_helper = DBHelper()
        sql_helper.init_schema(config.ROOT)

        # gen signup form data
        team = TeamGenerator()
        data = team.__dict__
        data['confirm'] = team.password
        data['ts'] = True

        # initiate signup
        self.post('/signup', data, follow_redirects=False)
        assert smtp.called, 'SMTP called in handler'

        # test duplicate signup
        self.post('/signup', data)
        assert self.get_cookie('error_message') == authed.SignUpHandler.INVALID_SIGNUP_MESSAGE, 'Duplicate signup'

        # test unchecked ts
        data.pop('ts')
        self.post('/signup', data, follow_redirects=False)
        assert self.get_cookie('error_message') == forms.SignUpForm.TS_MESSAGE, 'Not checked ts'



