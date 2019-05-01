"""
used to crop a dataset of faces (at IN) using our face localisation model
ads a file called .cropped.jpg
"""

import fnmatch
import glob
import random

import cv2

import chainer
import os

import numpy as np
from chainercv.links import FasterRCNNVGG16
from chainercv import utils
chainer.config.train = False # tells chainer to not be in training mode

localisation_model = FasterRCNNVGG16(n_fg_class=1, pretrained_model='/var/www/idmy.team/python/models/face_localisation.model')
localisation_model.to_gpu(0)
chainer.cuda.get_device(0).use()

from settings import config

IN = "/var/www/idmy.team/python/data-sets/Faces/essex/"
OUT = "/var/www/idmy.team/python/data-sets/Faces/CROPPED/"

def find_files(directory, pattern):
    for root, dirs, files in os.walk(directory, topdown=True):
        files.sort(reverse=True)
        for basename in files:
            if fnmatch.fnmatch(basename, pattern):
                filename = os.path.join(root, basename)
                yield filename

print('STARTED')
img_cnt = 0
classes = [path for path in os.listdir(IN) if os.path.isdir(os.path.join(IN, path))]
random.shuffle(classes)
for c in classes:
    images = glob.glob(IN + c + "/*.jpg")
    if len(images) >= 3: # must contain 3 or more photos of the same person
        for img_path in images:
            out_path = img_path.replace(IN, OUT)
            if not os.path.isfile(out_path):
                try:
                    img = utils.read_image(img_path)
                except:
                    print("not a valid image " + img_path)
                bboxes, labels, scores = localisation_model.predict([img])

                if len(scores[0]) > 0:
                    # pick face with best score that it is a face
                    best_score = 0
                    for i, score in enumerate(scores):
                        s = score[0]
                        if s >= best_score:
                            best_score = s
                            bbox = bboxes[i][0]
                        bbox = bboxes[i][0]
                        x = int(bbox[1])
                        y = int(bbox[0])
                        w = int(bbox[3]) - int(bbox[1])
                        h = int(bbox[2]) - int(bbox[0])
                        img = np.moveaxis(img, 0, -1)

                    if w > config.MIN_FACE_SIZE and h > config.MIN_FACE_SIZE:
                        img = cv2.imread(img_path)
                        img = img[y:y + h, x:x + w]

                        #mkdir
                        dir = os.path.dirname(out_path)
                        if not os.path.exists(dir):
                            os.makedirs(dir)

                        cv2.imwrite(out_path, img)
                        print(out_path)
                        img_cnt += 1
                else:
                    print("no scores")
            else:
                print(".", end=' ')
print(img_cnt)
print("done")