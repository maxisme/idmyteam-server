import logging
import os
import zipfile

from django.core.files.uploadedfile import InMemoryUploadedFile
from django.http import HttpResponseBadRequest, HttpResponse
from django.views.decorators.http import require_http_methods

from idmyteamserver.helpers import kb_to_b
from worker.structs import DetectJob, StoreImageFeaturesJob, TrainJob
from idmyteamserver.decorators import file_upload_auth_decorator
from idmyteamserver.models import Team
from web import settings
from worker.queue import MyQueue, REDIS_HIGH_Q, REDIS_LOW_Q, enqueue

MISSING_TEAM_MODEL_MSG = "Your team must train a model before you can predict."


@file_upload_auth_decorator()
@require_http_methods(["POST"])
def predict_image_handler(request, upload_form):
    team: Team = request.user
    if team.classifier_model_path:
        file: InMemoryUploadedFile = request.FILES["file"]
        enqueue(
            REDIS_HIGH_Q,
            DetectJob(
                img=file.read(),
                file_name=file.name,
                team_username=team,
                store_image_features=upload_form.cleaned_data.get(
                    "store_image_features", False
                ),
            ),
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
        training_images.enqueue(REDIS_LOW_Q, team)

        return HttpResponse()
    return HttpResponseBadRequest("Invalid ZIP file")


class ZipImg:
    def __init__(self, name: str, img: bytes):
        self.name = name
        self.img = img


class TeamTrainingZip:
    def __init__(
        self,
        z: zipfile.ZipFile,
        num_images_allowed_to_train: int,
        max_team_member_size: int,
        max_img_size_kb: int,
    ):
        self._imgs = {}
        members = set()
        img_cnt = 0
        for file in z.infolist():
            if file.file_size:
                img_cnt += 1
                if img_cnt > num_images_allowed_to_train:
                    logging.info("Too many images uploaded")
                    break

                if file.file_size > kb_to_b(max_img_size_kb):
                    raise Exception(f"Training image '{file.filename}' is too large!")

                # get member from file structure
                try:
                    # members images expected to be put in separate directories
                    member = self._extract_member_from_file_path(file.filename)
                except ValueError:
                    logging.error("Invalid named file uploaded")
                    continue
                members.add(member)
                if len(members) > max_team_member_size:
                    raise Exception(
                        f"You can't train more than {max_team_member_size} members!"
                    )
                self._add(member, ZipImg(name=file.filename, img=z.read(file)))

        if len(members) == 0:
            raise Exception(f"No members passed!")

    @staticmethod
    def _extract_member_from_file_path(path: str) -> int:
        # members images expected to be put in separate directories
        return int(os.path.basename(os.path.normpath(os.path.dirname(path))))

    def __len__(self):
        return len(self._imgs)

    def _add(self, member: int, file: ZipImg):
        if member in self._imgs:
            self._imgs[member].append(file)
        else:
            self._imgs[member] = [file]

    def enqueue(self, queue: MyQueue, team_username: str):
        for member in self._imgs:
            img: ZipImg
            for img in self._imgs[member]:
                enqueue(
                    queue,
                    StoreImageFeaturesJob(
                        img=img.img,
                        file_name=img.name,
                        team_username=team_username,
                        member_id=member,
                    ),
                )

        # tell model to now train with the stored image features
        enqueue(
            queue,
            TrainJob(
                team_username=team_username,
            ),
        )
