import pytest
from django.test import Client
from django.urls import reverse

from idmyteamserver.helpers import SUCCESS_COOKIE_KEY, ERROR_COOKIE_KEY
from idmyteamserver.models import Team
from idmyteamserver.tests.factories import TeamFactory, dict_from_team_factory
from idmyteamserver.urls import AUTH_URL_NAMES
from web.sitemap import PUBLIC_URL_NAMES

import unittest.mock


def argtest():
    """
    returns all arguments passed to function as well as if it has been called
    @return:
    """

    class TestArgs(object):
        hit = False

        def __call__(self, *args):
            self.args = list(args)
            self.hit = True

    return TestArgs()


@pytest.mark.django_db
class TestViews:
    @pytest.mark.parametrize("url_name", PUBLIC_URL_NAMES)
    def test_public_200(self, url_name):
        client = Client()
        response = client.get(reverse(url_name))
        assert response.status_code == 200


@pytest.mark.django_db
class TestAuthViews:
    @pytest.mark.parametrize("url_name", AUTH_URL_NAMES)
    def test_public_200(self, url_name):
        client = Client()
        response = client.get(reverse(url_name))
        assert response.status_code == 302

    def test_valid_signup(self, monkeypatch):
        client = Client()

        # initialise signup form data
        team = TeamFactory.build()
        team_dict = dict_from_team_factory(team)
        team_dict["confirm"] = team_dict["password"]
        team_dict["terms"] = True

        assert not bool(Team.objects.filter(username=team.username).exists())

        mock_send_confirm = unittest.mock.Mock()
        # monkeypatch send_confirm
        monkeypatch.setattr("idmyteamserver.email.send_confirm", mock_send_confirm)

        client.post(reverse("signup"), team_dict)

        mock_send_confirm.assert_called()
        assert Team.objects.filter(username=team.username).exists()

    def test_valid_login(self):
        client = Client()

        # initialise signup form data
        team_factory = TeamFactory.build()
        team_dict = dict_from_team_factory(team_factory)
        team = Team.objects.create_user(**team_dict)

        # confirm email
        team.confirm_email(team.get_confirmation_key())

        response = client.post(reverse("login"), team_dict, follow=True)
        assert response.context["user"].is_authenticated

    def test_unconfirmed_email_login_attempt(self):
        client = Client()

        # initialise signup form data
        team_factory = TeamFactory.build()
        team_dict = dict_from_team_factory(team_factory)
        Team.objects.create_user(**team_dict)

        assert Team.objects.filter(username=team_factory.username).exists()

        response = client.post(reverse("login"), team_dict, follow=True)
        assert not response.context["user"].is_authenticated

    def test_invalid_credentials_login_attempt(self):
        client = Client()

        # initialise signup form data
        team_factory = TeamFactory.build()
        team_dict = dict_from_team_factory(team_factory)

        # attempt to login without creating team
        response = client.post(reverse("login"), team_dict, follow=True)

        # todo more asserts
        assert not response.context["user"].is_authenticated

    def test_confirm_email(self, monkeypatch):
        client = Client()

        # initialise signup form data
        team = TeamFactory.build()
        team_dict = dict_from_team_factory(team)
        team_dict["confirm"] = team_dict["password"]
        team_dict["terms"] = True

        # mock send_confirm
        mock_send_confirm = unittest.mock.Mock()
        monkeypatch.setattr("idmyteamserver.email.send_confirm", mock_send_confirm)

        # create team
        client.post(reverse("signup"), team_dict)

        # verify would be sent to correct email
        assert mock_send_confirm.call_args.kwargs["to"] == team.email

        # get key used to confirm email
        confirm_email_key = mock_send_confirm.call_args.kwargs["key"]

        # confirm email
        request = client.get(
            reverse("confirm-email", kwargs={"key": confirm_email_key}),
            {"email": team.email},
            follow=False,
        )

        # verify that a succesful cookie was returned
        assert len(request.cookies[SUCCESS_COOKIE_KEY]) > 0

        # verify that the team has been confirmed
        assert Team.objects.get(username=team.username).is_confirmed

    def test_invalid_confirm_email_key(self, monkeypatch):
        client = Client()

        # initialise signup form data
        team = TeamFactory.build()
        team_dict = dict_from_team_factory(team)
        team_dict["confirm"] = team_dict["password"]
        team_dict["terms"] = True

        # mock send_confirm
        mock_send_confirm = unittest.mock.Mock()
        monkeypatch.setattr("idmyteamserver.email.send_confirm", mock_send_confirm)

        # create team
        client.post(reverse("signup"), team_dict)

        # confirm email
        request = client.get(
            reverse("confirm-email", kwargs={"key": "not-a-valid-key"}),
            {"email": team.email},
            follow=False,
        )

        # verify that a an error cookie was returned
        assert len(request.cookies[ERROR_COOKIE_KEY]) > 0

        # verify that the team has not been confirmed
        assert not Team.objects.get(username=team.username).is_confirmed

    @pytest.mark.parametrize("test_email", [True, False])
    def test_forgot_email_username_reset(self, monkeypatch, test_email):
        client = Client()

        # create a random user
        team_factory = TeamFactory.build()
        team_dict = dict_from_team_factory(team_factory)
        team = Team.objects.create_user(**team_dict)

        # mock send_confirm
        mock_send_reset = unittest.mock.Mock()
        monkeypatch.setattr("idmyteamserver.email.send_reset", mock_send_reset)

        if test_email:
            client.post(reverse("forgot-password"), {"username_email": team.email})
        else:
            client.post(reverse("forgot-password"), {"username_email": team.username})

        # get password_reset_key
        password_reset_key = mock_send_reset.call_args.kwargs["key"]

        new_password = TeamFactory.build().password
        request = client.post(
            reverse("reset-password"),
            {
                "reset_key": password_reset_key,
                "password": new_password,
                "confirm": new_password,
            },
        )

        assert len(request.cookies[SUCCESS_COOKIE_KEY]) > 0

        # verify the new password works
        team = Team.objects.get(username=team_factory.username)
        assert team.check_password(new_password)

    def test_logout_handler(self):
        client = Client()
        team, team_dict = create_team()
        request = client.post(reverse("login"), team_dict, follow=True)
        assert request.context["user"].is_authenticated
        request = client.post(reverse("logout"), team_dict, follow=True)
        assert not request.context["user"].is_authenticated


@pytest.mark.django_db
class TestApiViews:
    def test_toggle_image_storage_handler(self):
        client = Client()
        team, team_dict = create_team()
        client.post(reverse("login"), team_dict)
        client.get(reverse("toggle-image-storage"))
        # verify allow_image_storage have changed
        assert (
            team.allow_image_storage
            != Team.objects.get(username=team.username).allow_image_storage
        )

    def test_reset_credentials_handler(self):
        client = Client()
        team, team_dict = create_team()
        client.post(reverse("login"), team_dict)
        client.get(reverse("reset-credentials"))
        # verify credentials have changed
        assert team.credentials != Team.objects.get(username=team.username).credentials


def create_team() -> (Team, dict):
    """
    Creates a test team
    """
    team_factory = TeamFactory.build()
    team_dict = dict_from_team_factory(team_factory)
    team = Team.objects.create_user(**team_dict)
    team.confirm_email(team.get_confirmation_key())
    return team, team_dict
