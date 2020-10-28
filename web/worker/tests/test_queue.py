import unittest.mock
from datetime import datetime

import pytest

from idmyteam.idmyteam.structs import ErrorWSStruct
from idmyteamserver.models import Team
from tests.helpers import create_test_team
from web.settings import REDIS_CONN
from worker.classifier import (
    Classifier,
    NO_TRAINING_DATA_MSG,
    ALREADY_TRAINING_MSG,
)
from worker.queue import MyQueue, REDIS_QS, enqueue
from worker import queue
from worker.structs import TrainJob


@pytest.mark.django_db
def test_no_corresponding_team():
    q = MyQueue(REDIS_QS[0], connection=REDIS_CONN, default_timeout=60, is_async=False)
    with pytest.raises(Team.DoesNotExist):
        enqueue(q, TrainJob("this is not a valid team username"))


@pytest.mark.django_db
class TestTrainTeamJob:
    q = MyQueue(REDIS_QS[0], connection=REDIS_CONN, default_timeout=60, is_async=False)

    def test_no_training_data(self, monkeypatch):
        team, team_dict = create_test_team()
        queue.team_classifiers[team] = Classifier(team)

        mock_send_ws_message = unittest.mock.Mock()
        monkeypatch.setattr(
            "idmyteamserver.models.Team.send_ws_message", mock_send_ws_message
        )

        enqueue(self.q, TrainJob(team))

        mock_send_ws_message.assert_called_once()
        assert (
            mock_send_ws_message.call_args.args[0].dict()
            == ErrorWSStruct(NO_TRAINING_DATA_MSG).dict()
        )

    def test_already_training(self, monkeypatch):
        team, team_dict = create_test_team()
        team.is_training_dttm = datetime.now()  # force mark as training
        queue.team_classifiers[team] = Classifier(team)

        mock_send_ws_message = unittest.mock.Mock()
        monkeypatch.setattr(
            "idmyteamserver.models.Team.send_ws_message", mock_send_ws_message
        )

        enqueue(self.q, TrainJob(team))

        mock_send_ws_message.assert_called_once()
        assert (
            mock_send_ws_message.call_args.args[0].dict()
            == ErrorWSStruct(ALREADY_TRAINING_MSG).dict()
        )
