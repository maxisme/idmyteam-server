import tornado
from tornado.testing import AsyncHTTPTestCase

import server

class TestWebApp(AsyncHTTPTestCase):
    url_blacklist = [
        '/socket',
        '/local',
        '/upload'
    ]
    def get_app(self):
        self.app = tornado.web.Application(server.web_urls.www_urls, **server.server_settings)
        return self.app

    def test_urls(self):
        for url in server.web_urls.www_urls:
            if url[1].__module__ != 'events' and url[0] not in self.url_blacklist:
                response = self.fetch(url[0])
                assert response.code == 200
