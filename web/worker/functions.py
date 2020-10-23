import base64
import hashlib
import zlib

try:
    import cv2
    import numpy as np
except ImportError:
    pass


def pre_process_img(img, size):
    return cv2.resize(img, dsize=(size, size), interpolation=cv2.INTER_LINEAR)


def add_coord_padding(img: np.array, padding: int, face_coords):
    """

    @param padding:
    @param img:
    @type face_coords: worker.detecter.FaceCoords
    """
    if padding:
        min_x = 0
        max_x = img.shape[2]
        min_y = 0
        max_y = img.shape[1]

        x = int(face_coords.x - padding)
        if x < min_x:
            x = min_x
        elif x > max_x:
            x = max_x

        y = int(face_coords.y - padding)
        if y > max_y:
            y = max_y
        elif y < min_y:
            y = min_y

        w = int(face_coords.w + padding)
        if x + w > max_x:
            w = max_x - x

        h = int(face_coords.h + padding)
        if y + h > max_y:
            h = max_y - y
    return int(x), int(y), int(w), int(h)  # TODO this REDUCES ACCURACY


def crop_img(img: np.array, face_coords, padding: int):
    """
    @type face_coords: worker.detecter.FaceCoordinates
    """
    x, y, w, h = add_coord_padding(img, padding, face_coords)

    # img = np.array(img)
    img = img[:, y : y + h, x : x + w]
    img = np.moveaxis(img, 0, -1)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    return img


ROT = 10.0
CONT_MIN = 0.85
CONT_MAX = 1.15
BRIGHT_MIN = -45
BRIGHT_MAX = 30
SVP = 0.2  # salt vs pepper
SP_MAX_AMT = 0.004


def img_augmentation(img):
    np.random.uniform(-ROT, ROT)
    contrast = np.random.uniform(CONT_MIN, CONT_MAX)
    bright = np.random.randint(BRIGHT_MIN, BRIGHT_MAX)
    # sp_amt = np.random.uniform(0, SP_MAX_AMT)

    #########################
    # contrast & brightness #
    #########################
    img = img.astype(np.int)
    img = img * contrast + bright
    img[img > 255] = 255
    img[img < 0] = 0
    img = img.astype(np.uint8)

    # ############
    # # rotation #
    # ############
    # if np.random.randint(3) == 0:  # rotate 1/3 times
    #     img = scipy.misc.imrotate(img, angle, "bicubic")

    return img


def hash(s) -> str:
    return hashlib.sha256(str.encode(s)).hexdigest()


def compress_string(s):
    string = s.replace(" ", "")
    string = zlib.compress(str.encode(string))
    string = base64.encodebytes(string)
    return string


def decompress_string(s):
    string = base64.decodebytes(s)
    string = zlib.decompress(string)
    return string.decode("utf-8")


def json_helper(o):
    if isinstance(o, np.int64):
        return int(o)
    if isinstance(o, bytes):
        return o.decode("utf-8")
    raise TypeError
