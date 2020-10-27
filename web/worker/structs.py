from enum import Enum

from idmyteam.structs import Struct


class JobStruct(Struct):
    team_username: str
    type: int

    class Type(int, Enum):
        DETECT = 1
        STORE_IMG = 2  # store image to be used for training
        TRAIN = 3  # use all store images to train
        LOAD_CLASSIFIER = 4
        UNLOAD_CLASSIFIER = 5
        DELETE_CLASSIFIER = 6


class TrainJob(JobStruct):
    type = JobStruct.Type.TRAIN

    def __init__(self, team_username: str):
        self.team_username = team_username


class LoadClassifierJob(TrainJob):
    type = JobStruct.Type.LOAD_CLASSIFIER


class UnloadClassifierJob(TrainJob):
    type = JobStruct.Type.UNLOAD_CLASSIFIER


class DeleteClassifierJob(TrainJob):
    type = JobStruct.Type.DELETE_CLASSIFIER


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
