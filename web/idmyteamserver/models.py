from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_email_confirmation.models import SimpleEmailConfirmationUserMixin

from web.settings import (
    DEFAULT_NUM_TRAINING_IMGS_PER_HOUR,
    DEFAULT_NUM_CLASSES,
    DEFAULT_UPLOAD_RETRY_LIMIT,
    PASS_RESET_TOKEN_LEN,
    CREDENTIAL_LEN,
)


class Account(AbstractUser, SimpleEmailConfirmationUserMixin):
    # overwrite AbstractUser field
    email = models.EmailField(_("email address"), blank=True, unique=True)

    password_reset_token = models.CharField(max_length=PASS_RESET_TOKEN_LEN)

    credentials = models.CharField(max_length=CREDENTIAL_LEN)

    num_classifications = models.IntegerField(default=0)

    max_train_imgs_per_hr = models.IntegerField(
        default=DEFAULT_NUM_TRAINING_IMGS_PER_HOUR
    )
    max_class_num = models.IntegerField(default=DEFAULT_NUM_CLASSES)
    upload_retry_limit = models.FloatField(default=DEFAULT_UPLOAD_RETRY_LIMIT)

    local_ip = models.GenericIPAddressField(null=True)

    last_upload = models.TimeField(null=True)

    allow_image_storage = models.BooleanField(default=False)
    is_training = models.BooleanField(default=False)
