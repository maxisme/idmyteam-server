import unittest.mock

import pytest
from asgiref.sync import sync_to_async
from channels.testing import WebsocketCommunicator

from idmyteam.structs import LoadClassifierJob
from idmyteamserver.models import Team
from idmyteamserver.tests import test_views
from ws.consumers import WSConsumer


@pytest.mark.asyncio
class TestWS:
    async def test_connect_with_no_headers(self):
        communicator = WebsocketCommunicator(WSConsumer, "/ws")
        connected, _ = await communicator.connect()
        assert not connected

    @pytest.mark.django_db
    async def test_successful_connect(self, monkeypatch):
        team, _ = await self.create_team()
        communicator = WebsocketCommunicator(
            WSConsumer,
            "/ws",
            headers=[
                (b"username", team.username.encode()),
                (b"credentials", team.credentials.encode()),
                (b"local-ip", b"1.1.1.1"),
            ],
        )

        mock_enqueue_call = unittest.mock.Mock()
        monkeypatch.setattr("rq.Queue.enqueue_call", mock_enqueue_call)

        connected, _ = await communicator.connect()
        assert connected

        # verify enqueue_call was called properly
        mock_enqueue_call.assert_called_once()
        assert (
            mock_enqueue_call.call_args.kwargs["kwargs"]
            == LoadClassifierJob(team_username=team.username).dict()
        )

        # verify ip was stored in user
        team = await self.get_team(team.username)
        assert len(team.local_ip) > 0

        # verify socket channel was stored in user
        assert len(team.socket_channel) > 0

        await communicator.disconnect()

    @sync_to_async
    def create_team(self, **extras):
        return test_views.create_team(**extras)

    @sync_to_async
    def get_team(self, username) -> Team:
        return Team.objects.get(username=username)

    # await communicator.send_to(text_data="hello")
    # response = await communicator.receive_from()
    # assert response == "hello"
    #
    # await communicator.disconnect()
