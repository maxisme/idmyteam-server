from datetime import datetime, timedelta

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_email_confirmation.models import SimpleEmailConfirmationUserMixin

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
    is_training_dttm = models.DateTimeField(default=None)

    model_path = models.CharField(max_length=255, default=None, null=True)
    create_dttm = models.DateTimeField(auto_now_add=True)
    update_dttm = models.DateTimeField(auto_now=True)

    def num_features_added_last_hr(self) -> int:
        return self.objects.filter(
            feature__manual=False,
            feature__create_dttm__gt=datetime.now() - timedelta(hours=1),
        ).count()


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
