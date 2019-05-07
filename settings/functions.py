# common functions used in multiple scripts
import base64
import json
import logging
import os
import random
import smtplib
import string
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import MySQLdb
import cv2
import scipy
import yaml
import zlib
import socket
import numpy as np
from Crypto import Random
from Crypto.Cipher import AES
import bcrypt
import hashlib
from itsdangerous import URLSafeTimedSerializer
from premailer import transform

from tornado import template
from websocket import create_connection


def get_YAML(file):
    with open(file, 'r') as f:
        content = yaml.load(f)
    return content


# connects to db using credentials
class DB:
    @classmethod
    def conn(cls, u, p, db):
        return MySQLdb.connect(host="127.0.0.1", user=u, passwd=p, db=db)

    @classmethod
    def execute_sql_in_file(cls, conn, file):
        x = conn.cursor()
        if not os.path.isfile(file):
            raise Exception('No such file %s', file)
        sql = open(file, 'r').read()
        try:
            x.execute(sql)
        except Exception as e:
            print(sql)
        finally:
            x.close()


# marks a team as training in the database
def toggle_team_training(conn, hashed_username, training=True):
    training = training * 1  # convert to int
    x = conn.cursor()
    try:
        x.execute("UPDATE `Accounts` SET `is_training` = %s WHERE `username` = %s", (training, hashed_username))
        conn.commit()
    except Exception as e:
        print("error - didn't mark as finished training %s" % e)
        conn.rollback()
    finally:
        x.close()


# stores features from the feature extractor model in the database
def store_feature(conn, hashed_team_username, member_id, features, manual=True, score=0.0):
    # compress features for storage
    features = compress_string(str(features))

    type = 'MANUAL' if manual else 'MODEL'

    # store feature in db
    x = conn.cursor()
    try:
        x.execute("""INSERT INTO `Features` (username, `class`, `type`, `features`, `score`)
                  VALUES (%s, %s, %s, %s, %s)""", (hashed_team_username, member_id, type, features, score))
        conn.commit()
    except MySQLdb.Error as e:
        print(("Couldn't write feature: " + str(e)))
        conn.rollback()
    finally:
        x.close()


# formats message in mannor for client to receive a classification (recognition)
def send_classification(coords, member_id, recognition_score, file_id, hashed_username, socket):
    """
    :param coords:
    :param member_id: predicted member
    :param recognition_score:
    :param file_id:
    :param hashed_username:
    :return:
    """
    send_json_socket(socket, hashed_username, {
        "type": "classification",
        "coords": coords,
        "member_id": member_id,
        "recognition_score": recognition_score,
        "file_id": file_id
    })


# writes data log to database as can be seen in idmy.team/stats
def log_data(conn, name, type, method, val, user="system", yaxis="Seconds"):
    x = conn.cursor()
    try:
        x.execute("INSERT INTO `Logs` (`type`, `name`, `method`, `value`, username, `yaxis`) "
                  "VALUES (%s, %s, %s, %s, %s, %s)", (type, name, method, str(val), user, yaxis))
        conn.commit()
    except MySQLdb.Error as e:
        logging.error("didnt write feature: %s", e)
        conn.rollback()
    finally:
        x.close()


# deletes data log
def purge_log(conn, name, type, method, user):
    x = conn.cursor()
    try:
        x.execute("DELETE FROM `Logs` WHERE username = %s AND `type` = %s AND `method` = %s AND `name` = %s",
                  (user, type, method, name))
        conn.commit()
    except:
        conn.rollback()
    finally:
        x.close()


# Pre process a cropped image of the face for the feature extractor model.
def pre_process_img(img, size):
    img = scipy.misc.imresize(img, (size, size), interp='bilinear')
    # img = np.expand_dims(img, axis=0)
    return img


