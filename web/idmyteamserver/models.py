import logging
from datetime import datetime, timedelta

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_email_confirmation.models import SimpleEmailConfirmationUserMixin

from idmyteam.structs import WSStruct
from idmyteamserver import helpers
from web import settings


class Team(AbstractUser, SimpleEmailConfirmationUserMixin):
    # overwrite AbstractUser field
    email = models.EmailField(_("email address"), blank=True, unique=True)

    allow_image_storage = models.BooleanField(default=False)
    credentials = models.CharField(max_length=255, default=helpers.create_credentials)
    CREDENTIALS_FIELD = "credentials"

    password_reset_token = models.CharField(max_length=settings.PASS_RESET_TOKEN_LEN)

    num_classifications = models.IntegerField(default=0)

    max_train_imgs_per_hr = models.IntegerField(
        default=settings.DEFAULT_NUM_TRAINING_IMGS_PER_HOUR
    )
    max_team_members = models.IntegerField(
        default=settings.DEFAULT_MAX_NUM_TEAM_MEMBERS
    )

    last_upload = models.TimeField(null=True)

    is_training_dttm = models.DateTimeField(default=None, null=True)

    # fields acquired on websocket connection
    socket_channel = models.CharField(max_length=255, default=None, null=True)
    local_ip = models.GenericIPAddressField(null=True)

    classifier_model_path = models.CharField(
        max_length=255, default=None, null=True
    )  # prevent calling
    update_dttm = models.DateTimeField(auto_now=True)

    def num_features_added_last_hr(self) -> int:
        return Feature.objects.filter(
            team_id=self.id,
            is_manual=False,
            create_dttm__gt=datetime.now() - timedelta(hours=1),
        ).count()

    def validate_credentials(self, credentials: str) -> bool:
        # return bcrypt.checkpw(credentials, self.credentials.encode())
        return credentials == self.credentials

    def send_ws_message(self, message: WSStruct) -> bool:
        channel_layer = get_channel_layer()
        if not self.socket_channel:
            logging.error(f"{self.username} is not connected to a socket")
            # store message in redis
            return False

        async_to_sync(channel_layer.send)(self.socket_channel, message.dict())
        return True


class Feature(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    member = models.IntegerField()
    features = models.CharField(max_length=2000)  # TODO why 2000
    is_manual = models.BooleanField(default=True)
    score = models.FloatField()
    has_processed = models.BooleanField(default=False)

    create_dttm = models.DateTimeField(auto_now_add=True)
    update_dttm = models.DateTimeField(auto_now=True)

    INIT_TEAM_USERNAME = "init"
