import inspect
import json
from enum import Enum
from typing import TypedDict, List, Tuple


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
        DELETED_MODEL = 8

    type = "chat_message"
    _type: Type

    def __init__(self, message=""):
        self.message = json.dumps({"type": self._type, "message": message})


class ErrorWSStruct(WSStruct):
    _type = WSStruct.Type.ERROR


class DeleteImageWSStruct(WSStruct):
    _type = WSStruct.Type.DELETE_IMAGE


class NoModelWSStruct(WSStruct):
    _type = WSStruct.Type.NO_MODEL


class HasModelWSStruct(WSStruct):
    _type = WSStruct.Type.HAS_MODEL


class DeletedModelWSStruct(WSStruct):
    _type = WSStruct.Type.DELETED_MODEL


class InvalidClassificationWSStruct(WSStruct):
    _type = WSStruct.Type.INVALID_CLASSIFICATION


class FaceCoordinates(TypedDict):
    x: int
    y: int
    width: int
    height: int
    score: float
    is_manual: bool


class TrainedWSStruct(WSStruct):
    _type = WSStruct.Type.TRAINED

    def __init__(self, num_trained_classes: List[Tuple[int, int]]):
        super().__init__()
        self.num_trained_classes = num_trained_classes


class ClassificationWSStruct(WSStruct):
    _type = WSStruct.Type.CLASSIFICATION

    def __init__(
        self,
        coordinates: FaceCoordinates,
        member_id: int,
        score: float,
        file_name: str,
    ):
        super().__init__()
        self.coordinates = coordinates
        self.member_id = member_id
        self.score = score
        self.file_name = file_name