# adds some `padding` to bbox
def add_coord_padding(img, padding, x, y, w, h):
    if padding:
        min_x = 0
        max_x = img.shape[2]
        min_y = 0
        max_y = img.shape[1]

        x = int(x - padding)
        if x < min_x:
            x = min_x
        elif x > max_x:
            x = max_x

        y = int(y - padding)
        if y > max_y:
            y = max_y
        elif y < min_y:
            y = min_y

        w = int(w + padding)
        if x + w > max_x:
            w = max_x - x

        h = int(h + padding)
        if y + h > max_y:
            h = max_y - y
    return int(x), int(y), int(w), int(h)  # TODO this REDUCES ACCURACY


def crop_img(img, x, y, w, h):
    img = np.array(img)
    img = img[:, y:y + h, x:x + w]
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
    angle = np.random.uniform(-ROT, ROT)
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

    ############
    # rotation #
    ############
    if np.random.randint(3) == 0:  # rotate 1/3 times
        img = scipy.misc.imrotate(img, angle, 'bicubic')

    # ###################
    # # salt and pepper #
    # ###################
    # # salt
    # coords = [np.random.randint(0, i - 1, int(np.ceil(sp_amt * img.size * SVP))) for i in img.shape]
    # img[coords[0], coords[1], :] = 1
    # # pepper
    # coords = [np.random.randint(0, i - 1, int(np.ceil(sp_amt * img.size * (1.0 - SVP)))) for i in img.shape]
    # img[coords[0], coords[1], :] = 0

    ########
    # blur #
    ########
    # gaussian = np.random.random((img.shape[0], img.shape[1], 1)).astype(np.float32)
    # gaussian = np.concatenate((gaussian, gaussian, gaussian), axis=2)
    # img = cv2.addWeighted(img, 0.85, 0.25 * gaussian, 0.25, 0)

    return img


