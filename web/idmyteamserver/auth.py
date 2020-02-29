from django.contrib.auth import authenticate, logout
from django.http import HttpResponseRedirect

from idmyteamserver.helpers import ERROR_COOKIE_KEY
from idmyteamserver.views import render
from settings import functions, config, db
from web import forms

clients = {}


# def profile_handler(request):
#     if request.user.is_authenticated:
#
#         context = {}
#         context["team"] = team = functions.Team.get(
#             self.conn, username=hashed_username
#         )
#         if context["team"]:
#             context["num_members"] = functions.Team.num_users(
#                 self.conn, hashed_username
#             )
#             context["num_members"] = functions.Team.num_users(
#                 self.conn, hashed_username
#             )
#             context["num_images"] = functions.Team.num_stored_images(
#                 hashed_username, config.STORE_IMAGES_DIR
#             )
#             context["local_ip"] = (
#                 clients[hashed_username].local_ip
#                 if hashed_username in clients
#                 else False
#             )
#             context["has_model"] = Classifier.exists(hashed_username)
#             context["root_password"] = "zFHbmDM59nQIt5w6eYbWL2KsHHWdk4PQ9laRHZ5b"
#             context["credentials"] = functions.AESCipher(
#                 config.SECRETS["crypto"]
#             ).decrypt(team["credentials"])
#             context["xsrf_token"] = self.xsrf_token
#             return render(request, "profile.html", context)
#         else:
#             self.clear_cookie("username")
#     return self.redirect("/login")


def view_stored_images_handler(request):
    context = {"title": "Stored Images"}
    if request.user.is_authenticated():
        context["images"] = functions.Team.get_stored_images(
            functions.hash(request.user.username), config.STORE_IMAGES_DIR
        )
        return render("profile/images.html", context)
    return HttpResponseRedirect("/")


INVALID_LOGIN_MESSAGE = "Invalid credentials! Please try again."
INVALID_SIGNUP_MESSAGE = (
    "Error with user information! Please try a different username or email"
)


def login_handler(request):
    cookies = {}
    if request.method == "POST":
        form = forms.LoginForm(request.POST)
        if form.validate():
            user = authenticate(request.POST)
            if user and user["confirmed_email"]:
                return HttpResponseRedirect("/profile")
            else:
                logout(request)
                cookies = {
                    ERROR_COOKIE_KEY: """
                    You have not confirmed your email! <a href='/resend?email={}'>Resend confirmation?</a>
                    """.format(
                        user["email"]
                    )
                }
        else:
            cookies = {ERROR_COOKIE_KEY: INVALID_LOGIN_MESSAGE}
    else:
        form = forms.LoginForm()
    return render(
        request, "forms/form.html", {"title": "Login", "form": form}, cookies=cookies
    )


def signup_handler(request):
    cookies = {}
    if request.method == "POST":
        form = forms.SignUpForm(request.POST)
        if form.is_valid():
            form.save()
            if functions.Team.ConfirmEmail.send_confirmation(
                    self.conn,
                    form.email.data,
                    form.username.data,
                    config.EMAIL_CONFIG,
                    config.ROOT,
                    config.SECRETS["token"],
            ):
    else:
        form = forms.SignUpForm()

    return render(
        request, "forms/form.html", {"title": "Login", "form": form}, cookies=cookies
    )


# context["form"] = form = forms.SignUpForm(self.request.arguments)
# if self._is_valid_captcha(self.request.arguments):
#     if form.validate():
#         self.conn = db.pool.raw_connection()
#         if functions.Team.sign_up(
#                 self.conn,
#                 form.username.data,
#                 form.password.data,
#                 form.email.data,
#                 form.store.data,
#                 config.SECRETS["crypto"],
#         ):
#             if functions.Team.ConfirmEmail.send_confirmation(
#                     self.conn,
#                     form.email.data,
#                     form.username.data,
#                     config.EMAIL_CONFIG,
#                     config.ROOT,
#                     config.SECRETS["token"],
#             ):
#                 self.flash_success("Please confirm your email!")
#                 return self.redirect("/login")
#             else:
#                 self.flash_error(self.INVALID_SIGNUP_MESSAGE)
#         else:
#             self.flash_error(self.INVALID_SIGNUP_MESSAGE)
#     else:
#         for error in form.errors:
#             self.flash_error(form.errors[error][0])
#             break
# else:
#     context["failed_captcha"] = True
# return self._screen()

def _screen(self):
    context["title"] = "Sign Up"
    self.render("forms/form.html", **context)


class ForgotPassword(LoginHandler):
    def get(self):
        context["form"] = forms.ForgotForm()
        self._screen()

    def _screen(self):
        context["title"] = "Forgot Password"
        self.render("forms/form.html", **context)

    def post(self):
        context["form"] = form = forms.ForgotForm(self.request.arguments)
        if form.validate():
            self.conn = db.pool.raw_connection()
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
            context["form"] = forms.ResetPasswordForm(
                data={"token": token, "email": email, "username": username}
            )
            self._screen()
        else:
            return self.redirect("/")

    def _screen(self):
        context["title"] = "Reset Password"
        self.render("forms/form.html", **context)

    def post(self):
        if self._is_valid_captcha(self.request.arguments):
            context["form"] = form = forms.ResetPasswordForm(self.request.arguments)
            if form.validate():
                if form.email.data:
                    args = {"email": form.email.data}
                else:
                    args = {"username": functions.hash(form.username.data)}
                self.conn = db.pool.raw_connection()
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
            context["failed_captcha"] = True
        self._screen()
