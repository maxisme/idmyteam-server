from django.db.models import AutoField
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


def dict_from_team_factory(team: TeamFactory) -> dict:
    result = {}
    for k, v in team.__dict__.items():
        field: AutoField
        for field in Team._meta.fields:
            if v and field.attname == k:
                result[k] = v
                break
    return result
