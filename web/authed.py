import io
import json
import os
import urllib.request, urllib.parse, urllib.error
from collections import defaultdict

from rq import Queue

import tornado.websocket

import logging
import zipfile

from redis import Redis
from settings import functions, config
from view import BaseHandler
import forms
from ML.classifier import Classifier

clients = {}
redis_conn = Redis()

high_q = Queue('high', connection=redis_conn, default_timeout=60)
med_q = Queue('medium', connection=redis_conn, default_timeout=60)
low_q = Queue('low', connection=redis_conn, default_timeout=600)

logging.basicConfig(level='INFO')

class ProfileHandler(BaseHandler):
    def get(self):
        self.tmpl['title'] = 'Profile'
        username = self.tmpl['username']
        if username:
            hashed_username = functions.hash(username)
            conn = functions.connect(config.DB["username"], config.DB["password"], config.DB["db"])
            self.tmpl['team'] = functions.Team.get(conn, hashed_username)
            if self.tmpl['team']:
                self.tmpl['num_members'] = functions.Team.num_users(conn, hashed_username)
                self.tmpl['local_ip'] = clients[hashed_username].local_ip if hashed_username in clients else False
                self.tmpl['has_model'] = Classifier.exists(hashed_username)
                self.tmpl['root_password'] = 'zFHbmDM59nQIt5w6eYbWL2KsHHWdk4PQ9laRHZ5b'
                self.tmpl['credentials'] = functions.decrypt(self.tmpl['team']['credentials'], config.CRYPTO_KEY)
                self.tmpl['xsrf_token'] = self.xsrf_token
                return self.render('profile.html', **self.tmpl)
            else:
                self.clear_cookie('username')
        return self.redirect("/login")


class LoginHandler(BaseHandler):
    def __init__(self, *args, **kwargs):
        super(LoginHandler, self).__init__(*args, **kwargs)
        self.tmpl['failed_captcha'] = False

    def get(self):
        self.tmpl['form'] = forms.LoginForm()
        self._screen()

    def post(self):
        self.tmpl['form'] = form = forms.LoginForm(self.request.arguments)
        if self._is_valid_captcha(self.request.arguments):
            if form.validate():
                conn = functions.connect(config.DB["username"], config.DB["password"], config.DB["db"])
                user = functions.Team.get(conn, functions.hash(form.username.data))
                if functions.check_pw_hash(form.password.data, user['password']):
                    if user['confirmed_email']:
                        self.set_secure_cookie('username', form.username.data)
                        return self.redirect('/profile')
                    else:
                        self.tmpl['error_message'] = """You have not confirmed your email! 
                        <a href='/resend?email={}'>
                            Resend confirmation?
                        </a>""".format(user['email'])
                else:
                    self.tmpl['error_message'] = "Invalid credentials! Please try again."
        else:
            self.tmpl['failed_captcha'] = True
        return self._screen()

    def _screen(self):
        self.tmpl['title'] = 'Login'
        self.render('helpers/form.html', **self.tmpl)

    def _is_valid_captcha(self, args):
        # return True
        if 'g-recaptcha-response' in args:
            recaptcha_response = args['g-recaptcha-response'][0].decode('utf-8')
            url = 'https://www.google.com/recaptcha/api/siteverify'
            values = {
                'secret': config.RECAPTCHA_KEY,
                'response': recaptcha_response,
                'remoteip': self.request.remote_ip
            }
            data = urllib.parse.urlencode(values).encode('utf-8')
            req = urllib.request.Request(url, data)
            response = urllib.request.urlopen(req)
            return json.load(response)['success']
        return False


class SignUpHandler(LoginHandler):
    def get(self):
        self.tmpl['form'] = forms.SignUpForm()
        self._screen()

    def post(self):
        self.tmpl['form'] = form = forms.SignUpForm(self.request.arguments)
        if self._is_valid_captcha(self.request.arguments):
            if form.validate():
                conn = functions.connect(config.DB["username"], config.DB["password"], config.DB["db"])
                if functions.Team.sign_up(conn, form.username.data, form.password.data,
                                          form.email.data, form.store.data, config.CRYPTO_KEY):
                    functions.Team.send_confirmation_email(conn, form.email.data, config.EMAIL_CONFIG)
                else:
                    self.tmpl['error_message'] = 'Error with user information! ' \
                                                 'Please try a different username and/or email.'
        else:
            self.tmpl['failed_captcha'] = True

        return self._screen()

    def _screen(self):
        self.tmpl['title'] = 'Sign Up'
        self.render('helpers/form.html', **self.tmpl)


