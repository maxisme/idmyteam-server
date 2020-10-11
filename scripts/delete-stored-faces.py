# attached to cron ran every hour
# 18 * * * * PYTHONPATH="/var/www/f-server/:$PYTHONPATH" && CONF=/conf/prod_remote.conf && python /var/www/f-server/scripts/delete-stored-faces.py
import datetime
import logging

from utils import config
import os

num_deleted = 0
num_seen = 0
for root, dirs, files in os.walk(config.STORE_IMAGES_DIR):
    for file in files:
        if file.endswith(config.IMG_TYPE):
            file_path = os.path.join(root, file)
            allowed_time = datetime.datetime.fromtimestamp(
                os.stat(file_path).st_mtime
            ) + datetime.timedelta(config.ALLOWED_STORAGE_DAYS)

            num_seen += 1
            if allowed_time <= datetime.datetime.now():
                try:
                    os.unlink(file_path)
                    num_deleted += 1
                except Exception as e:
                    logging.error(e)

print(
    "Deleted {} images. Iterated {} others.".format(num_deleted, num_seen - num_deleted)
)
