from django.contrib.auth import authenticate, logout
from django.http import HttpResponseRedirect

from idmyteamserver.email import send_confirm
from idmyteamserver.helpers import SUCCESS_COOKIE_KEY, is_valid_email, redirect
from idmyteamserver.models import Account
from idmyteamserver.views import render
from idmyteamserver import forms

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
#             context["root_password"] = "zFHbmDM59nQIt5w6eYbWL2KsHHWdk4PQForgot password?9laRHZ5b"
#             context["credentials"] = functions.AESCipher(
#                 config.SECRETS["crypto"]
#             ).decrypt(team["credentials"])
#             context["xsrf_token"] = self.xsrf_token
#             return render(request, "profile.html", context)
#         else:
#             self.clear_cookie("username")
#     return self.redirect("/login")


# def view_stored_images_handler(request):
#     context = {"title": "Stored Images"}
#     if request.user.is_authenticated():
#         context["images"] = functions.Team.get_stored_images(
#             functions.hash(request.user.username), config.STORE_IMAGES_DIR
#         )
#         return render("profile/images.html", context)
#     return HttpResponseRedirect("/")


INVALID_LOGIN_MESSAGE = "Invalid credentials! Please try again."
INVALID_SIGNUP_MESSAGE = (
    "Error with user information! Please try a different username or email"
)


def login_handler(request):
    error_message = ""
    if request.method == "POST":
        form = forms.LoginForm(request.POST)
        if form.is_valid():
            username = request.POST['username']
            password = request.POST['password']
            user: Account = authenticate(
                username=username,
                password=password
            )
            if user:
                if user.is_confirmed:
                    return HttpResponseRedirect("/profile")
                else:
                    logout(request)
                    error_message = """
                    You have not confirmed your email! <a href='/resend?email={}'>Resend confirmation?</a>
                    """.format(
                        user.email
                    )
            else:
                error_message = INVALID_LOGIN_MESSAGE
    else:
        form = forms.LoginForm()

    return render(
        request, "forms/login.html", {"title": "Login", "form": form}, error_message=error_message
    )


def signup_handler(request):
    unstored_keys = ("confirm", "terms", "captcha")

    if request.method == "POST":
        form = forms.SignUpForm(request.POST)
        if form.is_valid():
            post_data = form.cleaned_data
            for key in unstored_keys:
                del post_data[key]
            user = Account.objects.create_user(**post_data)
            if user:
                # send confirmation email
                send_confirm(request, to=form.cleaned_data.get("email"), key=user.confirmation_key)

                return redirect("/", cookies={
                    SUCCESS_COOKIE_KEY: "Welcome! Please confirm your email to complete signup!"
                })
            else:
                form.add_error()
    else:
        form = forms.SignUpForm()

    return render(
        request, "forms/signup.html", {"title": "Login", "form": form}
    )


def confirm_handler(request, key):
    user_email = request.GET.get('email', None)
    if is_valid_email(user_email):
        user = Account.objects.get(email=user_email)
        if user:
            user.confirm_email(key)
            return redirect("/", cookies={
                SUCCESS_COOKIE_KEY: f"Welcome to the Team {user.username}!"
            })


def forgot_handler(request):
    if request.method == "POST":
        form = forms.ForgotForm(request.POST)
    else:
        form = forms.ForgotForm()

    return render(
        request, "forms/forgot.html", {"title": "Forgot Password", "form": form}
    )

# def _screen(self):
#     context["title"] = "Sign Up"
#     self.render("forms/form.html", **context)
#
#
# class ForgotPassword(LoginHandler):
#     def get(self):
#         context["form"] = forms.ForgotForm()
#         self._screen()
#
#     def _screen(self):
#         context["title"] = "Forgot Password"
#         self.render("forms/form.html", **context)
#
#     def post(self):
#         context["form"] = form = forms.ForgotForm(self.request.arguments)
#         if form.validate():
#             self.conn = db.pool.raw_connection()
#             if form.email.data or form.username.data:
#                 if form.email.data:
#                     args = {"email": form.email.data}
#                 else:
#                     args = {"username": functions.hash(form.username.data)}
#                 team = functions.Team.get(self.conn, **args)
#                 if team["email"]:
#                     functions.Team.PasswordReset.reset(
#                         self.conn,
#                         team["email"],
#                         config.EMAIL_CONFIG,
#                         config.SECRETS["token"],
#                         config.ROOT,
#                     )
#                     return self.flash_success("Sent reset email!", "/")
#             else:
#                 form.errors.append("Please enter either an email or a username.")
#         self._screen()
#
#
# class ResetPassword(LoginHandler):
#     SUCCESS = "Success resetting password!"
#     ERROR = "Invalid request to reset password."
#
#     def get(self):
#         email = self.get_argument("email", "")
#         username = self.get_argument("username", "")
#         token = self.get_argument("token", "")
#
#         if (email or username) and token:
#             context["form"] = forms.ResetPasswordForm(
#                 data={"token": token, "email": email, "username": username}
#             )
#             self._screen()
#         else:
#             return self.redirect("/")
#
#     def _screen(self):
#         context["title"] = "Reset Password"
#         self.render("forms/form.html", **context)
#
#     def post(self):
#         if self._is_valid_captcha(self.request.arguments):
#             context["form"] = form = forms.ResetPasswordForm(self.request.arguments)
#             if form.validate():
#                 if form.email.data:
#                     args = {"email": form.email.data}
#                 else:
#                     args = {"username": functions.hash(form.username.data)}
#                 self.conn = db.pool.raw_connection()
#                 team = functions.Team.get(self.conn, **args)
#                 if team and functions.Team.PasswordReset.validate(
#                     self.conn, team["email"], form.token.data, config.SECRETS["token"]
#                 ):
#                     if functions.Team.reset_password(
#                         self.conn, form.password.data, **args
#                     ):
#                         return self.flash_success(self.SUCCESS, "/login")
#             return self.flash_error(self.ERROR, "/forgot")
#         else:
#             context["failed_captcha"] = True
#         self._screen()
