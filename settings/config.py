import configparser

conf = configparser.ConfigParser()
conf.read('../conf/secrets.conf')

IMAGE_UPLOAD_DIR = '/var/www/idmy.team/images/'

STORE_IMAGES_DIR = '/var/www/idmy.team/faces/'

MODEL_DIR = '/var/www/idmy.team/python/models/'

FEATURE_EXTRACTOR_IMG_SIZE = 256
MIN_FACE_SIZE = 60
NUM_SHUFFLES = 2
MAX_CLASSIFIER_SIZE_MB = 25
MIN_LOCALISATION_PROB = 0.9
CROP_PADDING = 0
MIN_CLASSIFIER_TRAINING_IMAGES = 10
MIN_PROB = 0
MAX_IMG_UPLOAD_SIZE_KB = 1000
MAX_TRAIN_UPLOAD_SIZE_KB = 100 * 1024  # 100MB - approx 200 images

LOCALISATION_MODEL = '/var/www/idmy.team/python/models/face_localisation.model'
FEATURE_MODEL_DIR = '/var/www/idmy.team/python/models/feature_extractor.model'
CLIENT_MODEL_DIR = '/var/www/idmy.team/python/models/'  # user_hash .model

RECAPTCHA_KEY = conf['secret']['recaptcha']
CRYPTO_KEY = conf['secret']['crypto']
EMAIL_CONFIG = dict(conf.items('email'))

DB = dict(conf.items('database'))

SENTRY_URL = conf['sentry']['url']

###
# web
COOKIE_SECRET = conf['secret']['cookie']

###
# socket
LOCAL_SOCKET_URL = 'ws://localhost:8888'
