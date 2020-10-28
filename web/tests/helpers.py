from idmyteamserver.models import Team
from tests.factories import TeamFactory, dict_from_team_factory


def create_test_team(**extras) -> (Team, dict):
    """
    Creates a test team
    """
    team_factory = TeamFactory.build()
    team_dict = dict_from_team_factory(team_factory)
    team_dict = {**team_dict, **extras}
    team = Team.objects.create_user(**team_dict)
    team.confirm_email(team.get_confirmation_key())
    return team, team_dict
