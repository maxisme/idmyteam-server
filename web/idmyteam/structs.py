import inspect
import json
from enum import Enum


class Struct:
    def dict(self) -> dict:
        values = {}
        for i, v in inspect.getmembers(self):
            if (
                not inspect.ismethod(v)
                and not inspect.isclass(v)
                and not i.startswith("_")
            ):
                values[i] = self.__getattribute__(i)
        return values


class WSStruct(Struct):
    class Type(int, Enum):
        ERROR = 1
        TRAINED = 2
        DELETE_IMAGE = 3
        CLASSIFICATION = 4
        INVALID_CLASSIFICATION = 5
        NO_MODEL = 6
        HAS_MODEL = 7

    type = "chat_message"
    _type: Type

    def __init__(self, message=""):
        self.message = json.dumps({"type": self._type, "message": message})


class ErrorWSStruct(WSStruct):
    _type = WSStruct.Type.ERROR


class TrainedWSStruct(WSStruct):
    _type = WSStruct.Type.TRAINED


class DeleteImageWSStruct(WSStruct):
    _type = WSStruct.Type.DELETE_IMAGE


class NoModelWSStruct(WSStruct):
    _type = WSStruct.Type.NO_MODEL


class HasModelWSStruct(WSStruct):
    _type = WSStruct.Type.HAS_MODEL


class InvalidClassificationWSStruct(WSStruct):
    _type = WSStruct.Type.INVALID_CLASSIFICATION


class ClassificationWSStruct(WSStruct):
    _type = WSStruct.Type.CLASSIFICATION

    def __init__(
        self, coords: dict, member_id: int, recognition_score: float, file_name: str
    ):
        super().__init__(
            json.dumps(
                {
                    "coords": json.dumps(coords),
                    "member_id": member_id,
                    "recognition_score": recognition_score,
                    "file_name": file_name,
                }
            )
        )
