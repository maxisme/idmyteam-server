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
