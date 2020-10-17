import pytest
from django.test import Client
from django.urls import reverse

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
