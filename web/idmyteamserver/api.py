from idmyteamserver import helpers
from idmyteamserver.helpers import redirect
from idmyteamserver.models import Team


def delete_model_handler(request):
    team: Team = request.user
    if team.is_authenticated:
        pass  # TODO


def delete_team_handler(request):
    team: Team = request.user
    if team.is_authenticated:
        pass  # TODO


def toggle_storage_handler(request):
    team: Team = request.user
    if team.is_authenticated:
        team.allow_image_storage = False if team.allow_image_storage else True
        team.save()
    return redirect("/profile")


def reset_credentials_handler(request):
    team: Team = request.user
    if team.is_authenticated:
        team.credentials = helpers.create_credentials()
        team.save()
    return redirect("/profile")
