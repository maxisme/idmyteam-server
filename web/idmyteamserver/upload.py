import io
import logging
import zipfile

from django.http import HttpResponseBadRequest, HttpResponseForbidden
from django.views.decorators.http import require_http_methods

from idmyteam.structs import DetectJob
from idmyteamserver.forms import UploadFileForm
from idmyteamserver.helpers import TeamTrainingImages
from idmyteamserver.models import Team
from web import settings
from web.settings import REDIS_MED_Q, REDIS_LOW_Q


@require_http_methods(["POST"])
def predict_image_handler(request):
    form = UploadFileForm(request.POST, request.FILES)
    if not form.is_valid():
        return HttpResponseBadRequest(form.errors)

    team = Team.objects.get(username=form.username)
    if not team.validate_credentials(form.credentials):
        return HttpResponseForbidden()  # TODO prevent brute force

    if team.classifier_model_path:
        REDIS_MED_Q.enqueue_call(
            func=".",
            kwargs=DetectJob(
                img=form.file.read(),
                file_name=form.file.name,
                team_username=team.username,
                store_image_features=form.store_image_features,
            ).dict(),
        )
    else:
        logging.error(f"Prediction request before trained model! {team.username}")
        return HttpResponseBadRequest("The team needs to train before you can predict.")


@require_http_methods(["POST"])
def train_team_handler(request):
    form = UploadFileForm(request.POST, request.FILES)
    if not form.is_valid():
        return HttpResponseBadRequest(form.errors)

    team = Team.objects.get(username=form.username)
    if not team.validate_credentials(form.credentials):
        return HttpResponseForbidden()  # TODO prevent brute force

    # parse zip file
    z = zipfile.ZipFile(io.BytesIO(form.file.read()))
    if z:
        num_features_added_last_hr = team.num_features_added_last_hr()

        # get the number of images the team can train
        num_images_to_train = team.max_train_imgs_per_hr - num_features_added_last_hr
        if num_images_to_train <= 0:
            return HttpResponseBadRequest(
                "You have uploaded too many training images. Please try again later..."
            )

        # parse the images from the zip file
        try:
            training_images = TeamTrainingImages(z, settings.MAX_IMG_UPLOAD_SIZE_KB)
        except Exception as e:
            return HttpResponseBadRequest(str(e))
        training_images.crop(num_images_to_train)

        if len(training_images) < 2 and not team.classifier_model_path:
            # if the team has no model yet they have to initially train at least 2 team members
            return HttpResponseBadRequest(
                "You must train with at least 2 team members."
            )

        # enqueue images for training
        training_images.train(REDIS_LOW_Q, team.username)
    else:
        return HttpResponseBadRequest("Invalid ZIP file")
