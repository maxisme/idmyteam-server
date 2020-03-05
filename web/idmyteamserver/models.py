from django.db import models
from django.contrib.auth.models import AbstractUser
from simple_email_confirmation.models import SimpleEmailConfirmationUserMixin

from web.settings import DEFAULT_NUM_TRAINING_IMGS_PER_HOUR, DEFAULT_NUM_CLASSES, DEFAULT_UPLOAD_RETRY_LIMIT, \
    PASS_RESET_TOKEN_LEN


class Account(AbstractUser, SimpleEmailConfirmationUserMixin):

    password_reset_token = models.CharField(max_length=PASS_RESET_TOKEN_LEN)

    credentials = models.CharField(max_length=150)

    num_classifications = models.IntegerField(default=0)

    max_train_imgs_per_hr = models.IntegerField(default=DEFAULT_NUM_TRAINING_IMGS_PER_HOUR)
    max_class_num = models.IntegerField(default=DEFAULT_NUM_CLASSES)
    upload_retry_limit = models.FloatField(default=DEFAULT_UPLOAD_RETRY_LIMIT)

    local_ip = models.GenericIPAddressField(null=True)

    last_upload = models.TimeField(null=True)

    allow_storage = models.BooleanField(default=False)
    is_training = models.BooleanField(default=False)

