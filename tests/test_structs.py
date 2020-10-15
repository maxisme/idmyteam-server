from idmyteamserver.structs import *


def test_TrainJob_val():
    tj = TrainJob("foo")
    assert tj.val() == {"team_username": "foo", "type": 3}


def test_missing_enum():
    assert JobStruct.Type("foo") == 12