class Team(object):

    @classmethod
    def get(cls, conn, username):
        x = conn.cursor(MySQLdb.cursors.DictCursor)
        try:
            x.execute("SELECT * FROM Accounts WHERE username = %s", (username,))
            return x.fetchall()[0]
        except IndexError:
            return None

    @classmethod
    def sign_up(cls, conn, username, password, email, allow_storage, key):
        hashed_username = hash(username)
        password = hash_pw(password)
        credentials = AESCipher(key).encrypt(random_str(50))

        x = conn.cursor()
        try:
            x.execute("INSERT INTO `Accounts` (email, username, password, credentials, allow_storage) "
                      "VALUES (%s, %s, %s, %s, %s);", (email, hashed_username, password, credentials, allow_storage))
            conn.commit()
        except MySQLdb.Error as e:
            print(("Couldn't sign up: " + str(e)))
            conn.rollback()
            return False
        finally:
            x.close()
        return True

    @classmethod
    def email_to_username(cls, conn, email):
        x = conn.cursor()
        try:
            x.execute("SELECT username FROM `Accounts` WHERE email=%s", (email,))
            return x.fetchall()[0][0]
        except IndexError:
            return None
        finally:
            x.close()

    @classmethod
    def valid_credentials(cls, conn, username, credentials, key):
        hashed_username = hash(username)
        x = conn.cursor()
        try:
            x.execute("""
            SELECT `credentials`
            FROM Accounts
            WHERE `username` = %s
            """, (hashed_username,))
            encrypted_credentials = x.fetchall()[0][0]

            return decrypt(encrypted_credentials, key) == credentials
        except Exception as e:
            logging.info("Couldn't fetch credentials %s", e)
            return False

    @classmethod
    def allowed_to_upload(cls, conn, hashed_username):
        t = time.time()
        x = conn.cursor()
        try:
            x.execute("""
            SELECT `last_upload`, `upload_retry_limit`
            FROM Accounts
            WHERE `username` = %s
            """, (hashed_username,))

            result = x.fetchall()[0]
            if result[0]:
                last_upload = float(result[0]) or 0
                upload_retry_limit = float(result[1])

                if t - last_upload < upload_retry_limit:
                    return False
        except Exception as e:
            logging.error("allowed_to_predict %s", e)
            return False

        # insert new last_upload time
        try:
            x.execute("""
            UPDATE `Accounts`
            SET last_upload = %s
            WHERE username = %s""", (str(t), hashed_username))
            conn.commit()
            return True
        except MySQLdb.Error as e:
            logging.error("Couldn't add last_upload: %s", e)
            conn.rollback()
            return False

    @classmethod
    def get_num_trained_last_hr(cls, conn, hashed_username):
        x = conn.cursor()
        try:
            x.execute("""
            SELECT count(id)
            FROM Features
            WHERE username = %s
            AND type = 'MODEL'
            AND create_dttm > DATE_SUB(NOW(), INTERVAL 1 HOUR)""", (hashed_username,))
            return x.fetchall()[0][0]
        except Exception as e:
            logging.error("get_num_trained_last_hr %s", e)
            return False

    @classmethod
    def increase_num_classifications(cls, conn, hashed_username):
        x = conn.cursor()
        try:
            x.execute("""
            UPDATE Accounts
            SET num_classifications = num_classifications + 1
            WHERE username = %s
            """, (hashed_username,))
            conn.commit()
            return True
        except MySQLdb.Error as e:
            print(("Couldn't increment num_classifications: " + str(e)))
            conn.rollback()
            return False

    @classmethod
    def toggle_storage(cls, conn, hashed_username):
        x = conn.cursor()
        try:
            x.execute("""
            UPDATE Accounts
            SET allow_storage = 1 - allow_storage
            WHERE username = %s""", (hashed_username,))
            conn.commit()
            return True
        except MySQLdb.Error as e:
            print(("Couldn't toggle_storage: " + str(e)))
            conn.rollback()
            return False

    @classmethod
    def num_users(cls, conn, username):
        x = conn.cursor()
        try:
            x.execute("SELECT num_classes FROM Account_Users WHERE username = %s", (username,))
            return x.fetchall()[0][0]
        except IndexError:
            return None

    @classmethod
    def delete(cls, conn, hashed_username):
        x = conn.cursor()

        # delete logs
        try:
            x.execute("""
            DELETE from `Logs`
            WHERE username = %s""", (hashed_username,))
            conn.commit()
        except MySQLdb.Error as e:
            print(("Couldn't delete users logs: " + str(e)))
            return False

        # delete features
        try:
            x.execute("""
            DELETE from `Features`
            WHERE username = %s""", (hashed_username,))
            conn.commit()
        except MySQLdb.Error as e:
            print(("Couldn't delete users features: " + str(e)))
            return False

        # delete account
        try:
            x.execute("""
            DELETE from `Accounts`
            WHERE username = %s""", (hashed_username,))
            conn.commit()
        except MySQLdb.Error as e:
            print(("Couldn't delete user account: " + str(e)))
            return False

        return True

    class ConfirmEmail:
        @classmethod
        def send_confirmation(cls, conn, email, username, email_config, root):
            if cls.can_confirm(conn, email):
                token = EmailValidation.generate_token(email, email_config['key'])

                if cls._store_confirmation_token(conn, email, token):
                    # generate email content
                    msg = MIMEMultipart("alternative")
                    msg['From'] = email_config['email']
                    msg['To'] = email
                    msg['Subject'] = 'Confirm your ID My Team email'
                    email_html = cls._gen_template(root, 'confirm.html', email=email, token=token, username=username)
                    msg.attach(email_html)

                    # send email
                    with smtplib.SMTP(email_config['smtp'], port=email_config['smtp_port']) as smtp_server:
                        smtp_server.ehlo()
                        smtp_server.starttls()
                        smtp_server.ehlo()
                        smtp_server.login(email_config['email'], email_config['password'])
                        smtp_server.send_message(msg)
                return token
            else:
                return False

        @classmethod
        def _gen_template(cls, root, file, **kwargs):
            loader = template.Loader(root + "/web/")
            email_html = loader.load("templates/emails/inline/"+file).generate(**kwargs).decode()
            return MIMEText(email_html, "html")

        @classmethod
        def _store_confirmation_token(cls, conn, email, token):
            x = conn.cursor()
            try:
                x.execute("""
                UPDATE `Accounts`
                SET email_confirm_token = %s
                WHERE email = %s""", (token, email))
                conn.commit()
                return True
            except MySQLdb.Error as e:
                logging.error("Couldn't add confirm_secret: %s", e)
                conn.rollback()
                return False

        @classmethod
        def validate_token(cls, conn, email, token, email_secret_key):
            try:
                valid_token = EmailValidation.confirm_token(token, email, email_secret_key)
            except Exception as e:
                logging.error(e)
                return False

            if valid_token:
                x = conn.cursor()
                try:
                    x.execute("""
                        UPDATE `Accounts`
                        SET confirmed_email = NOW()
                        WHERE email = %s""", (email,))
                    conn.commit()
                    return True
                except MySQLdb.Error as e:
                    logging.error("Couldn't confirm email: %s", e)
                    conn.rollback()
                finally:
                    x.close()
            return False

        @classmethod
        def can_confirm(cls, conn, email):
            x = conn.cursor()
            try:
                x.execute("SELECT id, confirmed_email FROM Accounts WHERE email = %s", (email,))
                results = x.fetchall()[0]
                id = results[0]
                confirmed_email = results[1]
                if id and not confirmed_email:
                    return True
                return False
            except IndexError:
                return False
            finally:
                x.close()


