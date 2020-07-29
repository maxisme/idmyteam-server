# parse images in training folder on idmy.team to chainercv dataset format for train_face_localisation
from glob import glob
import chainer
from chainercv.utils import read_image
import numpy as np

from utils import functions

# class design replicates https://github.com/chainer/chainercv/blob/master/chainercv/datasets/voc/voc_bbox_dataset.py
class TeamParser(chainer.dataset.DatasetMixin):
    def __init__(self, image_dir):
        self.paths = []
        self.bboxs = {}

        for image in glob(image_dir + "*.jpg"):
            img_path = image_dir + image
            bbox = functions.read_img_comment(img_path)
            if bbox:
                # bbox to y1, x1, y2, x2
                bbox = bbox[:, 2:4] + bbox[:, 0:2].astype(np.float32)

                self.paths.append(img_path)
                self.bboxs[img_path] = bbox.astype(np.float32)

    def __len__(self):
        return len(self.paths)

    def get_example(self, item):
        img_path = self.paths[item]
        bbox = self.bboxs[img_path].astype(np.float32)
        img = read_image(img_path, color=True)

        return img, bbox, 0
