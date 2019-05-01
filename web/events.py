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
        try:
            email = self.request.arguments['email'][0].decode()
            token = self.request.arguments['token'][0].decode()
        except:
            return self.redirect('/')

        conn = functions.connect(config.DB["username"], config.DB["password"], config.DB["db"])
        if functions.Team.confirm_email_token(conn, email, token, config.EMAIL_CONFIG['key']):
            pass
        self.redirect('/')


class ResendConfirmationEmail(view.BaseHandler):
    def get(self):
        try:
            email = self.request.arguments['email'][0].decode()
        except:
            return self.redirect('/')

        # check if there is an email and also that it hasn't already been confirmed
        conn = functions.connect(config.DB["username"], config.DB["password"], config.DB["db"])
        if functions.Team.allowed_confirmation_resend(conn, email):
            functions.Team.send_confirmation_email(conn, email, config.EMAIL_CONFIG)

        self.redirect('/')
