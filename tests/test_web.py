import urllib

import tornado
from tornado import escape
from tornado.testing import AsyncHTTPTestCase
from tornado.web import decode_signed_value

import authed
import events
import forms
import server
from settings import functions, config
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

    def setUp(self):
        super(LoginTest, self).setUp()

        # create database
        conn = functions.DB.conn(config.DB["username"], config.DB["password"], '')
        x = conn.cursor()
        x.execute('DROP DATABASE IF EXISTS `{db}`; CREATE DATABASE `{db}`;'.format(db=config.DB["db"]))
        x.close()
        conn.close()

        # create tables
        conn = functions.DB.conn(config.DB["username"], config.DB["password"], config.DB["db"])
        functions.DB.execute_sql_in_file(conn, config.ROOT + "/sql/schema.sql")


    def get_app(self):
        server.server_settings['debug'] = False
        server.server_settings['xsrf_cookies'] = False
        return server.App(server.web_urls.www_urls, **server.server_settings)

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
        cookie = decode_signed_value(config.COOKIE_SECRET, name, self.cookies[name].value)
        if cookie:
            return cookie.decode()
        return None

@mock.patch('smtplib.SMTP')
@mock.patch('authed.LoginHandler._is_valid_captcha', return_value=True)
@mock.patch('settings.functions.Team.ConfirmEmail._gen_template')
class TestWebUrls(LoginTest):
    url_blacklist = [
        '/socket',
        '/local',
        '/upload',
        '/profile'
    ]

    def _signup(self, team):
        form_data = team.__dict__
        form_data['confirm'] = team.password
        form_data['ts'] = True
        self.post('/signup', form_data, follow_redirects=False)
        return form_data

    def _is_logged_in(self):
        return self.fetch('/profile', follow_redirects=False).code == 200  # successfully logged

    def _confirm_account_tests(self, email_token, team):
        # test no token
        self.fetch('/confirm?email={email}&username={username}'.format(token=email_token, **team.__dict__))
        assert self.fetch('/profile', follow_redirects=False).code == 302, 'no token'

        # test no username
        self.fetch('/confirm?email={email}&token={token}'.format(token=email_token, **team.__dict__))
        assert self.fetch('/profile', follow_redirects=False).code == 302, 'no username'

        # test no email
        self.fetch('/confirm?username={username}&token={token}'.format(token=email_token, **team.__dict__))
        assert self.fetch('/profile', follow_redirects=False).code == 302, 'no email'

        # test correct details
        self.fetch('/confirm?email={email}&username={username}&token={token}'.format(token=email_token, **team.__dict__))
        assert self._is_logged_in(), 'correct details'


    def test_urls(self, *args):
        for url in server.web_urls.www_urls:
            if url[1].__module__ != 'events' and url[0] not in self.url_blacklist:
                response = self.fetch(url[0], follow_redirects=False)
                assert response.code == 200, url[0]

    def test_email_confirmation_flow(self, gen_template, *args):
        team = TeamGenerator()
        self._signup(team)
        email_token = gen_template.call_args[1]['token']
        self._confirm_account_tests(email_token, team)

    def test_signup_flow(self, smtp, *args):
        form_data = self._signup(TeamGenerator())
        assert smtp.called, 'SMTP call in handler'

        # test duplicate signup
        self.post('/signup', form_data)
        assert self.get_cookie('error_message') == authed.SignUpHandler.INVALID_SIGNUP_MESSAGE, 'Duplicate signup'

        # test unchecked ts
        form_data.pop('ts')
        self.post('/signup', form_data, follow_redirects=False)
        assert self.get_cookie('error_message') == forms.SignUpForm.TS_MESSAGE, 'Not checked ts'

    def test_email_retry(self, gen_template, *args):
        team = TeamGenerator()
        self.fetch('/resend?email={email}&username={username}'.format(**team.__dict__))
        assert self.get_cookie('error_message') == events.ResendConfirmationEmail.CONFIRMATION_ERROR, 'No such team signed up'

        self._signup(team)
        self.fetch('/resend?email={email}&username={username}'.format(**team.__dict__))
        email_token = gen_template.call_args[1]['token']
        self._confirm_account_tests(email_token, team)

        self.fetch('/resend?email={email}&username={username}'.format(**team.__dict__))
        assert self.get_cookie('error_message') == events.ResendConfirmationEmail.CONFIRMATION_ERROR, 'Already confirmed'

    def test_login(self, gen_template, *args):
        team = TeamGenerator()
        self._signup(team)

        self.post('/login', team.__dict__)
        assert 'not confirmed' in self.get_cookie('error_message'), 'Not yet confirmed'

        # confirm signup
        email_token = gen_template.call_args[1]['token']
        self.fetch('/confirm?email={email}&username={username}&token={token}'.format(token=email_token, **team.__dict__))
        assert self._is_logged_in(), 'logged in'
        self.fetch('/logout')
        assert not self._is_logged_in(), 'logged out'

        # test login
        self.post('/login', team.__dict__)
        assert self._is_logged_in(), 'correct login details'
        self.fetch('/logout')
        assert not self._is_logged_in(), 'logged out'

        # test invalid login details
        self.post('/login', TeamGenerator().__dict__)
        assert self.get_cookie('error_message') == authed.LoginHandler.INVALID_MESSAGE, 'incorrect login details'



