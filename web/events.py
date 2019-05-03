import json
import logging
import view, authed
from settings import functions, config
from ML.classifier import Classifier


class LogoutHandler(view.BaseHandler):
    def get(self):
        self.clear_all_cookies()
        self.redirect('/')


class AllowUploadStorageHandler(view.BaseHandler):
    def post(self):
        username = self.tmpl['username']
        if username:
            hashed_username = functions.hash(username)
            conn = functions.connect(config.DB["username"], config.DB["password"], config.DB["db"])
            if not functions.Team.toggle_storage(conn, hashed_username):
                logging.error("unable to toggle storage for %s", hashed_username)
                return self.write_error(501)


class DeleteAccountHandler(view.BaseHandler):
    def post(self):
        username = self.tmpl['username']
        hashed_username = functions.hash(username)
        if username:
            conn = functions.connect(config.DB["username"], config.DB["password"], config.DB["db"])
            if Classifier.delete(hashed_username):
                send_delete_model(hashed_username)
            functions.Team.delete(conn, hashed_username)
            self.clear_all_cookies()


class DeleteModelHandler(view.BaseHandler):
    def post(self):
        username = self.tmpl['username']
        if username:
            hashed_username = functions.hash(username)
            if Classifier.delete(hashed_username):
                send_delete_model(hashed_username)
            else:
                logging.error("unable to delete model for %s", hashed_username)
                return self.write_error(501)


def send_delete_model(hashed_username):
    """
    Send message to client telling them to delete model
    :param hashed_username: client
    :return:
    """
    authed.send_local_message(json.dumps({
        'hashed_username': hashed_username,
        'delete-model': True
    }))


class ConfirmEmail(view.BaseHandler):
    def get(self):
        email = self.get_argument('email', None)
        token = self.get_argument('token', None)
        username = self.get_argument('username', None)

        conn = functions.connect(config.DB["username"], config.DB["password"], config.DB["db"])
        email_to_username = functions.Team.email_to_username(conn, email)
        hashed_username = functions.hash(username)
        if email_to_username == hashed_username:
            if not functions.Team.ConfirmEmail.has_confirmed(conn, email):
                if functions.Team.ConfirmEmail.validate_token(conn, email, token, config.EMAIL_CONFIG['key']):
                    self.set_secure_cookie('username', username)
                    self.flash_success('Congratulations! Your email has been confirmed.', '/profile')
        return self.flash_error('Invalid token', '/')



class ResendConfirmationEmail(view.BaseHandler):
    def get(self):
        try:
            email = self.request.arguments['email'][0].decode()
        except Exception as e:
            logging.error(e)
            return self.redirect('/')

        # check if there is an email and also that it hasn't already been confirmed
        conn = functions.connect(config.DB["username"], config.DB["password"], config.DB["db"])
        if not functions.Team.ConfirmEmail.send_confirmation(conn, email, config.EMAIL_CONFIG):
            return self.flash_error('Problem sending confirmation email.', '/')

        self.redirect('/')
