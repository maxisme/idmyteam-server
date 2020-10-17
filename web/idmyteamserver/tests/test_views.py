import pytest
from django.db.models import AutoField
from django.test import Client
from django.urls import reverse

from idmyteamserver.models import Team
from idmyteamserver.tests.factories import TeamFactory
from idmyteamserver.urls import AUTH_URL_NAMES
from web.sitemap import PUBLIC_URL_NAMES


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

    def test_valid_signup(self):
        client = Client()

        # initialise signup form data
        team = TeamFactory.build()
        team_dict = self._dict_from_team_factory(team)
        team_dict["confirm"] = team_dict["password"]
        team_dict["terms"] = True

        assert not bool(Team.objects.filter(username=team.username).exists())
        client.post(reverse("signup"), team_dict)
        assert Team.objects.filter(username=team.username).exists()

    def test_valid_login(self):
        client = Client()

        # initialise signup form data
        team_factory = TeamFactory.build()
        team_dict = self._dict_from_team_factory(team_factory)
        team = Team.objects.create_user(**team_dict)

        # confirm email with key
        team.confirm_email(team.get_confirmation_key())

        response = client.post(reverse("login"), team_dict, follow=True)
        assert response.context["user"].is_authenticated

    def _dict_from_team_factory(self, team: TeamFactory) -> dict:
        result = {}
        for k, v in team.__dict__.items():
            field: AutoField
            for field in Team._meta.fields:
                if v and field.attname == k:
                    result[k] = v
                    break
        return result
