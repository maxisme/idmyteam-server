from django.db import models
from django.contrib.auth.models import User
from simple_email_confirmation.models import SimpleEmailConfirmationUserMixin


class Account(SimpleEmailConfirmationUserMixin, User):
    PASS_RESET_TOKEN_LEN = 200

    password_reset_token = models.CharField(max_length=PASS_RESET_TOKEN_LEN)

    credentials = models.CharField(max_length=150)

    num_classifications = models.IntegerField()

    max_train_imgs_per_hr = models.IntegerField()
    max_class_num = models.IntegerField()
    upload_retry_limit = models.FloatField()

    local_ip = models.GenericIPAddressField()

    last_upload = models.TimeField()

    allow_storage = models.BooleanField(default=False)
    is_training = models.BooleanField(default=False)

    create_dttm = models.TimeField()


class Login(models.Model):
    dttm = models.TimeField(auto_now=True)
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    ip = models.GenericIPAddressField()
