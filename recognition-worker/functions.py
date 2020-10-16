# # common functions used in multiple scripts
# import base64
# import json
# import logging
# import os
# import random
# import shutil
# import string
# import time
# import MySQLdb
# import cv2
# from PIL import Image
# import yaml
# import zlib
# import socket
# import numpy as np
# from Crypto import Random
# from Crypto.Cipher import AES
# import bcrypt
# import hashlib
# from itsdangerous import URLSafeTimedSerializer
#
#
#
# formats message for client to receive a classification (recognition-worker)
import base64
import hashlib
import json
import zlib

import cv2
import numpy as np
from websocket import create_connection


#
#
# # writes data log to database as can be seen in idmy.team/stats
# def log_data(conn, name, type, method, val, user="system", yaxis="Seconds"):
#     x = conn.cursor()
#     try:
#         x.execute(
#             "INSERT INTO `Logs` (`type`, `name`, `method`, `value`, username, `yaxis`) "
#             "VALUES (%s, %s, %s, %s, %s, %s)",
#             (type, name, method, str(val), user, yaxis),
#         )
#         conn.commit()
#     except MySQLdb.Error as e:
#         logging.error("didnt write feature: %s", e)
#         conn.rollback()
#     finally:
#         x.close()
#
#
# # deletes data log
# def purge_log(conn, name, type, method, user):
#     x = conn.cursor()
#     try:
#         x.execute(
#             "DELETE FROM `Logs` WHERE username = %s AND `type` = %s AND `method` = %s AND `name` = %s",
#             (user, type, method, name),
#         )
#         conn.commit()
#     except:
#         conn.rollback()
#     finally:
#         x.close()
#
#
# # Pre process a cropped image of the face for the feature extractor model.
def pre_process_img(img, size):
    return cv2.resize(img, dsize=(size, size), interpolation=cv2.INTER_LINEAR)


#
#
# # adds some `padding` to bbox
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


#
#
def crop_img(img: np.array, face_coords: FaceCoordinates, padding: int):
    x, y, w, h = add_coord_padding(
        img,
        padding,
        face_coords["x"],
        face_coords["y"],
        face_coords["width"],
        face_coords["height"],
    )

    # img = np.array(img)
    img = img[:, y : y + h, x : x + w]
    img = np.moveaxis(img, 0, -1)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    return img


#
#
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

    # ############
    # # rotation #
    # ############
    # if np.random.randint(3) == 0:  # rotate 1/3 times
    #     img = scipy.misc.imrotate(img, angle, "bicubic")

    return img


