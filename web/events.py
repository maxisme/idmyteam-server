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
            if not functions.Team.toggle_storage(self.conn, hashed_username):
                logging.error("unable to toggle storage for %s", hashed_username)
                return self.write_error(501)


class DeleteAccountHandler(view.BaseHandler):
    def post(self):
        username = self.tmpl['username']
        hashed_username = functions.hash(username)
        if username:
            if Classifier.delete(hashed_username):
                send_delete_model(hashed_username)
            functions.Team.delete(self.conn, hashed_username)
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
        email = self.get_argument('email', '')
        token = self.get_argument('token', '')
        username = self.get_argument('username', '')

        email_to_username = functions.Team.email_to_username(self.conn, email)
        hashed_username = functions.hash(username)
        if email_to_username == hashed_username:
            if functions.Team.ConfirmEmail.can_confirm(self.conn, email):
                if functions.Team.ConfirmEmail.validate_token(self.conn, email, token, config.EMAIL_CONFIG['key']):
                    self.set_secure_cookie('username', username)
                    return self.flash_success('Congratulations! Your email has been confirmed.', '/profile')
        return self.flash_error('Invalid token', '/')


class ResendConfirmationEmail(view.BaseHandler):
    CONFIRMATION_ERROR = 'Problem sending confirmation email.'

    def get(self):
        email = self.get_argument('email', '')
        username = self.get_argument('username', '')

        # check if there is an email and also that it hasn't already been confirmed
        if not functions.Team.ConfirmEmail.send_confirmation(self.conn, email, username,
                                                             config.EMAIL_CONFIG, config.ROOT):
            return self.flash_error(self.CONFIRMATION_ERROR, '/')

        self.redirect('/')
