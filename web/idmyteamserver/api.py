import logging
import time

from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseServerError
from django.views.decorators.http import require_http_methods

from worker.queue import enqueue
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
        logging.warning(f"Problem deleting the teams '{team}' classifier.")

    # delete model from path
    team.classifier_model_path = None
    team.save()

    return HttpResponse()


@login_required
@require_http_methods(["DELETE"])
def delete_team_handler(request):
    team: Team = request.user

    if not _delete_team_model(team):
        logging.warning(f"Problem deleting the teams '{team}' classifier.")

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


def _delete_team_model(team: Team) -> bool:
    """
    Tells worker to delete the teams classifier model and waits for verification.
    @todo integration test.
    @todo put function somewhere better :)
    @return: whether the classifier model has been deleted or not
    """
    job = enqueue(queue.REDIS_HIGH_Q, DeleteClassifierJob(team_username=team))

    # wait for job to complete
    while not job.is_finished:
        time.sleep(0.1)

    return bool(job.result)