#
#
class Team:
    @classmethod
    def get(cls, conn, **search):
        # TODO cache
        WHERE, val = cls._get_where(search)
        x = conn.cursor(MySQLdb.cursors.DictCursor)
        try:
            x.execute("SELECT * FROM Accounts WHERE {}".format(WHERE), (val,))
            return x.fetchall()[0]
        except IndexError:
            return None

    @classmethod
    def _get_where(cls, search):
        """
        :param search dict:
        :return tuple: WHERE string, value of where
        """
        if len(search) > 1:
            raise Exception("You can only have one WHERE clause")
        column = list(search.keys())[0]
        return "{}=%s".format(column), search[column]

    @classmethod
    def valid_credentials(cls, conn, hashed_username, credentials, key):
        x = conn.cursor()
        try:
            x.execute(
                """
            SELECT `credentials`
            FROM Accounts
            WHERE `username` = %s
            """,
                (hashed_username,),
            )
            encrypted_credentials = x.fetchall()[0][0]

            return AESCipher(key).decrypt(encrypted_credentials) == credentials
        except Exception as e:
            logger.critical(f"Couldn't fetch credentials {e}")
            return False

    @classmethod
    def allowed_to_upload(cls, conn, hashed_username):
        t = time.time()
        x = conn.cursor()
        try:
            x.execute(
                """
            SELECT `last_upload`, `upload_retry_limit`
            FROM Accounts
            WHERE `username` = %s
            """,
                (hashed_username,),
            )

            result = x.fetchall()[0]
            if result[0]:
                last_upload = float(result[0]) or 0
                upload_retry_limit = float(result[1])

                if t - last_upload < upload_retry_limit:
                    return False
        except Exception as e:
            logging.error(f"allowed_to_predict {e}")
            return False

        # insert new last_upload time
        try:
            x.execute(
                """
            UPDATE `Accounts`
            SET last_upload = %s
            WHERE username = %s""",
                (str(t), hashed_username),
            )
            conn.commit()
            return True
        except MySQLdb.Error as e:
            logging.error(f"Couldn't add last_upload: {e}")
            conn.rollback()
            return False

    @classmethod
    def get_num_trained_last_hr(cls, conn, hashed_username):
        x = conn.cursor()
        try:
            x.execute(
                """
            SELECT count(id)
            FROM Features
            WHERE username = %s
            AND type = 'MODEL'
            AND create_dttm > DATE_SUB(NOW(), INTERVAL 1 HOUR)""",
                (hashed_username,),
            )
            return x.fetchall()[0][0]
        except Exception as e:
            logging.error(f"get_num_trained_last_hr {e}")
            return False

    @classmethod
    def increase_num_classifications(cls, conn, hashed_username):
        x = conn.cursor()
        try:
            x.execute(
                """
            UPDATE Accounts
            SET num_classifications = num_classifications + 1
            WHERE username = %s
            """,
                (hashed_username,),
            )
            conn.commit()
            return True
        except MySQLdb.Error as e:
            logger.critical(f"Couldn't increment num_classifications: {e}")
            conn.rollback()
            return False

    @classmethod
    def toggle_storage(cls, conn, hashed_username):
        x = conn.cursor()
        try:
            x.execute(
                """
            UPDATE Accounts
            SET allow_storage = 1 - allow_storage
            WHERE username = %s""",
                (hashed_username,),
            )
            conn.commit()
            return True
        except MySQLdb.Error as e:
            logger.critical(f"Couldn't toggle_storage: {e}")
            conn.rollback()
            return False

    @classmethod
    def num_users(cls, conn, username):
        x = conn.cursor()
        try:
            x.execute(
                "SELECT COUNT(DISTINCT class) from `Features` where username = %s;",
                (username,),
            )
            return x.fetchall()[0][0]
        except IndexError:
            return None

    @classmethod
    def num_stored_images(cls, hashed_username, stored_images_dir):
        return sum(
            [
                len(files)
                for r, d, files in os.walk(stored_images_dir + hashed_username + "/")
            ]
        )

    @classmethod
    def get_stored_images(cls, hashed_username, stored_images_dir):
        """
        :param hashed_username:
        :param stored_images_dir:
        :return: base64 encoded images for html rendering
        """
        images = []
        dir = stored_images_dir + hashed_username + "/"
        for r, d, f in os.walk(dir):
            for file in f:
                image_path = dir + file
                with open(image_path, "rb") as image_file:
                    encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
                    images.append(encoded_string)
        return images

    @classmethod
    def delete_stored_images(cls, hashed_username, stored_images_dir):
        """
        Delete directory containing stored recognition-worker images of team members
        """
        shutil.rmtree(stored_images_dir + "/" + hashed_username)

    @classmethod
    def delete_rows(cls, conn, hashed_username):
        """
        Delete all db rows relating to hashed_username
        """
        x = conn.cursor()

        # delete logs
        try:
            x.execute(
                """
            DELETE from `Logs`
            WHERE username = %s""",
                (hashed_username,),
            )
            conn.commit()
        except MySQLdb.Error as e:
            logger.critical(f"Couldn't delete users logs: {e}")
            return False

        # delete features
        try:
            x.execute(
                """
            DELETE from `Features`
            WHERE username = %s""",
                (hashed_username,),
            )
            conn.commit()
        except MySQLdb.Error as e:
            logger.critical(f"Couldn't delete users features: {e}")
            return False

        # delete account
        try:
            x.execute(
                """
            DELETE from `Accounts`
            WHERE username = %s""",
                (hashed_username,),
            )
            conn.commit()
        except MySQLdb.Error as e:
            logger.critical(f"Couldn't delete user account: {e}")
            return False

        return True

    class PasswordReset:
        @classmethod
        def reset(cls, conn, email, email_config, token_key, root):
            token = Token.generate(email, token_key)
            cls._store_reset_token(conn, token, email)
            email_html = Email.template(root, "reset.html", email=email, token=token)
            Email.send(email_config, email, "Reset ID My Team password", email_html)
            return token

        @classmethod
        def validate(cls, conn, email, token, token_key):
            try:
                valid_token = Token.validate(token, email, token_key)
            except Exception as e:
                logging.error(e)
                return False

            if valid_token:
                x = conn.cursor()
                x.execute(
                    """
                    UPDATE `Accounts`
                    SET password_reset_token = NULL
                    WHERE email = %s""",
                    (email,),
                )
                conn.commit()
                x.close()
                return True
            return False

        @classmethod
        def _store_reset_token(cls, conn, email, token):
            x = conn.cursor()
            x.execute(
                """
            UPDATE `Accounts`
            SET password_reset_token = %s
            WHERE email = %s""",
                (token, email),
            )
            conn.commit()
            x.close()

    class ConfirmEmail:
        @classmethod
        def send_confirmation(
            cls, conn, email, username, email_config, root, token_key
        ):
            team = Team.get(conn, username=hash(username))
            if team and not team["confirmed_email"]:
                token = Token.generate(email, token_key)
                cls._store_confirmation_token(conn, email, token)

                # generate email content
                email_html = Email.template(
                    root, "confirm.html", email=email, token=token, username=username
                )
                Email.send(
                    email_config, email, "Confirm your ID My Team email", email_html
                )
                return token
            else:
                return False

        @classmethod
        def confirm(cls, conn, email, token, token_key):
            try:
                valid_token = Token.validate(token, email, token_key)
            except Exception as e:
                logging.error(e)
                return False

            if valid_token:
                x = conn.cursor()
                x.execute(
                    """
                    UPDATE `Accounts`
                    SET confirmed_email = NOW(), email_confirm_token = NULL
                    WHERE email = %s""",
                    (email,),
                )
                conn.commit()
                x.close()
                return True
            return False

        @classmethod
        def _store_confirmation_token(cls, conn, email, token):
            x = conn.cursor()
            x.execute(
                """
            UPDATE `Accounts`
            SET email_confirm_token = %s
            WHERE email = %s""",
                (token, email),
            )
            conn.commit()
            x.close()