class ImageUploadHandler(BaseHandler):
    def post(self):
        try:
            username = self.request.arguments['username'][0].decode()
            credentials = self.request.arguments['credentials'][0].decode()
        except Exception as e:
            logging.error(e)
            return self.write_error(404)

        content_len = functions.bytes_to_kb(int(self.request.headers['Content-Length']))
        if content_len > config.MAX_TRAIN_UPLOAD_SIZE_KB:
            return self.write("Upload file too large")

        conn = functions.connect(config.DB["username"], config.DB["password"], config.DB["db"])
        if functions.Team.valid_credentials(conn, username, credentials, config.CRYPTO_KEY):
            hashed_username = functions.hash(username)
            if hashed_username in clients:
                if functions.Team.allowed_to_upload(conn, hashed_username):
                    if 'img_file' in self.request.files:
                        #####################
                        # PREDICTING upload #
                        #####################
                        if content_len <= config.MAX_IMG_UPLOAD_SIZE_KB:
                            if Classifier.get_model_path(hashed_username):
                                # There is a classifier for username
                                try:
                                    store_features = bool(self.request.arguments['store-features'][0])
                                except:
                                    return self.return_error('No features')

                                upload = self.request.files['img_file'][0]
                                img = upload['body']
                                file_name = self.request.arguments['file-name'][0]

                                med_q.enqueue_call(func='.', kwargs={
                                    'type': 'detect',
                                    'img': img,
                                    'file_name': file_name,
                                    'hashed_username': hashed_username,
                                    'store_image_features': store_features,
                                })
                            else:
                                logging.error("Prediction request before trained model! %s", hashed_username)
                                return self.return_error("The team needs to train before you can predict.")
                        else:
                            logging.warning('Image upload size too big (%sKB) from ip (%s)',
                                            (content_len, self.request.headers['X-Real-Ip']))
                            return self.return_error("Image upload size too large.")
                    elif 'ZIP' in self.request.files:
                        ###################
                        # TRAINING upload #
                        ###################
                        num_trained = functions.Team.get_num_trained_last_hr(conn, hashed_username)

                        user = functions.Team.get(conn, hashed_username)
                        max_train_imgs_per_hr = user['max_train_imgs_per_hr']

                        z = zipfile.ZipFile(io.BytesIO(self.request.files['ZIP'][0]['body']))
                        if z:
                            imgs_to_upload = defaultdict(list)
                            for file in z.infolist():
                                if file.file_size > 0:
                                    if file.file_size / 1024 > config.MAX_IMG_UPLOAD_SIZE_KB:
                                        return self.return_error(
                                            "Training image {} file is too large!".format(file.filename))

                                    try:
                                        member = int(os.path.dirname(file.filename))
                                    except:
                                        logging.error("Invalid file uploaded")
                                        continue

                                    imgs_to_upload[member].append(file)

                            train_quota = max_train_imgs_per_hr - num_trained

                            imgs_to_upload = functions.crop_arr(imgs_to_upload, train_quota)

                            if not imgs_to_upload:
                                return self.return_error("You have uploaded too many training images. Please try again later...")
                            elif len(imgs_to_upload) < 2 and not Classifier.exists(hashed_username):
                                return self.return_error("You must train with at least 2 team members.")

                            for member in imgs_to_upload:
                                for file in imgs_to_upload[member]:
                                    img = z.read(file)
                                    low_q.enqueue_call(func='.', kwargs={
                                        'type': 'detect',
                                        'img': img,
                                        'file_name': file.filename,
                                        'hashed_username': hashed_username,
                                        'member_id': member,
                                        'store_image': bool(user['allow_storage'])
                                    })

                            # tell model to train
                            low_q.enqueue_call(func='.', kwargs={
                                'type': 'train',
                                'hashed_username': hashed_username,
                            })

                        else:
                            return self.return_error("Invalid ZIP")
                    self.write('Uploaded')
            else:
                return self.return_error("Not connected to socket")

    # OVERIDE XSRF CHECK
    def check_xsrf_cookie(self):
        pass

    def return_error(self, message):
        if not isinstance(message, dict):
            message = {
                'message': message
            }
        message = json.dumps(message)
        return self.set_status(400, message)


