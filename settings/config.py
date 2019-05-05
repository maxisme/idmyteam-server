import configparser
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))

conf = configparser.ConfigParser()
conf.read(ROOT + os.environ['CONF'])

EMAIL_CONFIG = dict(conf.items('emails'))
DB = dict(conf.items('database'))
RECAPTCHA_KEY = conf['secrets']['recaptcha']
CRYPTO_KEY = conf['secrets']['crypto']
COOKIE_SECRET = conf['secrets']['cookie']
SENTRY_URL = conf['sentry']['url']

IMAGE_UPLOAD_DIR = ROOT+'/images/'
STORE_IMAGES_DIR = ROOT+'/faces/'
MODEL_DIR = ROOT+'/python/models/'
LOCALISATION_MODEL = ROOT+'/python/models/face_localisation.model'
FEATURE_MODEL_DIR = ROOT+'/python/models/feature_extractor.model'
CLIENT_MODEL_DIR = ROOT+'/python/models/'  # user_hash .model
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

###
# socket
LOCAL_SOCKET_URL = 'ws://localhost:8888'
