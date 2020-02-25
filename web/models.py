from django.db import models
from django.contrib.auth.models import User


class User(User):
    RESET_TOKEN_LEN = 200
    HASH_LEN = 64

    username = models.CharField(max_length=HASH_LEN, unique=True)
    email = models.EmailField(unique=True)

    confirmed_email_dttm = models.TimeField()
    email_confirm_token = models.CharField(max_length=RESET_TOKEN_LEN)

    password_reset_token = models.CharField(max_length=RESET_TOKEN_LEN)

    credentials = models.CharField()

    num_classifications = models.IntegerField()

    max_train_imgs_per_hr = models.IntegerField()
    max_class_num = models.IntegerField()
    upload_retry_limit = models.FloatField()

    local_ip = models.IPAddressField()

    last_upload = models.TimeField()

    allow_storage = models.BooleanField(default=False)
    is_training = models.BooleanField(default=False)

    create_dttm = models.TimeField()


class Login(models.Model):
    dttm = models.TimeField(auto_now=True)
    account = models.ForeignKey(User, on_delete=models.CASCADE)
    ip = models.IPAddressField()
