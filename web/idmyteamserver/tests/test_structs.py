import pytest

from idmyteamserver.structs import *


def test_TrainJob_val():
    tj = TrainJob("foo")
    assert tj.dict() == {"team_username": "foo", "type": 3}


def test_missing_enum():
    with pytest.raises(ValueError):
        assert JobStruct.Type("notatype")


def test_train_struct():
    ts = TrainedWSStruct("gi")
    assert ts.dict() == {
        "message": '{"type": 2, "message": "gi"}',
        "type": "chat_message",
    }