class WebSocketHandler(tornado.websocket.WebSocketHandler):
    hashed_username = None

    def check_origin(self, origin):
        if origin == 'wss://idmy.team':
            return True

    def open(self):
        try:
            headers = self.request.headers
            credentials = headers['credentials']
            local_ip = headers['local-ip']
            username = headers['username']
        except Exception as e:
            logging.warning('Invalid request %s', e)
            return self.close(1003, 'Invalid request')

        if not functions.is_valid_ip(local_ip):
            return self.close(1003, 'Invalid local IP')

        self.hashed_username = functions.hash(username)
        if self.hashed_username not in clients:
            conn = functions.connect(config.DB["username"], config.DB["password"], config.DB["db"])
            if functions.Team.valid_credentials(conn, username, credentials, config.CRYPTO_KEY):
                # add classifier to worker
                high_q.enqueue_call(func='.', kwargs={
                    'type': 'add',
                    'hashed_username': self.hashed_username
                })

                if not Classifier.exists(self.hashed_username):
                    self.write_message(json.dumps({
                        'type': 'no_model'
                    }))

                self.local_ip = local_ip
                clients[self.hashed_username] = self
                logging.info('%s connected to socket', self.hashed_username)

                # send all pending messages to client
                if self.hashed_username in pending_messages:
                    for message in pending_messages[self.hashed_username]:
                        self.write_message(message)
            else:
                self.write_message(json.dumps({
                    'type': 'invalid_credentials'
                }))
                return self.close(1003, 'Invalid request')
        else:
            logging.warning('%s already connected wss - %s', self.hashed_username, self.request.headers['X-Real-Ip'])
            return self.close(1003, 'Invalid request')

    def on_close(self):
        if self.hashed_username and self.hashed_username in clients:
            clients.pop(self.hashed_username)

            # remove classifier from worker
            high_q.enqueue_call(func='.', kwargs={
                'type': 'remove',
                'hashed_username': self.hashed_username
            })
            logging.info('%s disconnected from socket', self.hashed_username)

    def on_message(self, message):
        """
        :param message: integer value representing the pending message id
        :return:
        """
        try:
            message = int(message)
        except:
            self.close(1004, 'Invalid Message')

        # incoming messages contain an id to confirm received
        if self.hashed_username in pending_messages:
            for m in pending_messages[self.hashed_username]:
                if json.loads(m)['id'] == message:
                   return pending_messages[self.hashed_username].remove(m)
        self.close(1004, 'Invalid Message')

    def close(self, code=None, reason=None):
        logging.warning('Close socket reason: %s', reason)
        self.write_message(reason)
        super(WebSocketHandler, self).close(code, reason)


class LocalWebSocketHandler(tornado.websocket.WebSocketHandler):

    def check_origin(self, origin):
        if origin == config.LOCAL_SOCKET_URL.replace('ws', 'http'):
            return True

    def on_message(self, message):
        """
        Only comes from classifier with classification response
        :param message:
        :return:
        """
        send_local_message(message)


pending_messages = defaultdict(list)  # TODO monitor size of this variable
def send_local_message(message):
    try:
        message = json.loads(message)
    except:
        logging.error('Invalid local message sent %s', message)
        return False

    hashed_username = message.pop("hashed_username")
    if hashed_username in clients:
        arr = pending_messages[hashed_username]
        arr.append(json.dumps({
            "id": len(arr),
            "message": message
        }))

        # client connected
        ws = clients[hashed_username]  # type: WebSocketHandler
        ws.write_message(pending_messages[hashed_username][-1])