def create_local_socket(url):
    return create_connection(url + "/local")


def send_json_socket(socket, hashed_username, dic):
    """
    :type dic: dict
    :param hashed_username:
    :param dic:
    :return:
    """
    dic['hashed_username'] = hashed_username
    socket.send(json.dumps(dic, default=json_helper))


def random_str(length):
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))




class AESCipher:
    def __init__(self, key, byte_size=32):
        self.key = base64.b64decode(key)
        self.bs = byte_size

    def encrypt(self, raw):
        raw = self._pad(raw)
        iv = Random.new().read(AES.block_size)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return base64.b64encode(iv + cipher.encrypt(raw))

    def decrypt(self, enc):
        enc = base64.b64decode(enc)
        iv = enc[:16]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return self._unpad(cipher.decrypt(enc[16:])).decode('utf8')

    def _pad(self, s):
        return bytes(s + (self.bs - len(s) % self.bs) * chr(self.bs - len(s) % self.bs), 'utf-8')

    def _unpad(self, s):
        return s[0:-ord(s[-1:])]


def hash_pw(s):
    return bcrypt.hashpw(str.encode(s), bcrypt.gensalt()).decode('utf-8')


def check_pw_hash(s, h):
    """
    :param s: string to compare with a hash
    :param h: a hash
    :return: matching
    """
    return str.encode(h) == bcrypt.hashpw(str.encode(s), str.encode(h))


def hash(s):
    return hashlib.sha256(str.encode(s)).hexdigest()


def compress_string(s):
    string = s.replace(' ', '')
    string = zlib.compress(str.encode(string))
    string = base64.encodebytes(string)
    return string


def decompress_string(s):
    string = base64.decodebytes(s)
    string = zlib.decompress(string)
    return string.decode('utf-8')


def is_valid_ip(ip):
    try:
        socket.inet_aton(str(ip))  # legal
        return True
    except socket.error:  # Not legal
        return False


def bytes_to_kb(bytes):
    return bytes / 1024


def json_helper(o):
    if isinstance(o, np.int64):
        return int(o)
    if isinstance(o, bytes):
        return o.decode('utf-8')
    raise TypeError


def crop_arr(arr, num):
    if num <= 0:
        return {}

    new_arr = {}
    each, rem = divmod(num, len(arr))
    for i, key in enumerate(arr):
        if i < rem:
            new_arr[key] = arr[key][:each + 1]
        else:
            new_arr[key] = arr[key][:each]
    return new_arr


class EmailValidation:
    @classmethod
    def generate_token(cls, email, secret_key):
        serializer = URLSafeTimedSerializer(secret_key)
        return serializer.dumps(email)

    @classmethod
    def confirm_token(cls, token, email, secret_key, expiration=3600):
        serializer = URLSafeTimedSerializer(secret_key)
        return serializer.loads(token, max_age=expiration) == email
