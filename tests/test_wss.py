# emulates connection from web panel
import time

import mock
from tornado.httpclient import HTTPRequest
from tornado.websocket import websocket_connect
from tornado import gen

from test_web import TeamGenerator
from web_helpers import WebTest


class TestSocketClient(object):
    """
    Mimics code from web panel
    """

    def __init__(self, request):
        self.ws = None
        self.request = request
        self.failure = True

    @gen.coroutine
    def connect(self):
        try:
            self.ws = yield websocket_connect(self.request)
        except Exception as e:
            print(e)
        else:
            self.run()

    def close(self):
        self.ws = None

    @gen.coroutine
    def run(self):
        msg = yield self.ws.read_message()
        if msg:
            self.failure = True
            self._asserts(msg)
            self.failure = False

    def _asserts(self, msg):
        raise Exception("Not customised asserts!")


@mock.patch("smtplib.SMTP")
@mock.patch("authed.LoginHandler._is_valid_captcha", return_value=True)
@mock.patch("settings.functions.Email.template")
@mock.patch("settings.functions.AESCipher._mock_me")
class WSSTest(WebTest):
    def test_initial_team_connection(self, _mock_me, template, *args):
        class TestWSS(TestSocketClient):
            def _asserts(self, msg):
                # IMPORTANT
                assert msg == '{"type": "no_model"}'

        # create user
        team = TeamGenerator()
        self.new_team(team, template)
        credentials = self.get_credentials(team, _mock_me)

        # connect to socket
        url = self.get_url("/socket").replace("http", "ws")
        request = HTTPRequest(
            url,
            headers={
                "username": team.username,
                "credentials": credentials,
                "local-ip": team.ip,
            },
        )
        ws = TestWSS(request)
        ws.connect()

        try:
            self.wait(timeout=0.1)
        except:
            assert not ws.failure

    @mock.patch("ML.classifier.Classifier.get_model_path", return_value=True)
    def test_team_with_model_connection(self, _, _mock_me, template, *args):
        class TestWSS(TestSocketClient):
            def _asserts(self, msg):
                # IMPORTANT
                assert msg == '{"type": "connected"}'

        # create user
        team = TeamGenerator()
        self.new_team(team, template)
        credentials = self.get_credentials(team, _mock_me)

        # connect to socket
        url = self.get_url("/socket").replace("http", "ws")
        request = HTTPRequest(
            url,
            headers={
                "username": team.username,
                "credentials": credentials,
                "local-ip": team.ip,
            },
        )
        ws = TestWSS(request)
        ws.connect()

        try:
            self.wait(timeout=0.1)
        except:
            assert not ws.failure

    def test_invalid_team_credentials(self, _mock_me, template, *args):
        class TestWSS(TestSocketClient):
            def _asserts(self, msg):
                # IMPORTANT
                assert msg == '{"type": "invalid_credentials"}'

        team = TeamGenerator()

        # connect to socket
        url = self.get_url("/socket").replace("http", "ws")
        request = HTTPRequest(
            url,
            headers={
                "username": team.username,
                "credentials": "foo",
                "local-ip": team.ip,
            },
        )
        ws = TestWSS(request)
        ws.connect()

        try:
            self.wait(timeout=0.1)
        except:
            assert not ws.failure

    @mock.patch("ML.classifier.Classifier.get_model_path", return_value=True)
    def test_team_with_invalid_ip(self, _, _mock_me, template, *args):
        class TestWSS(TestSocketClient):
            def _asserts(self, msg):
                # IMPORTANT
                assert msg == "Invalid request"

        # create user
        team = TeamGenerator()
        self.new_team(team, template)
        credentials = self.get_credentials(team, _mock_me)

        # connect to socket
        url = self.get_url("/socket").replace("http", "ws")
        request = HTTPRequest(
            url,
            headers={
                "username": team.username,
                "credentials": credentials,
                "local-ip": "foo",
            },
        )
        ws = TestWSS(request)
        ws.connect()

        try:
            self.wait(timeout=0.1)
        except:
            assert not ws.failure

    def test_no_headers(self, _mock_me, *args):
        class TestWSS(TestSocketClient):
            def _asserts(self, msg):
                # IMPORTANT
                assert msg == "Invalid request"

        # connect to socket
        url = self.get_url("/socket").replace("http", "ws")
        request = HTTPRequest(url)
        ws = TestWSS(request)
        ws.connect()

        try:
            self.wait(timeout=0.1)
        except:
            assert not ws.failure
