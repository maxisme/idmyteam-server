import urllib
from http.cookies import SimpleCookie

import tornado.testing
from tornado import escape
from tornado.web import decode_signed_value

from settings import functions, config
import server


class WebTest(tornado.testing.AsyncHTTPTestCase):
    def __init__(self, *rest):
        self.cookies = SimpleCookie()
        tornado.testing.AsyncHTTPTestCase.__init__(self, *rest)

    def setUp(self):
        super(WebTest, self).setUp()

        # create database
        conn = functions.DB.conn(config.DB["username"], config.DB["password"], "")
        x = conn.cursor()
        x.execute(
            "DROP DATABASE IF EXISTS `{db}`; CREATE DATABASE `{db}`;".format(
                db=config.DB["db"]
            )
        )
        x.close()
        conn.close()

        # create tables
        conn = functions.DB.conn(
            config.DB["username"], config.DB["password"], config.DB["db"]
        )
        functions.DB.execute_sql_in_file(conn, config.ROOT + "/sql/schema.sql")
        conn.close()

    def get_app(self):
        server.server_settings["debug"] = False
        server.server_settings["xsrf_cookies"] = False
        return tornado.web.Application(
            server.web_urls.www_urls, **server.server_settings
        )

    def _update_cookies(self, headers):
        cs = str(headers["Set-Cookie"])
        cs = escape.native_str(cs)
        cookies = cs.split(",")
        for cookie in cookies:
            self.cookies.update(SimpleCookie(cookie))

    def fetch(self, url, *r, **kw):
        if "follow_redirects" not in kw:
            kw["follow_redirects"] = False

        header = {"Cookie": ""}
        for cookie in self.cookies:
            header["Cookie"] += cookie + "=" + self.cookies[cookie].value + "; "

        resp = tornado.testing.AsyncHTTPTestCase.fetch(
            self, url, headers=header, *r, **kw
        )
        self._update_cookies(resp.headers)
        return resp

    def post(self, url, data, *r, **kw):
        body = urllib.parse.urlencode(data)
        return self.fetch(url, body=body, method="POST", *r, **kw)

    def get_cookie(self, name):
        cookie = decode_signed_value(
            config.SECRETS["cookie"], name, self.cookies[name].value
        )
        if cookie:
            return cookie.decode()
        return None

    def _signup(self, team):
        form_data = team.__dict__
        form_data["confirm"] = team.password
        form_data["ts"] = True
        self.post("/signup", form_data, follow_redirects=False)
        return form_data

    def new_team(self, team, template):
        self._signup(team)
        email_token = template.call_args[1]["token"]
        self.fetch(
            "/confirm?email={email}&username={username}&token={token}".format(token=email_token, **team.__dict__))
        assert self._is_logged_in(), "correct details"

    def get_credentials(self, team, decrypt):
        self.post("/login", team.__dict__)
        self.fetch('/profile')
        return decrypt.call_args[0][0]

    def _is_logged_in(self):
        return (
            self.fetch("/profile", follow_redirects=False).code == 200
        )  # successfully logged