import tornado.web
import tornado.websocket
from raven.contrib.tornado import SentryMixin

# from ML import Classifier
socket_clients = set()
classifiers = {}


class BaseHandler(SentryMixin, tornado.web.RequestHandler):
    def __init__(self, *args, **kwargs):
        super(BaseHandler, self).__init__(*args, **kwargs)

        # default values
        self.tmpl = {
            'title': '',
            'meta': {
                'description': 'A recognition system for your team.',
                'keywords': 'detect, recognise, facial, detection, team, id, recogniser, id my team, idmy.team'
            },
            'username': self.get_secure_cookie('username'),
            'error_message': self.get_secure_cookie('error_message'),
            'success_message': self.get_secure_cookie('success_message'),
        }

        if self.tmpl['username']:
            self.tmpl['username'] = self.tmpl['username'].decode('utf-8')

        # remove flash messages
        self.clear_cookie('error_message')
        self.clear_cookie('success_message')

    def flash_error(self, message, redirect_url=''):
        self.set_secure_cookie('error_message', message)
        if redirect_url:
            return self.redirect(redirect_url)

    def flash_success(self, message, redirect_url=''):
        self.set_secure_cookie('success_message', message)
        if redirect_url:
            return self.redirect(redirect_url)


class Error404(BaseHandler):
    def get(self):
        self.write('404')


class WelcomeHandler(BaseHandler):
    def get(self):
        self.render('welcome.html', **self.tmpl)


class AboutHandler(BaseHandler):
    def get(self):
        self.tmpl['title'] = 'About'
        self.render('about.html', **self.tmpl)


class ContactHandler(BaseHandler):
    def get(self):
        self.tmpl['title'] = 'Contact'
        self.render('contact.html', **self.tmpl)


class TermsHandler(BaseHandler):
    def get(self):
        self.tmpl['title'] = 'Terms'
        self.render('terms.html', **self.tmpl)


class TutorialListHandler(BaseHandler):
    def get(self):
        self.tmpl['title'] = 'Tutorials'
        self.render('tutorials/list.html', **self.tmpl)


class TutorialHandler(BaseHandler):
    def get(self, name):
        title = name.replace("-", " ").title()
        path = 'tutorials/' + name + '.html'

        self.tmpl['title'] = title
        self.render(path, **self.tmpl)
