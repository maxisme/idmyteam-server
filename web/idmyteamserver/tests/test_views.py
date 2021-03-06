import os
import shutil
import tempfile
import unittest.mock
import zipfile
from os.path import basename

import pytest
from PIL import Image
from django.http import HttpResponseBadRequest
from django.test import Client
from django.urls import reverse

from idmyteam.idmyteam.structs import DeletedModelWSStruct
from tests.factories import TeamFactory, dict_from_team_factory
from tests.helpers import create_test_team
from worker.structs import DetectJob, TrainJob
from idmyteam.idmyteam.helpers import SUCCESS_COOKIE_KEY, ERROR_COOKIE_KEY, random_str
from idmyteamserver.models import Team
from idmyteamserver.upload import MISSING_TEAM_MODEL_MSG
from idmyteamserver.urls import AUTH_URL_NAMES
from web.settings import DEFAULT_MAX_NUM_TEAM_MEMBERS, PASSWORD_HASHERS, REDIS_CONN
from web.sitemap import PUBLIC_URL_NAMES
from worker.queue import MyQueue

CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))
TMP_FILE_DIR = f"{CURRENT_DIR}/files/"
TMP_ZIP_DIR = f"{CURRENT_DIR}/zip/"


@pytest.fixture(autouse=True)
def overide_hasher():
    PASSWORD_HASHERS[0] = "django.contrib.auth.hashers.MD5PasswordHasher"


@pytest.mark.django_db
class TestViews:
    @pytest.mark.parametrize("url_name", PUBLIC_URL_NAMES)
    def test_public_200(self, url_name):
        client = Client()
        response = client.get(reverse(url_name))
        assert response.status_code == 200


@pytest.mark.django_db
class TestAuthViews:
    @pytest.mark.parametrize("url_name", AUTH_URL_NAMES)
    def test_public_200(self, url_name):
        client = Client()
        response = client.get(reverse(url_name))
        assert response.status_code == 302

    def test_valid_signup(self, monkeypatch):
        client = Client()

        # initialise signup form data
        team = TeamFactory.build()
        team_dict = dict_from_team_factory(team)
        team_dict["confirm"] = team_dict["password"]
        team_dict["terms"] = True

        assert not bool(Team.objects.filter(username=team).exists())

        mock_send_email = unittest.mock.Mock()
        # monkeypatch _send_email
        monkeypatch.setattr("idmyteamserver.email._send_email", mock_send_email)

        client.post(reverse("signup"), team_dict)

        mock_send_email.assert_called_once()
        assert Team.objects.filter(username=team).exists()

    def test_valid_login(self):
        client = Client()

        # initialise signup form data
        team_factory = TeamFactory.build()
        team_dict = dict_from_team_factory(team_factory)
        team = Team.objects.create_user(**team_dict)

        # confirm email
        team.confirm_email(team.get_confirmation_key())

        response = client.post(reverse("login"), team_dict, follow=True)
        assert response.context["user"].is_authenticated

    def test_unconfirmed_email_login_attempt(self):
        client = Client()

        # initialise signup form data
        team_factory = TeamFactory.build()
        team_dict = dict_from_team_factory(team_factory)
        Team.objects.create_user(**team_dict)

        assert Team.objects.filter(username=team_factory.username).exists()

        response = client.post(reverse("login"), team_dict, follow=True)
        assert not response.context["user"].is_authenticated

    def test_invalid_credentials_login_attempt(self):
        client = Client()

        # initialise signup form data
        team_factory = TeamFactory.build()
        team_dict = dict_from_team_factory(team_factory)

        # attempt to login without creating team
        response = client.post(reverse("login"), team_dict, follow=True)

        # todo more asserts
        assert not response.context["user"].is_authenticated

    def test_confirm_email(self, monkeypatch):
        client = Client()

        # initialise signup form data
        team = TeamFactory.build()
        team_dict = dict_from_team_factory(team)
        team_dict["confirm"] = team_dict["password"]
        team_dict["terms"] = True

        mock_send_confirm = unittest.mock.Mock()
        monkeypatch.setattr("idmyteamserver.email.send_confirm", mock_send_confirm)

        # create team
        client.post(reverse("signup"), team_dict)

        # verify would be sent to correct email
        assert mock_send_confirm.call_args.kwargs["to"] == team.email

        # get key used to confirm email
        confirm_email_key = mock_send_confirm.call_args.kwargs["key"]

        # confirm email
        client.get(
            reverse("confirm-email", kwargs={"key": confirm_email_key}),
            {"email": team.email},
            follow=False,
        )

        team = Team.objects.get(username=team)
        # verify that the team has been confirmed
        assert team.is_confirmed

    def test_invalid_confirm_email_key(self, monkeypatch):
        client = Client()

        # initialise signup form data
        team = TeamFactory.build()
        team_dict = dict_from_team_factory(team)
        team_dict["confirm"] = team_dict["password"]
        team_dict["terms"] = True

        mock_send_email = unittest.mock.Mock()
        monkeypatch.setattr("idmyteamserver.email._send_email", mock_send_email)

        # create team
        client.post(reverse("signup"), team_dict)

        # confirm email
        request = client.get(
            reverse("confirm-email", kwargs={"key": "not-a-valid-key"}),
            {"email": team.email},
            follow=False,
        )

        # verify that a an error cookie was returned
        assert len(request.cookies[ERROR_COOKIE_KEY]) > 0

        # verify that the team has not been confirmed
        assert not Team.objects.get(username=team).is_confirmed

    @pytest.mark.parametrize("test_email", [True, False])
    def test_forgot_email_username_reset(self, monkeypatch, test_email):
        client = Client()

        # create a random user
        team_factory = TeamFactory.build()
        team_dict = dict_from_team_factory(team_factory)
        team = Team.objects.create_user(**team_dict)

        mock_send_reset = unittest.mock.Mock()
        monkeypatch.setattr("idmyteamserver.email.send_reset", mock_send_reset)

        if test_email:
            client.post(reverse("forgot-password"), {"username_email": team.email})
        else:
            client.post(reverse("forgot-password"), {"username_email": team})

        # get password_reset_key
        password_reset_key = mock_send_reset.call_args.kwargs["key"]

        new_password = TeamFactory.build().password
        request = client.post(
            reverse("reset-password"),
            {
                "reset_key": password_reset_key,
                "password": new_password,
                "confirm": new_password,
            },
        )

        assert len(request.cookies[SUCCESS_COOKIE_KEY]) > 0

        # verify the new password works
        team = Team.objects.get(username=team_factory.username)
        assert team.check_password(new_password)

    def test_logout_handler(self):
        client = Client()
        team, team_dict = create_test_team()
        request = client.post(reverse("login"), team_dict, follow=True)
        assert request.context["user"].is_authenticated
        request = client.post(reverse("logout"), team_dict, follow=True)
        assert not request.context["user"].is_authenticated