#
#


#
#
# def random_str(length):
#     return "".join(
#         random.choice(string.ascii_letters + string.digits) for _ in range(length)
#     )
#
#
# class AESCipher:
#     def __init__(self, key, byte_size=32):
#         self.key = base64.b64decode(key)
#         self.bs = byte_size
#
#     def encrypt(self, raw):
#         raw = self._pad(raw)
#         iv = Random.new().read(AES.block_size)
#         cipher = AES.new(self.key, AES.MODE_CBC, iv)
#         return base64.b64encode(iv + cipher.encrypt(raw))
#
#     def decrypt(self, enc):
#         enc = base64.b64decode(enc)
#         iv = enc[:16]
#         cipher = AES.new(self.key, AES.MODE_CBC, iv)
#         decrypted = self._unpad(cipher.decrypt(enc[16:])).decode("utf8")
#         self._mock_me(decrypted)
#         return decrypted
#
#     def _pad(self, s):
#         return bytes(
#             s + (self.bs - len(s) % self.bs) * chr(self.bs - len(s) % self.bs), "utf-8"
#         )
#
#     def _unpad(self, s):
#         return s[0 : -ord(s[-1:])]
#
#     def _mock_me(self, val):
#         """
#         Used in pytest to gather the decrypted value
#         TODO surely there is a better way to do this?!
#         :param val:
#         :return:
#         """
#         return val
#
#
# def hash_pw(s):
#     return bcrypt.hashpw(str.encode(s), bcrypt.gensalt()).decode("utf-8")
#
#
# def check_pw_hash(s, h):
#     """
#     :param s: string to compare with a hash
#     :param h: a hash
#     :return: matching
#     """
#     return str.encode(h) == bcrypt.hashpw(str.encode(s), str.encode(h))
#
#
def hash(s):
    return hashlib.sha256(str.encode(s)).hexdigest()


#
#
def compress_string(s):
    string = s.replace(" ", "")
    string = zlib.compress(str.encode(string))
    string = base64.encodebytes(string)
    return string


#
#
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


#
#
# def is_valid_ip(ip):
#     try:
#         socket.inet_aton(str(ip))  # legal
#         return True
#     except socket.error:  # Not legal
#         return False
#
#
# def bytes_to_kb(bytes):
#     return bytes / 1024
#
#
def json_helper(o):
    if isinstance(o, np.int64):
        return int(o)
    if isinstance(o, bytes):
        return o.decode("utf-8")
    raise TypeError


#
#
# def crop_arr(arr, num):
#     if num <= 0:
#         return {}
#
#     new_arr = {}
#     each, rem = divmod(num, len(arr))
#     for i, key in enumerate(arr):
#         if i < rem:
#             new_arr[key] = arr[key][: each + 1]
#         else:
#             new_arr[key] = arr[key][:each]
#     return new_arr
#
#
# class Token:
#     MAX_AGE = 3600
#
#     @classmethod
#     def generate(cls, obj, token_key):
#         serializer = URLSafeTimedSerializer(token_key)
#         return serializer.dumps(obj)
#
#     @classmethod
#     def validate(cls, token, obj, token_key):
#         serializer = URLSafeTimedSerializer(token_key)
#         return serializer.loads(token, max_age=cls.MAX_AGE) == obj
#
#
# # class Email:
# #     @classmethod
# #     def send(cls, email_config, email, subject, html):
# #         # generate email content
# #         msg = MIMEMultipart("alternative")
# #         msg["From"] = email_config["email"]
# #         msg["To"] = email
# #         msg["Subject"] = subject
# #         msg.attach(html)
# #
# #         # send email
# #         with smtplib.SMTP(
# #             email_config["smtp"], port=email_config["smtp_port"]
# #         ) as smtp_server:
# #             smtp_server.ehlo()
# #             smtp_server.starttls()
# #             smtp_server.ehlo()
# #             smtp_server.login(email_config["email"], email_config["password"])
# #             smtp_server.send_message(msg)
# #
# #     @classmethod
# #     def template(cls, root, file, **kwargs):
# #         loader = template.Loader(root + "/web/")
# #         email_html = (
# #             loader.load("templates/emails/inline/" + file).generate(**kwargs).decode()
# #         )
# #         return MIMEText(email_html, "html")
