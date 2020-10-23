import logging

from rq import Queue, Worker
from rq.job import Job

from idmyteam.structs import (
    JobStruct,
    DetectJob,
    StoreImageJob,
    TrainJob,
    LoadClassifierJob,
    UnloadClassifierJob,
    DeleteClassifierJob,
)
from idmyteamserver.models import Team
from web.settings import REDIS_CONN, TRAIN_Q_TIMEOUT

try:
    from worker.classifier import Classifier
except ModuleNotFoundError:
    pass

team_classifiers = {}
detecter = None


class MyJob(Job):
    team: Team

    def _execute(self):
        job_type = JobStruct.Type(self.kwargs.pop("type"))

        self.team: Team = Team.objects.get(username=self.kwargs["team_username"])
        if not self.team:
            raise Exception(
                f"No such team with the username: {self.kwargs['team_username']}"
            )

        if job_type == JobStruct.Type.DETECT:
            return self._detect_image(DetectJob(**self.kwargs))
        elif job_type == JobStruct.Type.STORE_IMG:
            return self._store_image(StoreImageJob(**self.kwargs))
        elif job_type == JobStruct.Type.TRAIN:
            return self._train_team(TrainJob(**self.kwargs))
        elif job_type == JobStruct.Type.LOAD_CLASSIFIER:
            return self._load_team_classifier(LoadClassifierJob(**self.kwargs))
        elif job_type == JobStruct.Type.UNLOAD_CLASSIFIER:
            return self._unload_team_classifier(UnloadClassifierJob(**self.kwargs))
        elif job_type == JobStruct.Type.DELETE_CLASSIFIER:
            return self._delete_team_classifier(DeleteClassifierJob(**self.kwargs))
        return Exception("Not a valid job")

    def _store_image(self, job: StoreImageJob):
        num_trained = self.team.num_features_added_last_hr()
        num_allowed = self.team.max_train_imgs_per_hr
        if num_trained >= num_allowed:
            raise Exception(f"User {job.team_username} has uploaded too many images.")

        return detecter.store_image(job.img, job.file_name, job.member_id, self.team)

    def _detect_image(self, job: DetectJob):
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
        else:
            raise Exception(
                f"The team '{job.team_username}' does not have a trained model."
            )

    def _train_team(self, job: TrainJob) -> bool:
        if job.team_username in team_classifiers:
            team_classifiers[job.team_username].train()
            return True
        logging.warning(
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
            team_classifiers.pop(job.team_username, None)
            return True
        logging.info(
            f"Delete - The team '{job.team_username}' has no classifier loaded."
        )
        return False


class MyQueue(Queue):
    job_class = MyJob


class MyWorker(Worker):
    queue_class = MyQueue
    job_class = MyJob


REDIS_QS = ["high", "medium", "low"]
REDIS_HIGH_Q = MyQueue("high", connection=REDIS_CONN, default_timeout=60)
REDIS_MED_Q = MyQueue("medium", connection=REDIS_CONN, default_timeout=60)
REDIS_LOW_Q = MyQueue("low", connection=REDIS_CONN, default_timeout=TRAIN_Q_TIMEOUT)