@pytest.mark.django_db
class TestApiViews:
    def test_toggle_image_storage_handler(self):
        client = Client()
        team, team_dict = create_test_team()
        client.post(reverse("login"), team_dict)
        client.patch(reverse("toggle-image-storage"))

        # verify allow_image_storage have changed
        allow_storage = Team.objects.get(username=team).allow_image_storage
        assert team.allow_image_storage != allow_storage

    def test_reset_credentials_handler(self):
        client = Client()
        team, team_dict = create_test_team()
        client.post(reverse("login"), team_dict)
        client.patch(reverse("reset-credentials"))
        # verify credentials have changed
        assert team.credentials != Team.objects.get(username=team).credentials

    def test_delete_model_handler(self, monkeypatch):
        client = Client()
        with tempfile.NamedTemporaryFile(mode="w+b") as f:
            team, team_dict = create_test_team(classifier_model_path=f.name)
            client.post(reverse("login"), team_dict)

            # monkeypatches
            monkeypatch.setattr(
                "worker.queue.REDIS_HIGH_Q",
                MyQueue("high", connection=REDIS_CONN, is_async=False),
            )
            mock_send_ws_message = unittest.mock.Mock()
            monkeypatch.setattr(
                "idmyteamserver.models.Team.send_ws_message", mock_send_ws_message
            )
            monkeypatch.setattr(
                "worker.queue.MyJob._delete_team_classifier", _return_true
            )

            request = client.delete(reverse("delete-model"))
            assert request.status_code == 200

            # verify classifier_model_path has been removed
            assert (
                team.classifier_model_path
                != Team.objects.get(username=team).classifier_model_path
            )

            # verify websocket message was sent to client to delete model
            mock_send_ws_message.assert_called_once()
            assert (
                mock_send_ws_message.call_args.args[0].dict()
                == DeletedModelWSStruct().dict()
            )

    def test_delete_team_handler(self, monkeypatch):
        client = Client()
        team, team_dict = create_test_team()
        client.post(reverse("login"), team_dict)

        monkeypatch.setattr(
            "worker.queue.REDIS_HIGH_Q",
            MyQueue("high", connection=REDIS_CONN, is_async=False),
        )
        request = client.delete(reverse("delete-team"))
        assert request.status_code == 200

        # verify team no longer exists
        assert not bool(Team.objects.filter(username=team).exists())


