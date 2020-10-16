import logging
from datetime import datetime, timedelta
from typing import Type

import bcrypt
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_email_confirmation.models import SimpleEmailConfirmationUserMixin

from idmyteamserver.structs import WSStruct
from web import settings


class Team(AbstractUser, SimpleEmailConfirmationUserMixin):
    # overwrite AbstractUser field
    email = models.EmailField(_("email address"), blank=True, unique=True)

    password_reset_token = models.CharField(max_length=settings.PASS_RESET_TOKEN_LEN)

    credentials = models.CharField(max_length=255)
    CREDENTIALS_FIELD = "credentials"

    num_classifications = models.IntegerField(default=0)

    max_train_imgs_per_hr = models.IntegerField(
        default=settings.DEFAULT_NUM_TRAINING_IMGS_PER_HOUR
    )
    max_class_num = models.IntegerField(default=settings.DEFAULT_NUM_CLASSES)
    upload_retry_limit = models.FloatField(default=settings.DEFAULT_UPLOAD_RETRY_LIMIT)

    local_ip = models.GenericIPAddressField(null=True)

    last_upload = models.TimeField(null=True)

    allow_image_storage = models.BooleanField(default=False)
    is_training_dttm = models.DateTimeField(default=None, null=True)

    socket_channel = models.CharField(max_length=255, default=None, null=True)

    model_path = models.CharField(max_length=255, default=None, null=True)
    update_dttm = models.DateTimeField(auto_now=True)

    def num_features_added_last_hr(self) -> int:
        return self.objects.filter(
            feature__manual=False,
            feature__create_dttm__gt=datetime.now() - timedelta(hours=1),
        ).count()

    def validate_credentials(self, credentials: bytes) -> bool:
        # return bcrypt.checkpw(credentials, self.credentials.encode())
        return credentials == self.credentials.encode()

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

    INIT_team_username = "init"
