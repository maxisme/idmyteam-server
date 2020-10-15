import json

from channels.generic.websocket import AsyncWebsocketConsumer


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.team_group = self.scope['url_route']['kwargs']['team']

        # Join room group
        await self.channel_layer.group_add(
            self.team_group,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.team_group,
            self.channel_name
        )

    async def receive(self, text_data=None, bytes_data=None):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']

        # Send message to room group
        await self.channel_layer.group_send(
            self.team_group,
            {
                'type': 'chat_message',
                'message': message
            }
        )

    async def chat_message(self, event):
        # message from group
        message = event['message']

        # forward message from group to client
        await self.send(text_data=json.dumps({
            'message': message
        }))
