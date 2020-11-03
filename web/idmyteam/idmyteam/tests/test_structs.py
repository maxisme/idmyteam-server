import pytest

from idmyteam.idmyteam.structs import *


def test_TrainJob_val():
    tj = ErrorWSStruct("foo")
    assert tj.dict() == {
        "message": '{"type": 1, "message": "foo"}',
        "type": "chat_message",
    }


def test_missing_enum():
    with pytest.raises(ValueError):
        assert ErrorWSStruct.Type("notatype")


def test_ws_struct():
    ts = DeletedModelWSStruct("gi")
    assert ts.dict() == {
        "message": '{"type": 8, "message": "gi"}',
        "type": "chat_message",
    }
