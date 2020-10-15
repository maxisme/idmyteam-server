import json

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from idmyteamserver.models import Team


class ChatConsumer(AsyncWebsocketConsumer):
    team: Team

    @sync_to_async
    def get_team(self, username: str) -> Team:
        return Team.objects.get(username=username)

    async def connect(self):
        username, credentials = None, None
        for key, val in self.scope["headers"]:
            if key == b"username":
                username = val.decode("utf-8")
            elif key == b"credentials":
                credentials = val

            if username and credentials:
                break

        if not username or not credentials:
            raise Exception("No username or credentials header on connection")

        self.team = await self.get_team(username)
        if not self.team or not self.team.validate_credentials(credentials):
            # TODO prevent brute force
            raise Exception("Invalid credentials")

        print(self.channel_name)
        # Join room group
        await self.channel_layer.group_add(self.team.username, self.channel_name)

        await self.accept()

    async def disconnect(self, close_code):
        self.channel_layer.group_discard(self.team.username, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        # Send message to room group
        print(self.team.username)
        await self.channel_layer.group_send(
            str(self.team.username),
            {
                'type': 'chat_message',
                'message': self.team.username
            }
        )
        await self.send(text_data=self.team.username)

    async def chat_message(self, event):
        # message from group
        message = event["message"]

        # forward message from group to client
        await self.send(text_data=json.dumps({"message": message}))
