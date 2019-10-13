import json
import urllib.request, urllib.parse, urllib.error

import logging
from settings import functions, config, db
from view import BaseHandler
import forms
from ML.classifier import Classifier

clients = {}
logging.basicConfig(level="INFO")


class ProfileHandler(BaseHandler):
    def get(self):
        self.tmpl["title"] = "Profile"
        username = self.tmpl["username"]
        if username:
            hashed_username = functions.hash(username)
            self.conn = db.pool.connect()

            self.tmpl["team"] = team = functions.Team.get(
                self.conn, username=hashed_username
            )
            if self.tmpl["team"]:
                self.tmpl["num_members"] = functions.Team.num_users(
                    self.conn, hashed_username
                )
                self.tmpl["local_ip"] = (
                    clients[hashed_username].local_ip
                    if hashed_username in clients
                    else False
                )
                self.tmpl["has_model"] = Classifier.exists(hashed_username)
                self.tmpl["root_password"] = "zFHbmDM59nQIt5w6eYbWL2KsHHWdk4PQ9laRHZ5b"
                self.tmpl["credentials"] = functions.AESCipher(
                    config.SECRETS["crypto"]
                ).decrypt(team["credentials"])
                self.tmpl["xsrf_token"] = self.xsrf_token
                return self.render("profile.html", **self.tmpl)
            else:
                self.clear_cookie("username")
        return self.redirect("/login")


class LoginHandler(BaseHandler):
    INVALID_MESSAGE = "Invalid credentials! Please try again."

    def __init__(self, *args, **kwargs):
        super(LoginHandler, self).__init__(*args, **kwargs)
        self.tmpl["failed_captcha"] = False

    def get(self):
        self.tmpl["form"] = forms.LoginForm()
        self._screen()

    def post(self):
        self.tmpl["form"] = form = forms.LoginForm(self.request.arguments)
        if self._is_valid_captcha(self.request.arguments):
            if form.validate():
                self.conn = db.pool.connect()
                user = functions.Team.get(
                    self.conn, username=functions.hash(form.username.data)
                )
                if user and functions.check_pw_hash(
                    form.password.data, user["password"]
                ):
                    if user["confirmed_email"]:
                        self.set_secure_cookie("username", form.username.data)
                        return self.redirect("/profile")
                    else:
                        self.flash_error(
                            """You have not confirmed your email! 
                        <a href='/resend?email={}'>
                            Resend confirmation?
                        </a>""".format(
                                user["email"]
                            )
                        )
                else:
                    self.flash_error(self.INVALID_MESSAGE)
        else:
            self.tmpl["failed_captcha"] = True
        return self._screen()

    def _screen(self):
        self.tmpl["title"] = "Login"
        self.render("forms/form.html", **self.tmpl)

    def _is_valid_captcha(self, args):
        # return True
        if "g-recaptcha-response" in args:
            recaptcha_response = args["g-recaptcha-response"][0].decode("utf-8")
            url = "https://www.google.com/recaptcha/api/siteverify"
            values = {
                "secret": config.SECRETS["recaptcha"],
                "response": recaptcha_response,
                "remoteip": self.request.remote_ip,
            }
            data = urllib.parse.urlencode(values).encode("utf-8")
            req = urllib.request.Request(url, data)
            response = urllib.request.urlopen(req)
            return json.load(response)["success"]
        return False


class SignUpHandler(LoginHandler):
    INVALID_SIGNUP_MESSAGE = (
        "Error with user information! Please try a different username or email"
    )

    def get(self):
        self.tmpl["form"] = forms.SignUpForm()
        self._screen()

    def post(self):
        self.tmpl["form"] = form = forms.SignUpForm(self.request.arguments)
        if self._is_valid_captcha(self.request.arguments):
            if form.validate():
                self.conn = db.pool.connect()
                if functions.Team.sign_up(
                    self.conn,
                    form.username.data,
                    form.password.data,
                    form.email.data,
                    form.store.data,
                    config.SECRETS["crypto"],
                ):
                    if functions.Team.ConfirmEmail.send_confirmation(
                        self.conn,
                        form.email.data,
                        form.username.data,
                        config.EMAIL_CONFIG,
                        config.ROOT,
                        config.SECRETS["token"],
                    ):
                        self.flash_success("Please confirm your email!")
                        return self.redirect("/login")
                    else:
                        self.flash_error(self.INVALID_SIGNUP_MESSAGE)
                else:
                    self.flash_error(self.INVALID_SIGNUP_MESSAGE)
            else:
                for error in form.errors:
                    self.flash_error(form.errors[error][0])
                    break
        else:
            self.tmpl["failed_captcha"] = True
        return self._screen()

    def _screen(self):
        self.tmpl["title"] = "Sign Up"
        self.render("forms/form.html", **self.tmpl)


class ForgotPassword(LoginHandler):
    def get(self):
        self.tmpl["form"] = forms.ForgotForm()
        self._screen()

    def _screen(self):
        self.tmpl["title"] = "Forgot Password"
        self.render("forms/form.html", **self.tmpl)

    def post(self):
        self.tmpl["form"] = form = forms.ForgotForm(self.request.arguments)
        if form.validate():
            self.conn = db.pool.connect()
            if form.email.data or form.username.data:
                if form.email.data:
                    args = {"email": form.email.data}
                else:
                    args = {"username": functions.hash(form.username.data)}
                team = functions.Team.get(self.conn, **args)
                if team["email"]:
                    functions.Team.PasswordReset.reset(
                        self.conn,
                        team["email"],
                        config.EMAIL_CONFIG,
                        config.SECRETS["token"],
                        config.ROOT,
                    )
                    return self.flash_success("Sent reset email!", "/")
            else:
                form.errors.append("Please enter either an email or a username.")
        self._screen()


class ResetPassword(LoginHandler):
    SUCCESS = "Success resetting password!"
    ERROR = "Invalid request to reset password."

    def get(self):
        email = self.get_argument("email", "")
        username = self.get_argument("username", "")
        token = self.get_argument("token", "")

        if (email or username) and token:
            self.tmpl["form"] = forms.ResetPasswordForm(
                data={"token": token, "email": email, "username": username}
            )
            self._screen()
        else:
            return self.redirect("/")

    def _screen(self):
        self.tmpl["title"] = "Reset Password"
        self.render("forms/form.html", **self.tmpl)

    def post(self):
        if self._is_valid_captcha(self.request.arguments):
            self.tmpl["form"] = form = forms.ResetPasswordForm(self.request.arguments)
            if form.validate():
                if form.email.data:
                    args = {"email": form.email.data}
                else:
                    args = {"username": functions.hash(form.username.data)}
                self.conn = db.pool.connect()
                team = functions.Team.get(self.conn, **args)
                if team and functions.Team.PasswordReset.validate(
                    self.conn, team["email"], form.token.data, config.SECRETS["token"]
                ):
                    if functions.Team.reset_password(
                        self.conn, form.password.data, **args
                    ):
                        return self.flash_success(self.SUCCESS, "/login")
            return self.flash_error(self.ERROR, "/forgot")
        else:
            self.tmpl["failed_captcha"] = True
        self._screen()