@pytest.mark.django_db
class TestPredictHandler:
    def test_successful(self, monkeypatch):
        client = Client()
        team, form_dict = create_test_team(
            classifier_model_path="/path/to/none/existent/model"
        )
        img = create_img(TMP_FILE_DIR)
        with open(img, "rb") as file:
            form_dict["file"] = file
            mock_enqueue_call = unittest.mock.Mock()
            monkeypatch.setattr("rq.Queue.enqueue_call", mock_enqueue_call)
            request = client.post(reverse("predict"), form_dict)
            assert request.status_code == 200

            file.seek(0)  # so file can be read again for comparison
            redis_queue_kwargs = DetectJob(
                img=file.read(),
                file_name=basename(file.name),
                team_username=team,
                store_image_features=False,
            ).dict()
            assert mock_enqueue_call.call_args.kwargs["kwargs"] == redis_queue_kwargs
        os.remove(img)

    def test_missing_model(self):
        client = Client()
        team, form_dict = create_test_team()
        img = create_img(TMP_FILE_DIR)
        with open(img, "rb") as file:
            form_dict["file"] = file
            form_dict["store_image_features"] = 0
            request = client.post(reverse("predict"), form_dict)
            assert request.status_code == HttpResponseBadRequest.status_code
            assert request.content.decode() == MISSING_TEAM_MODEL_MSG
        os.remove(img)


@pytest.mark.django_db
class TestTrainHandler:
    client = Client()

    def test_successful(self, monkeypatch):
        team, form_dict = create_test_team()

        # create zip
        zip_path = create_zip(5, 1)
        form_dict["file"] = open(zip_path, "rb")

        # create mock
        mock_enqueue_call = unittest.mock.Mock()
        monkeypatch.setattr("rq.Queue.enqueue_call", mock_enqueue_call)

        # make POST request
        request = self.client.post(reverse("train"), form_dict)

        assert request.status_code == 200
        assert mock_enqueue_call.call_count == 6  # 5 images + 1 final train job

        # verify last mock_enqueue_call was for sending training image
        assert (
            mock_enqueue_call.call_args.kwargs["kwargs"]
            == TrainJob(
                team_username=team,
            ).dict()
        )

        # tidy
        os.remove(zip_path)

    @pytest.mark.parametrize(
        "members,images_per_member,expected_status_code",
        [
            # must train with more than 1 member if not trained before
            (1, 1, HttpResponseBadRequest.status_code),
            # max number of members for team + 1
            (DEFAULT_MAX_NUM_TEAM_MEMBERS + 1, 1, HttpResponseBadRequest.status_code),
        ],
    )
    def test_different_number_of_members(
        self, monkeypatch, members, images_per_member, expected_status_code
    ):
        team, form_dict = create_test_team()
        zip_path = create_zip(members, images_per_member)
        form_dict["file"] = open(zip_path, "rb")
        mock_enqueue_call = unittest.mock.Mock()
        monkeypatch.setattr("rq.Queue.enqueue_call", mock_enqueue_call)
        request = self.client.post(reverse("train"), form_dict)
        assert request.status_code == expected_status_code
        os.remove(zip_path)


def create_img(dir: str) -> str:
    try:
        os.makedirs(dir)
    except FileExistsError:
        pass
    name = random_str(5)
    img_path = f"{dir}/{name}.png"
    img = Image.new("RGBA", (10, 10), (255, 0, 0, 0))
    img.save(img_path, "PNG")
    return img_path


def create_zip(members=5, number_of_images=1) -> str:
    zip_path = f"{TMP_ZIP_DIR}{members}_{number_of_images}.zip"

    try:
        os.makedirs(TMP_ZIP_DIR)
    except FileExistsError:
        pass

    tmp_image_dir = random_str(5) + "/"
    os.makedirs(tmp_image_dir)
    zip = zipfile.ZipFile(zip_path, "w")
    for member in range(1, members + 1):
        for i in range(number_of_images):
            image = create_img(f"{tmp_image_dir}/{member}")
            zip.write(image)
    zip.close()
    shutil.rmtree(tmp_image_dir)
    return zip_path


def _return_true(*args, **kwargs):
    return True
