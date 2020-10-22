import logging

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from idmyteam.structs import (
    LoadClassifierJob,
    NoModelWSStruct,
    HasModelWSStruct,
    UnloadClassifierJob,
)
from idmyteamserver.models import Team
from worker.queue import REDIS_HIGH_Q


class WSConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        try:
            self.team = await self._verify_credentials(self.scope["headers"])
        except InvalidCredentials as e:
            logging.warning(e)
            await self.close(1)
            return

        await self.accept()

        # ask redis to load teams classifier ML model into memory for quicker actions
        REDIS_HIGH_Q.enqueue_call(
            func=".", kwargs=LoadClassifierJob(team_username=self.team.username).dict()
        )

        if bool(self.team.classifier_model_path):
            await self.send(HasModelWSStruct().dict()["message"])
        else:
            await self.send(NoModelWSStruct().dict()["message"])

    async def disconnect(self, close_code):
        if hasattr(self, "team"):
            # ask redis to unload teams classifier ML model
            REDIS_HIGH_Q.enqueue_call(
                func=".",
                kwargs=UnloadClassifierJob(team_username=self.team.username).dict(),
            )

            await self._team_socket_disconnect()

    async def receive(self, text_data=None, bytes_data=None):
        await self.send(text_data=self.team.username)

    async def chat_message(self, event):
        # message from group
        await self.send(text_data=event["message"])

    @sync_to_async
    def _verify_credentials(self, headers: [(bytes, bytes)]) -> Team:
        """
        Extracts the username, credential and local ip header fields and verifies them
        Also saves the ip and socket channel in the db
        returns Team object if successful credentials
        """
        username, credentials, ip = None, None, None
        for key, val in headers:
            if key == b"username":
                username = val.decode()
            elif key == b"credentials":
                credentials = val
            elif key == b"local-ip":
                ip = val

            if username and credentials and ip:
                break

        if not username or not credentials or not ip:
            raise InvalidCredentials(
                "No username or credentials or local-ip header on connection"
            )

        team = Team.objects.get(username=username)
        if not team or not team.validate_credentials(credentials.decode()):
            # TODO prevent brute force
            raise InvalidCredentials("Invalid credentials")

        # set client local ip
        team.local_ip = ip.decode()

        # set channel
        team.socket_channel = self.channel_name
        team.save()

        return team

    @sync_to_async
    def _team_socket_disconnect(self):
        self.team.local_ip = None
        self.team.socket_channel = None
        self.team.save()


class InvalidCredentials(BaseException):
    pass
