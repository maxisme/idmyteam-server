import authed
import events
import forms
import server
import mock
from faker import Factory

from web_helpers import WebTest


class TeamGenerator(object):
    def __init__(self):
        fake = Factory.create()
        self.username = fake.user_name()
        self.email = fake.email()
        self.password = fake.password()
        self.allow_storage = fake.boolean()
        self.ip = fake.ipv4_private()


@mock.patch("view.BaseHandler.flash_error")
@mock.patch("smtplib.SMTP")
@mock.patch("authed.LoginHandler._is_valid_captcha", return_value=True)
@mock.patch("settings.functions.AESCipher._mock_me")
@mock.patch("settings.functions.Email.template")
class TestWeb(WebTest):
    protected_urls = ["/socket", "/local", "/upload", "/profile", "/reset", "/profile/stored-images"]

    def test_urls(self, *args):
        for url in server.web_urls.www_urls:
            if url[1].__module__ != "events" and url[0] not in self.protected_urls:
                response = self.fetch(url[0])
                assert response.code == 200, url[0]

    def test_email_confirmation_flow(self, template, *args):
        team = TeamGenerator()
        self._signup(team)
        email_token = template.call_args[1]["token"]
        self._confirm_account_tests(email_token, team)

    def test_signup_flow(self, smtp, *args):
        form_data = self._signup(TeamGenerator())
        assert smtp.called, "SMTP call in handler"

        # test duplicate signup
        self.post("/signup", form_data)
        error_message = args[3].call_args[0][0]
        assert (
            error_message == authed.SignUpHandler.INVALID_SIGNUP_MESSAGE
        ), "Duplicate signup"

        # test unchecked ts
        form_data.pop("ts")
        self.post("/signup", form_data, follow_redirects=False)
        error_message = args[3].call_args[0][0]
        assert error_message == forms.SignUpForm.TS_MESSAGE, "Not checked ts"

    def test_email_retry(self, template, *args):
        team = TeamGenerator()
        self.fetch("/resend?email={email}&username={username}".format(**team.__dict__))
        error_message = args[3].call_args[0][0]
        assert (
            error_message == events.ResendConfirmationEmail.CONFIRMATION_ERROR
        ), "No such team signed up"

        self._signup(team)
        self.fetch("/resend?email={email}&username={username}".format(**team.__dict__))
        email_token = template.call_args[1]["token"]
        self._confirm_account_tests(email_token, team)

        self.fetch("/resend?email={email}&username={username}".format(**team.__dict__))
        error_message = args[3].call_args[0][0]
        assert (
            error_message == events.ResendConfirmationEmail.CONFIRMATION_ERROR
        ), "Already confirmed"

    def test_login(self, template, *args):
        team = TeamGenerator()
        self._signup(team)

        self.post("/login", team.__dict__)
        error_message = args[3].call_args[0][0]
        assert "not confirmed" in error_message, "Not yet confirmed"

        # confirm signup
        email_token = template.call_args[1]["token"]
        self.fetch(
            "/confirm?email={email}&username={username}&token={token}".format(
                token=email_token, **team.__dict__
            )
        )
        assert self._is_logged_in(), "logged in"
        self.fetch("/logout")
        assert not self._is_logged_in(), "logged out"

        # test login
        self.post("/login", team.__dict__)
        assert self._is_logged_in(), "correct login details"
        self.fetch("/logout")
        assert not self._is_logged_in(), "logged out"

        # test invalid login details
        self.post("/login", TeamGenerator().__dict__)
        error_message = args[3].call_args[0][0]
        assert (
            error_message == authed.LoginHandler.INVALID_MESSAGE
        ), "incorrect login details"

    def _confirm_account_tests(self, email_token, team):
        # test no token
        self.fetch(
            "/confirm?email={email}&username={username}".format(
                token=email_token, **team.__dict__
            )
        )
        assert self.fetch("/profile", follow_redirects=False).code == 302, "no token"

        # test no username
        self.fetch(
            "/confirm?email={email}&token={token}".format(
                token=email_token, **team.__dict__
            )
        )
        assert self.fetch("/profile", follow_redirects=False).code == 302, "no username"

        # test no email
        self.fetch(
            "/confirm?username={username}&token={token}".format(
                token=email_token, **team.__dict__
            )
        )
        assert self.fetch("/profile", follow_redirects=False).code == 302, "no email"

        # test correct details
        self.fetch(
            "/confirm?email={email}&username={username}&token={token}".format(
                token=email_token, **team.__dict__
            )
        )
        assert self._is_logged_in(), "correct details"

    def test_password_reset_username(self, template, *args):
        team = TeamGenerator()
        self._signup(team)
        self.fetch("/logout")

        self.post("/forgot", {"username": team.username})
        token = template.call_args[1]["token"]
        assert token

        new_pass = TeamGenerator().password

        # invalid reset
        self.post(
            "/reset",
            {
                "username": team.username,
                "password": new_pass,
                "confirm": new_pass,
                "token": "foo",
            },
        )
        error_message = args[3].call_args[0][0]
        assert error_message == authed.ResetPassword.ERROR

        # successful reset
        self.post(
            "/reset",
            {
                "username": team.username,
                "password": new_pass,
                "confirm": new_pass,
                "token": token,
            },
        )
        assert self.get_cookie("success_message") == authed.ResetPassword.SUCCESS

    def test_password_reset_email(self, template, *args):
        team = TeamGenerator()
        self._signup(team)
        self.fetch("/logout")

        self.post("/forgot", {"email": team.email})
        token = template.call_args[1]["token"]
        assert token

        new_pass = TeamGenerator().password

        # invalid reset
        self.post(
            "/reset",
            {
                "email": team.email,
                "password": new_pass,
                "confirm": new_pass,
                "token": "foo",
            },
        )
        error_message = args[3].call_args[0][0]
        assert error_message == authed.ResetPassword.ERROR

        # successful reset
        self.post(
            "/reset",
            {
                "email": team.email,
                "password": new_pass,
                "confirm": new_pass,
                "token": token,
            },
        )
        assert self.get_cookie("success_message") == authed.ResetPassword.SUCCESS

    def test_credentials(self, template, _mock_me, *args):
        team = TeamGenerator()
        self.new_team(team, template)
        assert self.get_credentials(team, _mock_me)
