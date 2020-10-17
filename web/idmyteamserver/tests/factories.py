from factory import Faker
from factory.django import DjangoModelFactory

from idmyteamserver.models import Team


class TeamFactory(DjangoModelFactory):
    class Meta:
        model = Team

    username = Faker("user_name")
    password = Faker("password")
    email = Faker("email")
    allow_image_storage = Faker("boolean")
