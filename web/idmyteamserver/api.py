import logging
import time

from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseServerError
from django.views.decorators.http import require_http_methods

from worker.structs import DeleteClassifierJob
from idmyteamserver import helpers
from idmyteamserver.helpers import redirect
from idmyteamserver.models import Team
from worker import queue


@login_required
@require_http_methods(["DELETE"])
def delete_model_handler(request):
    team: Team = request.user

    if not _delete_team_model(team):
        logging.warning(f"Problem deleting the teams '{team.username}' classifier.")

    # delete model from path
    team.classifier_model_path = None
    team.save()

    return HttpResponse()


def _delete_team_model(team: Team) -> bool:
    job: queue.MyJob = queue.REDIS_HIGH_Q.enqueue_call(
        func=".", kwargs=DeleteClassifierJob(team_username=team.username).dict(), ttl=1
    )

    # wait for job to complete
    while not job.is_finished:
        time.sleep(0.1)

    return bool(job.result)


@login_required
@require_http_methods(["DELETE"])
def delete_team_handler(request):
    team: Team = request.user

    if not _delete_team_model(team):
        logging.warning(f"Problem deleting the teams '{team.username}' classifier.")

    if team.delete():
        logout(request)
        return HttpResponse()
    return HttpResponseServerError(b"Unable to delete team")


@login_required
@require_http_methods(["PATCH"])
def toggle_image_storage_handler(request):
    team: Team = request.user
    team.allow_image_storage = False if team.allow_image_storage else True
    team.save()
    return redirect("/profile")


@login_required
@require_http_methods(["PATCH"])
def reset_credentials_handler(request):
    team: Team = request.user
    team.credentials = helpers.create_credentials()
    team.save()
    # TODO logout of websocket
    return redirect("/profile")
