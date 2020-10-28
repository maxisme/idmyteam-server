import unittest.mock

import pytest
from asgiref.sync import sync_to_async
from channels.testing import WebsocketCommunicator

from idmyteam.idmyteam.structs import (
    NoModelWSStruct,
    HasModelWSStruct,
    WSStruct,
    ErrorWSStruct,
)
from worker.structs import LoadClassifierJob, UnloadClassifierJob
from idmyteamserver.models import Team
from idmyteamserver.tests import test_views
from ws.consumers import WSConsumer


@pytest.mark.asyncio
@pytest.mark.django_db
class TestWS:
    async def test_connect_with_no_headers(self):
        communicator = WebsocketCommunicator(WSConsumer, "/ws")
        connected, _ = await communicator.connect()
        assert not connected
        await communicator.disconnect()

    @pytest.mark.parametrize("with_model", [True, False])
    async def test_successful_connect(self, monkeypatch, with_model):
        extras = {}
        if with_model:
            extras = {"classifier_model_path": "/path/to/none/existent/model"}

        communicator, team = await self._init_team_communicator(**extras)

        # create enqueue_call mock
        mock_enqueue_call = unittest.mock.Mock()
        monkeypatch.setattr("rq.Queue.enqueue_call", mock_enqueue_call)

        connected, _ = await communicator.connect()
        assert connected

        # verify enqueue_call was called to LoadClassifierJob on connect
        mock_enqueue_call.assert_called_once()
        assert (
            mock_enqueue_call.call_args.kwargs["kwargs"]
            == LoadClassifierJob(team_username=team).dict()
        )

        # verify ip was stored in user
        team = await self._get_team(team)
        assert len(team.local_ip) > 0

        # verify socket channel was stored in user
        assert len(team.socket_channel) > 0

        # verify immediate response message with status of model
        incoming_msg = await communicator.receive_from()
        if with_model:
            assert incoming_msg == HasModelWSStruct().dict()["message"]
        else:
            assert incoming_msg == NoModelWSStruct().dict()["message"]

        await communicator.disconnect()

    async def test_successful_disconnect(self, monkeypatch):
        communicator, team = await self._init_team_communicator()
        connected, _ = await communicator.connect()
        assert connected

        # create enqueue_call mock
        mock_enqueue_call = unittest.mock.Mock()
        monkeypatch.setattr("rq.Queue.enqueue_call", mock_enqueue_call)

        await communicator.disconnect()

        # verify enqueue_call was called to UnloadClassifierJob on disconnect
        assert (
            mock_enqueue_call.call_args.kwargs["kwargs"]
            == UnloadClassifierJob(team_username=team).dict()
        )

        # verify ip was removed from team
        team = await self._get_team(team)
        assert not team.local_ip

        # verify socket channel was removed from team
        assert not team.socket_channel

    async def test_team_send_ws_message(self):
        communicator, t = await self._init_team_communicator()
        connected, _ = await communicator.connect()
        _ = await communicator.receive_from()  # ignore first message on connection

        # send message via Team
        test_msg = ErrorWSStruct("test")
        await self._send_team_ws_message(t.username, test_msg)

        msg = await communicator.receive_from()
        assert msg == test_msg.dict()["message"]

    async def test_team_send_unconnected_ws_message(self):
        _, t = await self._init_team_communicator()

        # send message via Team
        test_msg = ErrorWSStruct("test")
        assert not await self._send_team_ws_message(t.username, test_msg)

    async def _init_team_communicator(self, **extras):
        team, _ = await self._create_team(**extras)
        return (
            WebsocketCommunicator(
                WSConsumer,
                "/ws",
                headers=[
                    (b"username", team.username.encode()),
                    (b"credentials", team.credentials.encode()),
                    (b"local-ip", b"1.1.1.1"),
                ],
            ),
            team,
        )

    @sync_to_async
    def _create_team(self, **extras):
        return test_views.create_test_team(**extras)

    @sync_to_async
    def _get_team(self, username) -> Team:
        return Team.objects.get(username=username)

    @sync_to_async
    def _send_team_ws_message(self, username, message: WSStruct) -> bool:
        return Team.objects.get(username=username).send_ws_message(message)
