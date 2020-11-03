import logging
from typing import Dict

from rq import Queue, Worker
from rq.job import Job

from idmyteam.idmyteam.structs import ErrorWSStruct, TrainedWSStruct
from worker.structs import (
    JobStruct,
    DetectJob,
    StoreImageFeaturesJob,
    TrainJob,
    LoadClassifierJob,
    UnloadClassifierJob,
    DeleteClassifierJob,
)
from idmyteamserver.models import Team
from web.settings import REDIS_CONN, TRAIN_Q_TIMEOUT

try:
    from worker.classifier import (
        Classifier,
        AlreadyTrainingException,
        NotEnoughClassesException,
    )
    from worker.detecter import Detecter

    team_classifiers: Dict[str, Classifier] = {}
    detecter: Detecter
except ModuleNotFoundError:
    team_classifiers = {}
    detecter = None


class MyJob(Job):
    def _execute(self):
        # remember to set PYDEVD_USE_CYTHON=NO when debugging in pycharm
        job_type = JobStruct.Type(self.kwargs.pop("type"))

        self.team: Team = Team.objects.get(username=self.kwargs["team_username"])

        if job_type == JobStruct.Type.DETECT:
            return self._detect_image(DetectJob(**self.kwargs))
        elif job_type == JobStruct.Type.STORE_IMG_FEATURES:
            return self._store_image_features(StoreImageFeaturesJob(**self.kwargs))
        elif job_type == JobStruct.Type.TRAIN:
            return self._train_team(TrainJob(**self.kwargs))
        elif job_type == JobStruct.Type.LOAD_CLASSIFIER:
            return self._load_team_classifier(LoadClassifierJob(**self.kwargs))
        elif job_type == JobStruct.Type.UNLOAD_CLASSIFIER:
            return self._unload_team_classifier(UnloadClassifierJob(**self.kwargs))
        elif job_type == JobStruct.Type.DELETE_CLASSIFIER:
            return self._delete_team_classifier(DeleteClassifierJob(**self.kwargs))

    def _detect_image(self, job: DetectJob) -> bool:
        if (
            job.team_username in team_classifiers
            and team_classifiers[job.team_username].has_trained_model()
        ):
            return detecter.detect(
                img=job.img,
                file_name=job.file_name,
                store_image_features=job.store_image_features,
                classifier=team_classifiers[job.team_username],
                team=self.team,
            )
        return False

    def _store_image_features(self, job: StoreImageFeaturesJob) -> bool:
        num_trained = self.team.num_features_added_last_hr()
        num_allowed = self.team.max_train_imgs_per_hr
        if num_trained >= num_allowed:
            logging.warning(f"User {job.team_username} has uploaded too many images.")
            return False

        return detecter.store_image_features(
            job.img, job.file_name, job.member_id, self.team
        )

    def _train_team(self, job: TrainJob) -> bool:
        if job.team_username in team_classifiers:
            try:
                num_trained_classes = team_classifiers[job.team_username].train()
                return self.team.send_ws_message(TrainedWSStruct(num_trained_classes))
            except AlreadyTrainingException as e:
                logging.warning(e)
                return self.team.send_ws_message(ErrorWSStruct(str(e)))
            except NotEnoughClassesException as e:
                logging.error(e)
                return self.team.send_ws_message(ErrorWSStruct(str(e)))
        logging.error(
            f"Train - The team '{job.team_username}' has no classifier loaded."
        )
        return False

    def _load_team_classifier(self, job: LoadClassifierJob):
        team_classifiers[job.team_username] = Classifier(self.team)

    def _unload_team_classifier(self, job: UnloadClassifierJob):
        team_classifiers.pop(job.team_username, None)

    def _delete_team_classifier(self, job: DeleteClassifierJob) -> bool:
        if job.team_username in team_classifiers:
            team_classifiers[job.team_username].delete()

            # remove classifier from memory
            team_classifiers.pop(job.team_username, None)
            return True
        logging.warning(
            f"Delete - The team '{job.team_username}' has no classifier loaded."
        )
        return False


class MyQueue(Queue):
    job_class = MyJob


class MyWorker(Worker):
    queue_class = MyQueue
    job_class = MyJob


def enqueue(q: MyQueue, job: JobStruct) -> MyJob:
    return q.enqueue_call(func=".", kwargs=job.dict())


REDIS_QS = ["high", "medium", "low"]
REDIS_HIGH_Q = MyQueue(REDIS_QS[0], connection=REDIS_CONN, default_timeout=60)
REDIS_MED_Q = MyQueue(REDIS_QS[1], connection=REDIS_CONN, default_timeout=60)
REDIS_LOW_Q = MyQueue(
    REDIS_QS[2], connection=REDIS_CONN, default_timeout=TRAIN_Q_TIMEOUT
)
