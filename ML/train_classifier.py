# the create_model function within this script is called from run_detecter.py when the last file to be trained
# has had its features stored.
import json
import os, time, ast
from pwd import getpwnam
import zmq
import MySQLdb
from sklearn.externals import joblib
from sklearn.model_selection import cross_val_score
from sklearn.model_selection import ShuffleSplit
from sklearn.svm import SVC
import numpy as np
import os.path
from random import randint

from settings import functions, config






