from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from idmyteamserver.models import Team
from idmyteamserver.structs import LoadClassifierJob, NoModelWSStruct, HasModelWSStruct
from web.settings import REDIS_HIGH_Q


class ChatConsumer(AsyncWebsocketConsumer):
    team: Team

    async def connect(self):
        self.team = await self._verify_credentials(self.scope["headers"])

        # ask redis to load classifier model for recognition
        REDIS_HIGH_Q.enqueue_call(
            func=".",
            kwargs=LoadClassifierJob(
                team_username=self.team.username,
            ).dict(),
        )

        if Classifier.exists(self.team.username):  # TODO has to be gRPC call
            self.team.send_ws_message(HasModelWSStruct(""))
        else:
            self.team.send_ws_message(NoModelWSStruct(""))

        # store socket channel in team
        await self._save_channel_to_team(self.channel_name)

        await self.accept()

    async def disconnect(self, close_code):
        # remove socket channel
        await self._save_channel_to_team(None)

    async def receive(self, text_data=None, bytes_data=None):
        await self.send(text_data=self.team.username)

    async def chat_message(self, event):
        # message from group
        await self.send(text_data=event["message"])

    @sync_to_async
    def _verify_credentials(self, headers: [(bytes, bytes)]) -> Team:
        """
        Extracts the username and credential header fields and verifys them
        returns Team object if successful
        """
        username, credentials = None, None
        for key, val in headers:
            if key == b"username":
                username = val.decode("utf-8")
            elif key == b"credentials":
                credentials = val

            if username and credentials:
                break

        if not username or not credentials:
            raise Exception("No username or credentials header on connection")

        team = Team.objects.get(username=username)
        if not team or not team.validate_credentials(credentials):
            # TODO prevent brute force
            raise Exception("Invalid credentials")
        return team

    @sync_to_async
    def _save_channel_to_team(self, channel_name):
        self.team.socket_channel = channel_name
        self.team.save()
