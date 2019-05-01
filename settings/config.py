# settings for the whole remote server system.

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

RECAPTCHA_KEY = '6LfthEQUAAAAAHP1_WPyWQ_R7A4Wa0Jy_zEROHP6'
CRYPTO_KEY = 'BAdZFm0/1Wa2ynQn+F+1NSXL6yJhC42VP1SQ0lvxulI='
EMAIL_CONFIG = {
    'key': 'q8s5KzAxabtXBhEZp9DS5lgP3WvvOLNBnHBPipct'
}

DB = {
    'username': 'idmyteam_user',
    'password': 'pPArS16chi9zMBGEqPNVcaY4NodtSu5pSK5rWFFq!',
    'db': 'idmyteam'
}

SENTRY_URL = 'https://41ff4de927694cb7bf28dd4ce3e083d0:b1f0d66b3fe447c48fa08f2ef70f2a14@sentry.io/1335020'

###
# web
cookie_secret='FeDFFg49mtvSXPBAHBqknUwGn0e14K'

###
# socket
LOCAL_SOCKET_URL = 'ws://localhost:8888'