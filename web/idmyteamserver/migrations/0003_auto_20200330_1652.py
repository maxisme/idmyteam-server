# Generated by Django 3.0.3 on 2020-03-30 16:52

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("idmyteamserver", "0002_auto_20200330_1648"),
    ]

    operations = [
        migrations.RenameField(
            model_name="account",
            old_name="storeimage",
            new_name="allow_image_storage",
        ),
    ]
