import io
import logging
import zipfile

import bcrypt
from django.http import HttpResponseBadRequest, HttpResponseForbidden
from django.views.decorators.http import require_http_methods
from redis import Redis
from rq import Queue

from idmyteamserver.forms import UploadFileForm
from idmyteamserver.helpers import TeamTrainingImages
from idmyteamserver.structs import DetectJob
from idmyteamserver.models import Team
from web import settings

PREDICT_FILE_FIELD = "predict_file"
TRAIN_FILE_FIELD = "train_file"
TRAIN_Q_TIMEOUT = 600

redis_conn = Redis()

HIGH_Q = Queue("high", connection=redis_conn, default_timeout=60)
MED_Q = Queue("medium", connection=redis_conn, default_timeout=60)
LOW_Q = Queue("low", connection=redis_conn, default_timeout=TRAIN_Q_TIMEOUT)


@require_http_methods(["POST"])
def upload_handler(request):
    form = UploadFileForm(request.POST, request.FILES)
    if not form.is_valid():
        return HttpResponseBadRequest(form.errors)

    team = Team.objects.get(username=form.username)
    if not team.validate_credentials(form.credentials):
        return HttpResponseForbidden()  # TODO prevent brute force

    if PREDICT_FILE_FIELD in request.FILES:
        if team.model_path:
            MED_Q.enqueue_call(
                func=".",
                kwargs=DetectJob(
                    img=request.FILES[PREDICT_FILE_FIELD].read(),
                    file_name=request.FILES[PREDICT_FILE_FIELD].name,
                    team_username=team.username,
                    store_image_features=form.store_image_features,
                ).val(),
            )
        else:
            logging.error(f"Prediction request before trained model! {team.username}")
            return HttpResponseBadRequest(
                "The team needs to train before you can predict."
            )

    elif TRAIN_FILE_FIELD in request.FILES:
        # parse zip file
        z = zipfile.ZipFile(io.BytesIO(request.FILES[TRAIN_FILE_FIELD].read()))
        if z:
            num_features_added_last_hr = team.num_features_added_last_hr()

            # get the number of images the team can train
            num_images_to_train = (
                team.max_train_imgs_per_hr - num_features_added_last_hr
            )
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

            if len(training_images) < 2 and not team.model_path:
                # if the team has no model yet they have to initially train at least 2 team members
                return HttpResponseBadRequest(
                    "You must train with at least 2 team members."
                )

            # enqueue images for training
            training_images.train(LOW_Q, team.username, form.store_image_features)
        else:
            return HttpResponseBadRequest("Invalid ZIP file")
