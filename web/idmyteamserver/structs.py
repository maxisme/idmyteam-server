import inspect
from enum import Enum


class Struct:
    def val(self):
        values = {}
        for i, v in inspect.getmembers(self):
            if not inspect.ismethod(v) and not inspect.isclass(v) and "__" not in i:
                values[i] = self.__getattribute__(i)
        return values


class JobStruct(Struct):
    team_username: str
    type: int

    class JobType(int, Enum):
        DETECT = 1
        STORE_IMG = 2  # store image to be used for training
        TRAIN = 3  # use all store images to train
        LOAD_CLASSIFIER = 4
        UNLOAD_CLASSIFIER = 5


class TrainJob(JobStruct):
    type = JobStruct.JobType.TRAIN

    def __init__(self, team_username: str):
        self.team_username = team_username


class LoadClassifierJob(TrainJob):
    type = JobStruct.JobType.LOAD_CLASSIFIER


class UnloadClassifierJob(TrainJob):
    type = JobStruct.JobType.UNLOAD_CLASSIFIER


class DetectJob(JobStruct):
    type = JobStruct.JobType.DETECT

    def __init__(
            self, team_username: str, img: bytes, file_name: str, store_image_features: bool
    ):
        self.team_username = team_username
        self.img = img
        self.file_name = file_name
        self.store_image_features = store_image_features  # whether to store image features for online ML training


class StoreImageJob(JobStruct):
    type = JobStruct.JobType.STORE_IMG

    def __init__(self, team_username: str, img: bytes, file_name: str, member_id: int):
        self.team_username = team_username
        self.img = img
        self.file_name = file_name
        self.member_id = member_id
