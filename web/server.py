import os

import tornado.httpserver
import tornado.wsgi
from raven.contrib.tornado import AsyncSentryClient
from sqlalchemy import pool
from tornado.ioloop import IOLoop
from tornado.web import url

import view
import web_urls
from settings import config

server_settings = {
    "template_path": os.path.join(os.path.dirname(__file__), "templates"),
    "static_path": os.path.join(os.path.dirname(__file__), 'static'),
    "cookie_secret": config.SECRETS['cookie'],
    "xsrf_cookies": True,
    "debug": True,
    "default_handler_class": view.Error404,
}

app = tornado.web.Application(handlers=web_urls.www_urls, **server_settings)
app.sentry_client = AsyncSentryClient(config.SENTRY_URL)


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
