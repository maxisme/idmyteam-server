import os

import tornado.httpserver
import tornado.wsgi
from raven.contrib.tornado import AsyncSentryClient
from sqlalchemy import pool
from tornado.ioloop import IOLoop
from tornado.web import url

import view
import web_urls
from settings import config, functions

server_settings = {
    "template_path": os.path.join(os.path.dirname(__file__), "templates"),
    "static_path": os.path.join(os.path.dirname(__file__), 'static'),
    "cookie_secret": config.COOKIE_SECRET,
    "xsrf_cookies": True,
    "debug": True,
    "default_handler_class": view.Error404,
}




class App(tornado.web.Application):
    def __init__(self, *args, **kwargs):
        super(App, self).__init__(*args, **kwargs)
        self.db = pool.QueuePool(self.get_conn, max_overflow=10, pool_size=5)

    def get_conn(self):
        return functions.DB.conn(config.DB["username"], config.DB["password"], config.DB["db"])


app = App(handlers=web_urls.www_urls, **server_settings)
# integrate sentry
app.sentry_client = AsyncSentryClient(
    'https://41ff4de927694cb7bf28dd4ce3e083d0:b1f0d66b3fe447c48fa08f2ef70f2a14@sentry.io/1335020'
)


def main():
    server = tornado.httpserver.HTTPServer(app)
    server.bind(8888)
    if not app.settings['debug']:
        server.start(0)  # all cpus
    else:
        server.start(1)  # 1 cpu
    IOLoop.current().start()


if __name__ == '__main__':
    main()
