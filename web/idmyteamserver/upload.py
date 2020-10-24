import zipfile

from django.core.files.uploadedfile import InMemoryUploadedFile
from django.http import HttpResponseBadRequest, HttpResponse
from django.views.decorators.http import require_http_methods

from worker.structs import DetectJob
from idmyteamserver.decorators import file_upload_auth_decorator
from idmyteamserver.helpers import TeamTrainingZip
from idmyteamserver.models import Team
from web import settings
from worker.queue import REDIS_MED_Q, REDIS_LOW_Q

MISSING_TEAM_MODEL_MSG = "Your team must train a model before you can predict."


@file_upload_auth_decorator()
@require_http_methods(["POST"])
def predict_image_handler(request, form):
    team: Team = request.user
    if team.classifier_model_path:
        file: InMemoryUploadedFile = request.FILES["file"]

        REDIS_MED_Q.enqueue_call(
            func=".",
            kwargs=DetectJob(
                img=file.read(),
                file_name=file.name,
                team_username=team.username,
                store_image_features=form.cleaned_data.get(
                    "store_image_features", False
                ),
            ).dict(),
        )
        return HttpResponse()
    return HttpResponseBadRequest(MISSING_TEAM_MODEL_MSG)


@file_upload_auth_decorator()
@require_http_methods(["POST"])
def train_team_handler(request, _):
    team: Team = request.user
    # parse zip file
    z = zipfile.ZipFile(request.FILES["file"])
    if z:
        num_features_added_last_hr = team.num_features_added_last_hr()

        # get the number of images the team can train
        num_images_allowed_to_train = (
            team.max_train_imgs_per_hr - num_features_added_last_hr
        )
        if num_images_allowed_to_train <= 0:
            return HttpResponseBadRequest(
                "You have uploaded too many training images. Please try again later..."
            )

        # parse the images from the zip file
        try:
            training_images = TeamTrainingZip(
                z,
                num_images_allowed_to_train,
                team.max_team_members,
                settings.MAX_IMG_UPLOAD_SIZE_KB,
            )
        except Exception as e:
            return HttpResponseBadRequest(str(e))

        if len(training_images) < 2 and not team.classifier_model_path:
            # if the team has no model yet they have to initially train at least 2 team members
            return HttpResponseBadRequest(
                "You must train with at least 2 team members."
            )

        # enqueue images for training
        training_images.enqueue(REDIS_LOW_Q, team.username)

        return HttpResponse()
    return HttpResponseBadRequest("Invalid ZIP file")
