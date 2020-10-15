import ast
import io
import json
import logging
import math
import os
from importlib import import_module
from random import randint

import chainer
import numpy as np
import tensorflow as tf
from PIL import Image
from chainercv.links import FasterRCNNVGG16
from redis import Redis
from rq import Queue

import config
import functions
from classifier import Classifier
from idmyteamserver.models import Team, Feature

chainer.config.train = False  # tells chainer to not be in training mode

redis_conn = Redis()
classifier_q = Queue("low", connection=redis_conn)

from typing import TypedDict, List


class Detecter:
    def __init__(self):
        logging.info("Started loading recognition-worker models...")
        self.face_localiser = self.FaceLocalisation()
        self.feaure_extractor = self.FeatureExtractor()
        logging.info("Finished loading recognition-worker models!")

    class FeatureExtractor:
        model = import_module("train.resnet_v1_50")
        head = import_module("train.fc1024")

        def __init__(self):
            self._load_model()

        def predict(self, img: np.array) -> List:
            return self.sess.detect(
                self.endpoints["emb"], feed_dict={self.image_placeholder: [img]}
            ).tolist()

        def _load_model(self):
            self.image_placeholder = tf.placeholder(
                tf.float32,
                shape=(
                    None,
                    config.FEATURE_EXTRACTOR_IMG_SIZE,
                    config.FEATURE_EXTRACTOR_IMG_SIZE,
                    3,
                ),
            )
            self.endpoints, body_prefix = self.model.endpoints(
                self.image_placeholder, is_training=False
            )
            with tf.name_scope("head"):
                self.head.head(self.endpoints, 128, is_training=False)
            c = tf.ConfigProto()
            c.gpu_options.allow_growth = True
            self.sess = tf.Session(config=c)

            # TODO convert the below path into one file at config.FEATURE_MODEL_DIR (this path looks at multiple files)
            tf.train.Saver().restore(
                self.sess, config.ROOT + "/models/checkpoint-407500"
            )
            #########################################

            # run prediction with white image as the first prediction takes longer than all proceeding ones
            img = np.zeros(
                [
                    config.FEATURE_EXTRACTOR_IMG_SIZE,
                    config.FEATURE_EXTRACTOR_IMG_SIZE,
                    3,
                ],
                dtype=np.uint8,
            )
            img[:] = 255  # set white pixels
            self.predict(img)

    class FaceLocalisation(object):
        def __init__(self):
            self._load_model()

        def predict(self, img: np.array):
            return self.localisation_model.predict([img])

        def _load_model(self):
            self.localisation_model = FasterRCNNVGG16(
                n_fg_class=1, pretrained_model=config.LOCALISATION_MODEL
            )
            self.localisation_model.to_gpu(0)
            chainer.cuda.get_device(0).use()

            # Run prediction with a white image.
            # (The first prediction takes longer than all proceeding ones)
            img = np.zeros([3, 480, 640], dtype=np.uint8)
            img[:] = 255
            self.predict(img)

    def detect(
            self,
            img: bytes,
            file_name: str,
            store_image_features: bool,
            classifier: Classifier,
            team: Team,
    ):
        # parse image bytes to np array
        try:
            img, _ = self._bytes_to_image(img)
        except Exception as e:
            raise Exception(f"Invalid image: {e}")

        # run face localisation and find the face which returns the most likely to be a face
        # TODO MAYBE MAKE RANDOM:
        # AS THIS COULD LEAD TO WHEN TWO PEOPLE COME IN together IT ALWAYS SAYS HELLO
        # TO ONE OF THEM BECAUSE THEY HAVE A CLEARER FACE

        bboxes, labels, scores = self.face_localiser.predict(img)

        if scores:
            bbox = None
            best_coord_score = 0
            if len(scores[0]) > 0:
                logging.info(scores)
                # pick bbox with best score that it is a face
                for i, score in enumerate(scores):
                    s = score[0]
                    if s >= best_coord_score and s >= config.MIN_LOCALISATION_PROB:
                        best_coord_score = s
                        bbox = bboxes[i][0]

                if best_coord_score > 0:
                    # found detected face coords (ints for json)
                    # convert back to our preferred bbox format - (y_min, x_min, y_max, x_max) -> (x,y,w,h)
                    face_coords = FaceCoordinates(
                        x=int(math.floor(bbox[1])),
                        y=int(math.floor(bbox[0])),
                        width=int(math.ceil(bbox[3] - bbox[1])),
                        height=int(math.ceil(bbox[2] - bbox[0])),
                        score=best_coord_score,
                        is_manual=False,
                    )

                    # crop image to coords of face + config.CROP_PADDING
                    img = functions.crop_img(img, face_coords, config.CROP_PADDING)
                    img = functions.pre_process_img(
                        img, config.FEATURE_EXTRACTOR_IMG_SIZE
                    )

                    # extract features from image
                    features = self.feaure_extractor.predict(img)

                    # predict the member based on features
                    member_id, max_prob = classifier.predict(features)

                    # send member classification back to user
                    socket = functions.create_local_socket(config.LOCAL_SOCKET_URL)
                    functions.send_classification(
                        json.dumps(face_coords),
                        member_id,
                        max_prob,
                        file_name,
                        team.username,
                        socket,
                    )

                    if member_id > 0:
                        # increase number of successful classifications
                        team.num_classifications += 1
                        team.save()

                        if store_image_features:
                            # store features in db for further training of model
                            Feature.objects.create(
                                team=team,
                                member=member_id,
                                features=features,
                                manual=False,
                                score=max_prob,
                            )

    def store_image(self, img: bytes, file_name: str, member_id: int, team: Team):
        """
        Stores image for training in the future
        """
        # parse image bytes to np array
        try:
            img, original_image = self._bytes_to_image(img)
        except Exception as e:
            raise Exception(f"Invalid image: {e}")

        # get facial coordinates from comment in original image
        try:
            face_coords = ast.literal_eval(original_image.app["COM"].decode())
        except Exception as e:
            raise Exception(
                f"Training image does not have valid facial coordinates: {e}"
            )

        socket = functions.create_local_socket(config.LOCAL_SOCKET_URL)

        # crop image to coords of face + config.CROP_PADDING
        img = functions.crop_img(img, face_coords, config.CROP_PADDING)
        img = functions.pre_process_img(img, config.FEATURE_EXTRACTOR_IMG_SIZE)

        # extract features from image
        features = self.feaure_extractor.predict(img)

        # insert features into db for training later
        Feature.objects.create(team=team, member=member_id, features=features)

        # create more training features by adding augmentation to images
        for _ in range(config.NUM_SHUFFLES):
            # augment image
            aug_img = functions.img_augmentation(img)
            # extract new features from augmented image
            features = self.feaure_extractor.predict(aug_img)
            # save features
            Feature.objects.create(
                team=team, member=member_id, features=features, manual=False
            )

        # tell the client they can now delete the training image locally
        functions.send_to_client(
            socket,
            team.username,
            {"type": "delete_trained_image", "img_path": file_name},
        )

        if team.allow_image_storage:
            # - permission granted by team to store image for further training
            # - move uploaded image to directory for pending semi anonymous face training (FE and FL).
            file_path = self._get_unique_file_path(team)
            original_image.save(file_path)

    @staticmethod
    def _bytes_to_image(img: bytes) -> (np.array, Image):
        original_image = Image.open(io.BytesIO(img))
        # convert to recognition-worker readable image
        img = original_image.convert("RGB")
        img = np.asarray(img, dtype=np.float32)
        return img.transpose((2, 0, 1)), original_image

    @staticmethod
    def _get_unique_file_path(team: Team) -> str:
        """
        get unique filepath to store face at
        @param team:
        @return:
        """
        hashed_team_member = str(functions.hash(str(team.id) + team.username))
        while True:
            dir = config.STORE_IMAGES_DIR + team.username + "/"
            if not os.path.exists(dir):
                os.makedirs(dir)

            file_path = (
                    dir + hashed_team_member + "_" + str(randint(0, 1e20)) + config.IMG_TYPE
            )
            if not os.path.isfile(file_path):
                break
        return file_path


class FaceCoordinates(TypedDict):
    x: int
    y: int
    width: int
    height: int
    score: float
    is_manual: bool