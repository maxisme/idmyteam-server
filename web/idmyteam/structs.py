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

    def __init__(self, message: str):
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


class JobStruct(Struct):
    team_username: str
    type: int

    class Type(int, Enum):
        DETECT = 1
        STORE_IMG = 2  # store image to be used for training
        TRAIN = 3  # use all store images to train
        LOAD_CLASSIFIER = 4
        UNLOAD_CLASSIFIER = 5


class TrainJob(JobStruct):
    type = JobStruct.Type.TRAIN

    def __init__(self, team_username: str):
        self.team_username = team_username


class LoadClassifierJob(TrainJob):
    type = JobStruct.Type.LOAD_CLASSIFIER


class UnloadClassifierJob(TrainJob):
    type = JobStruct.Type.UNLOAD_CLASSIFIER


class DetectJob(JobStruct):
    type = JobStruct.Type.DETECT

    def __init__(
        self, team_username: str, img: bytes, file_name: str, store_image_features: bool
    ):
        self.team_username = team_username
        self.img = img
        self.file_name = file_name
        # whether to store image features for online ML training
        self.store_image_features = store_image_features


class StoreImageJob(JobStruct):
    type = JobStruct.Type.STORE_IMG

    def __init__(self, team_username: str, img: bytes, file_name: str, member_id: int):
        self.team_username = team_username
        self.img = img
        self.file_name = file_name
        self.member_id = member_id
