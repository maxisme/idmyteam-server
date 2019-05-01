import io
import logging
import time
import os
import json
import math
from random import randint
import tensorflow as tf
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # reduce tensorflow logging
import numpy as np

from redis import Redis
from rq import Queue

from settings import functions, config
from importlib import import_module
import ast
import chainer
from PIL import Image
from chainercv.links import FasterRCNNVGG16

chainer.config.train = False  # tells chainer to not be in training mode

redis_conn = Redis()
classifier_q = Queue('low', connection=redis_conn)


class Detecter(object):

    def __init__(self):
        print("Started loading ML models...")
        self.face_localiser = self.FaceLocalisation()
        self.feaure_extractor = self.FeatureExtractor()
        print("Finished loading ML models!")

    class FeatureExtractor(object):
        model = import_module('train.resnet_v1_50')
        head = import_module('train.fc1024')

        def __init__(self):
            self._load_model()

        def predict(self, img, conn=None):
            t = time.time()

            predict = self.sess.run(self.endpoints['emb'], feed_dict={
                self.image_placeholder: [img]
            }).tolist()

            if conn:
                functions.log_data(conn, "Feature Extractor", "Model", "Predict", str(time.time() - t))
            return predict

        def _load_model(self):
            print("Loading feature extractor model ...")
            load_model_begin = time.time()

            ############ LOAD MODEL ##################
            self.image_placeholder = tf.placeholder(tf.float32, shape=(
                None, config.FEATURE_EXTRACTOR_IMG_SIZE, config.FEATURE_EXTRACTOR_IMG_SIZE, 3))
            self.endpoints, body_prefix = self.model.endpoints(self.image_placeholder, is_training=False)
            with tf.name_scope('head'):
                self.head.head(self.endpoints, 128, is_training=False)
            c = tf.ConfigProto()
            c.gpu_options.allow_growth = True
            self.sess = tf.Session(config=c)
            # TODO convert the below path into one file at config.FEATURE_MODEL_DIR (this path looks at multiple files)
            tf.train.Saver().restore(self.sess, '/var/www/idmy.team/python/models/checkpoint-407500')
            #########################################

            # run prediction with white image as the first prediction takes longer than all proceeding ones
            img = np.zeros([config.FEATURE_EXTRACTOR_IMG_SIZE, config.FEATURE_EXTRACTOR_IMG_SIZE, 3], dtype=np.uint8)
            img[:] = 255  # set white pixels
            self.predict(img)

            # how long it took to load model
            load_time = str(time.time() - load_model_begin)
            print("loading feature extractor took" + load_time)
            conn = functions.connect(config.DB["username"], config.DB["password"], config.DB["db"])
            functions.log_data(conn, "Feature Extractor", "Model", "Load", load_time)
            functions.purge_log(conn, "Feature Extractor", "Model", "Predict", "system")  # clear all prediction scores

    class FaceLocalisation(object):
        def __init__(self):
            self._load_model()

        def predict(self, img, conn=None):
            """
            :param img:
            :param conn:
            :return: tuple of lists
            """
            t = time.time()

            try:
                prediction = self.localisation_model.predict([img])
            except Exception as e:
                logging.critical('Localisation model error: %s', e)
                return None, None, None

            if conn:
                functions.log_data(conn, "Face Localisation", "Model", "Predict", str(time.time() - t))
            return prediction

        def _load_model(self):
            print("Loading localisation model...")
            t = time.time()

            ############ LOAD MODEL ##################
            self.localisation_model = FasterRCNNVGG16(n_fg_class=1, pretrained_model=config.LOCALISATION_MODEL)
            self.localisation_model.to_gpu(0)
            chainer.cuda.get_device(0).use()
            #########################################

            # run white pass through image as the first prediction takes longer than all proceeding ones
            img = np.zeros([3, 480, 640], dtype=np.uint8)
            img[:] = 255
            self.predict(img)

            # log how long it took to load model
            load_time = str(time.time() - t)
            print("loading localisation took: " + load_time)
            conn = functions.connect(config.DB["username"], config.DB["password"], config.DB["db"])
            functions.log_data(conn, "Face Localisation", "Model", "Load", load_time)
            functions.purge_log(conn, "Face Localisation", "Model", "Predict", "system")  # clear all predicted scores

    def run(self, img, file_name, hashed_username, classifier, conn, member_id=False, store_image=False,
            store_image_features=True):
        """
        :type classifier: ML.Classifier
        :param img:
        :param file_name:
        :param hashed_username:
        :param classifier:
        :param member_id:
        :param bool store_image: whether to store the trained image file on ID My Team for increased recognition accuraccy.
        :param bool store_image_features: whether to store the predicted images features for constant learning.
        :return:
        """

        is_training = bool(member_id)

        # parse image to array
        format_time = time.time()
        try:
            original_image = Image.open(io.BytesIO(img))
            # convert to ML readable image
            img = original_image.convert('RGB')
            img = np.asarray(img, dtype=np.float32)
            img = img.transpose((2, 0, 1))
        except Exception as e:
            print("not a valid image {}".format(e))
            return False
        print('image format took: %s' % (time.time() - format_time))

        face_coords = None
        if not is_training:
            # run face localisation and find the face which returns the most likely to be a face
            # TODO MAYBE MAKE RANDOM:
            # AS THIS COULD LEAD TO WHEN TWO PEOPLE COME IN together IT ALWAYS SAYS HELLO
            # TO ONE OF THEM BECAUSE THEY HAVE A CLEARER FACE

            bboxes, labels, scores = self.face_localiser.predict(img, conn)

            if scores:
                bbox = None
                best_coord_score = 0
                if len(scores[0]) > 0:
                    # pick bbox with best score that it is a face
                    for i, score in enumerate(scores):
                        s = score[0]
                        if s >= best_coord_score and s >= config.MIN_LOCALISATION_PROB:
                            best_coord_score = s
                            bbox = bboxes[i][0]

                    if best_coord_score > 0:
                        # found detected face coords (ints for json)
                        # convert back to our preferred bbox format - (y_min, x_min, y_max, x_max) -> (x,y,w,h)
                        face_coords = {
                            "x": int(math.floor(bbox[1])),
                            "y": int(math.floor(bbox[0])),
                            "width": int(math.ceil(bbox[3] - bbox[1])),
                            "height": int(math.ceil(bbox[2] - bbox[0])),
                            "score": str(best_coord_score),
                            "method": "model"
                        }

        else:
            # get image file comment with face coords
            try:
                face_coords = ast.literal_eval(original_image.app['COM'].decode())
            except Exception as e:
                logging.warning("Training image does not have valid coordinates %s", e)

        socket = functions.create_local_socket(config.LOCAL_SOCKET_URL)
        if face_coords:
            #############################
            #### feature extraction #####
            #############################

            # crop image to coords of face + config.CROP_PADDING
            pre_time = time.time()
            x, y, w, h = functions.add_coord_padding(img, config.CROP_PADDING, face_coords['x'], face_coords['y'],
                                                     face_coords['width'], face_coords['height'])
            img = functions.crop_img(img, x, y, w, h)
            img = functions.pre_process_img(img, config.FEATURE_EXTRACTOR_IMG_SIZE)
            print('pre_time took: %s' % (time.time() - pre_time))

            feature_time = time.time()
            features = self.feaure_extractor.predict(img, conn)
            print('feature_time took: %s' % (time.time() - feature_time))

            if member_id:
                #######################################
                ## store Features in DB for training ##
                #######################################

                # insert features into db
                functions.store_feature(conn, hashed_username, member_id, features)

                # create more training features by adding augmentation to images
                for _ in range(config.NUM_SHUFFLES):
                    aug_img = functions.img_augmentation(img)
                    features = self.feaure_extractor.predict(aug_img)
                    functions.store_feature(conn, hashed_username, member_id, features, manual=False)

                if store_image:  # permission granted by team to store image
                    # move uploaded image to directory for pending semi anonymous face training (FE and FL).
                    hashed_team_member = str(functions.hash(str(member_id) + hashed_username))
                    file_type = os.path.splitext(file_name)[1]
                    file_path = config.STORE_IMAGES_DIR + hashed_team_member + "_" + str(randint(0, 1e20)) + file_type
                    original_image.save(file_path)

                # forward to client they can now delete the training image locally
                functions.send_json_socket(socket, hashed_username, {
                    "type": "delete_trained_image",
                    "img_path": file_name
                })

            else:
                #######################################################
                ### send FE to custom team model for classification ###
                #######################################################
                predict_time = time.time()
                classifier.predict(features, file_name, face_coords, store_image_features)
                print('predict_time took: %s' % (time.time() - predict_time))

        elif not is_training:
            # no face detected so send INVALID classification
            functions.send_classification(json.dumps(face_coords), -1, 0, file_name, hashed_username, socket)

        print('total took: %s' % (time.time() - format_time))
