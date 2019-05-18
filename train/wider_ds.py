# parse wider dataset to chainercv dataset format for  train_face_localisation
import chainer
from chainercv.utils import read_image
import numpy as np
import os
from PIL import Image

class WiderDataset(chainer.dataset.DatasetMixin):
    def __init__(self, root_dir, annotation_file):

        self.paths = []
        self.bboxs = {}

        current_path = None
        width, height = None, None
        file_bboxs = []
        start = True
        with open(annotation_file) as f:
            for line in f:
                if "/" in line:
                    tmp_path = root_dir+line.strip()
                    # if change in current_path store all coords for last one
                    if tmp_path != current_path and os.path.isfile(tmp_path):
                        if len(file_bboxs) > 0:
                            if current_path == '/var/www/idmy.team/data-sets/Faces/WIDER/WIDER_train/images/0--Parade/0_Parade_marchingband_1_849.jpg':
                                print(file_bboxs)
                            self.paths.append(current_path)
                            file_bboxs = np.array(file_bboxs).astype(np.float32)
                            file_bboxs = file_bboxs[:, [1,0,3,2]] # swap to bbox format used by chainer (y_min, x_min, y_max, x_max)
                            self.bboxs[current_path] = file_bboxs

                        file_bboxs = [] # reset bbox array

                    current_path = tmp_path
                    width, height = Image.open(tmp_path).size
                else:
                    # get coords
                    coords = line.split()
                    if len(coords) > 1:
                        x1 = int(coords[0])
                        y1 = int(coords[1])
                        x2 = x1 + int(coords[2]) # x1 + width
                        y2 = y1 + int(coords[3]) # y1 + height

                        # check legal bbox
                        if x1 >= 0 and y1 >= 0 and x2 <= width and y2 <= height and x2 - x1 > 0 and y2 - y1 > 0:
                            file_bboxs.append([x1,y1,x2,y2])
                        else:
                            print("ilegal bbox in "+ current_path)


    def __len__(self):
        return len(self.paths)

    def get_example(self, i):
        img_path = self.paths[i]

        bboxs = self.bboxs[img_path].astype(np.float32)
        labels = np.zeros(len(bboxs), dtype=np.int32)

        img = read_image(img_path, color=True)

        return img, bboxs, labels
