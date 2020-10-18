from django.contrib.auth.decorators import login_required

from idmyteamserver import helpers
from idmyteamserver.helpers import redirect
from idmyteamserver.models import Team


@login_required
def delete_model_handler(request):
    team: Team = request.user
    if team.is_authenticated:
        pass  # TODO


@login_required
def delete_team_handler(request):
    team: Team = request.user
    if team.is_authenticated:
        pass  # TODO


@login_required
def toggle_image_storage_handler(request):
    team: Team = request.user
    team.allow_image_storage = False if team.allow_image_storage else True
    team.save()
    return redirect("/profile")


@login_required
def reset_credentials_handler(request):
    team: Team = request.user
    if team.is_authenticated:
        team.credentials = helpers.create_credentials()
        team.save()
    return redirect("/profile")
