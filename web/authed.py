import json
import urllib.request, urllib.parse, urllib.error

import logging
from settings import functions, config
from view import BaseHandler
import forms
from ML.classifier import Classifier

clients = {}
logging.basicConfig(level='INFO')


class ProfileHandler(BaseHandler):
    def get(self):
        self.tmpl['title'] = 'Profile'
        username = self.tmpl['username']
        if username:
            hashed_username = functions.hash(username)
            self.tmpl['team'] = functions.Team.get(self.conn, hashed_username)
            if self.tmpl['team']:
                self.tmpl['num_members'] = functions.Team.num_users(self.conn, hashed_username)
                self.tmpl['local_ip'] = clients[hashed_username].local_ip if hashed_username in clients else False
                self.tmpl['has_model'] = Classifier.exists(hashed_username)
                self.tmpl['root_password'] = 'zFHbmDM59nQIt5w6eYbWL2KsHHWdk4PQ9laRHZ5b'
                self.tmpl['credentials'] = functions.AESCipher(config.CRYPTO_KEY).decrypt(self.tmpl['team']['credentials'])
                self.tmpl['xsrf_token'] = self.xsrf_token
                return self.render('profile.html', **self.tmpl)
            else:
                self.clear_cookie('username')
        return self.redirect("/login")


class LoginHandler(BaseHandler):
    INVALID_MESSAGE = "Invalid credentials! Please try again."

    def __init__(self, *args, **kwargs):
        super(LoginHandler, self).__init__(*args, **kwargs)
        self.tmpl['failed_captcha'] = False

    def get(self):
        self.tmpl['form'] = forms.LoginForm()
        self._screen()

    def post(self):
        self.tmpl['form'] = form = forms.LoginForm(self.request.arguments)
        if self._is_valid_captcha(self.request.arguments):
            if form.validate():
                conn = functions.DB.conn(config.DB["username"], config.DB["password"], config.DB["db"])
                user = functions.Team.get(conn, functions.hash(form.username.data))
                if user and functions.check_pw_hash(form.password.data, user['password']):
                    if user['confirmed_email']:
                        self.set_secure_cookie('username', form.username.data)
                        return self.redirect('/profile')
                    else:
                        self.flash_error("""You have not confirmed your email! 
                        <a href='/resend?email={}'>
                            Resend confirmation?
                        </a>""".format(user['email']))
                else:
                    self.flash_error(self.INVALID_MESSAGE)
        else:
            self.tmpl['failed_captcha'] = True
        return self._screen()

    def _screen(self):
        self.tmpl['title'] = 'Login'
        self.render('helpers/form.html', **self.tmpl)

    def _is_valid_captcha(self, args):
        # return True
        if 'g-recaptcha-response' in args:
            recaptcha_response = args['g-recaptcha-response'][0].decode('utf-8')
            url = 'https://www.google.com/recaptcha/api/siteverify'
            values = {
                'secret': config.RECAPTCHA_KEY,
                'response': recaptcha_response,
                'remoteip': self.request.remote_ip
            }
            data = urllib.parse.urlencode(values).encode('utf-8')
            req = urllib.request.Request(url, data)
            response = urllib.request.urlopen(req)
            return json.load(response)['success']
        return False


class SignUpHandler(LoginHandler):
    INVALID_SIGNUP_MESSAGE = 'Error with user information! Please try a different username or email'
    def get(self):
        self.tmpl['form'] = forms.SignUpForm()
        self._screen()

    def post(self):
        self.tmpl['form'] = form = forms.SignUpForm(self.request.arguments)
        if self._is_valid_captcha(self.request.arguments):
            if form.validate():
                conn = functions.DB.conn(config.DB["username"], config.DB["password"], config.DB["db"])
                if functions.Team.sign_up(conn, form.username.data, form.password.data,
                                          form.email.data, form.store.data, config.CRYPTO_KEY):
                    functions.Team.ConfirmEmail.send_confirmation(conn, form.email.data, form.username.data,
                                                                  config.EMAIL_CONFIG, config.ROOT)
                else:
                    self.flash_error(self.INVALID_SIGNUP_MESSAGE)
            else:
                for error in form.errors:
                    self.flash_error(form.errors[error][0])
                    break
        else:
            self.tmpl['failed_captcha'] = True

        return self._screen()

    def _screen(self):
        self.tmpl['title'] = 'Sign Up'
        self.render('helpers/form.html', **self.tmpl)


