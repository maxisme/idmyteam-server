import io
import json
import os
from collections import defaultdict

from redis import Redis
from rq import Queue

import logging
import zipfile
from settings import functions, config, db
from view import BaseHandler
from ML.classifier import Classifier

import authed

redis_conn = Redis()

high_q = Queue("high", connection=redis_conn, default_timeout=60)
med_q = Queue("medium", connection=redis_conn, default_timeout=60)
low_q = Queue("low", connection=redis_conn, default_timeout=600)


class ImageUploadHandler(BaseHandler):
    def post(self):
        try:
            username = self.request.arguments["username"][0].decode()
            credentials = self.request.arguments["credentials"][0].decode()
        except Exception as e:
            logging.error(e)
            return self.write_error(404)

        content_len = functions.bytes_to_kb(int(self.request.headers["Content-Length"]))
        if content_len > config.MAX_TRAIN_UPLOAD_SIZE_KB:
            return self.write("Upload file too large")

        self.conn = db.pool.connect()
        hashed_username = functions.hash(username)
        if functions.Team.valid_credentials(
            self.conn, hashed_username, credentials, config.SECRETS["crypto"]
        ):
            if hashed_username in authed.clients:
                if functions.Team.allowed_to_upload(self.conn, hashed_username):
                    if "img_file" in self.request.files:
                        #####################
                        # PREDICTING upload #
                        #####################
                        if content_len <= config.MAX_IMG_UPLOAD_SIZE_KB:
                            if Classifier.get_model_path(hashed_username):
                                # There is a classifier for username
                                try:
                                    store_features = bool(
                                        self.request.arguments["store-features"][0]
                                    )
                                except:
                                    return self.return_error("No features")

                                upload = self.request.files["img_file"][0]
                                img = upload["body"]
                                file_name = self.request.arguments["file-name"][0]

                                med_q.enqueue_call(
                                    func=".",
                                    kwargs={
                                        "type": "detect",
                                        "img": img,
                                        "file_name": file_name,
                                        "hashed_username": hashed_username,
                                        "store_image_features": store_features,
                                    },
                                )
                            else:
                                logging.error(
                                    "Prediction request before trained model! %s",
                                    hashed_username,
                                )
                                return self.return_error(
                                    "The team needs to train before you can predict."
                                )
                        else:
                            logging.warning(
                                "Image upload size too big (%sKB) from ip (%s)",
                                (content_len, self.request.headers["X-Real-Ip"]),
                            )
                            return self.return_error("Image upload size too large.")
                    elif "ZIP" in self.request.files:
                        ###################
                        # TRAINING upload #
                        ###################
                        num_trained = functions.Team.get_num_trained_last_hr(
                            self.conn, hashed_username
                        )

                        user = functions.Team.get(self.conn, username=hashed_username)
                        max_train_imgs_per_hr = user["max_train_imgs_per_hr"]

                        z = zipfile.ZipFile(
                            io.BytesIO(self.request.files["ZIP"][0]["body"])
                        )
                        if z:
                            imgs_to_upload = defaultdict(list)
                            for file in z.infolist():
                                if file.file_size > 0:
                                    if (
                                        file.file_size / 1024
                                        > config.MAX_IMG_UPLOAD_SIZE_KB
                                    ):
                                        return self.return_error(
                                            "Training image {} file is too large!".format(
                                                file.filename
                                            )
                                        )

                                    try:
                                        member = int(os.path.dirname(file.filename))
                                    except:
                                        logging.error("Invalid file uploaded")
                                        continue

                                    imgs_to_upload[member].append(file)

                            train_quota = max_train_imgs_per_hr - num_trained

                            imgs_to_upload = functions.crop_arr(
                                imgs_to_upload, train_quota
                            )

                            if not imgs_to_upload:
                                return self.return_error(
                                    "You have uploaded too many training images. Please try again later..."
                                )
                            elif len(imgs_to_upload) < 2 and not Classifier.exists(
                                hashed_username
                            ):
                                return self.return_error(
                                    "You must train with at least 2 team members."
                                )

                            for member in imgs_to_upload:
                                for file in imgs_to_upload[member]:
                                    img = z.read(file)
                                    low_q.enqueue_call(
                                        func=".",
                                        kwargs={
                                            "type": "detect",
                                            "img": img,
                                            "file_name": file.filename,
                                            "hashed_username": hashed_username,
                                            "member_id": member,
                                            "store_image": bool(user["allow_storage"]),
                                        },
                                    )

                            # tell model to train
                            low_q.enqueue_call(
                                func=".",
                                kwargs={
                                    "type": "train",
                                    "hashed_username": hashed_username,
                                },
                            )

                        else:
                            return self.return_error("Invalid ZIP")
                    self.write("Uploaded")
            else:
                return self.return_error("Not connected to socket")

    # OVERIDE XSRF CHECK
    def check_xsrf_cookie(self):
        pass

    def return_error(self, message):
        if not isinstance(message, dict):
            message = {"message": message}
        message = json.dumps(message)
        return self.set_status(400, message)
