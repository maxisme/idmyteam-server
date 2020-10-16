import os

import redis
import sentry_sdk
from rq import Worker, Queue, Connection
from rq.job import Job

from classifier import Classifier
from detecter import Detecter
from idmyteamserver.models import Team
from idmyteamserver.structs import (
    JobStruct,
    DetectJob,
    StoreImageJob,
    TrainJob,
    LoadClassifierJob,
    UnloadClassifierJob,
)
from web.settings import REDIS_QS

team_classifiers = {}


class CustomJob(Job):
    team: Team

    def _execute(self):
        job_type = JobStruct.Type(self.kwargs["type"])

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
                team=self.team
            )
        else:
            raise Exception(
                f"The team '{job.team_username}' does not have a trained model."
            )

    def _train_team(self, job: TrainJob):
        if job.team_username in team_classifiers:
            team_classifiers[job.team_username].train(self.team)
        else:
            raise Exception(f"The team '{job.team_username}' has no classifier loaded.")

    def _load_team_classifier(self, job: LoadClassifierJob):
        team_classifiers[job.team_username] = Classifier(self.team)

    def _unload_team_classifier(self, job: UnloadClassifierJob):
        team_classifiers.pop(job.team_username, None)


class CustomQueue(Queue):
    job_class = CustomJob


if __name__ == "__main__":
    sentry_url = os.getenv("SENTRY_URL", False)
    if not sentry_url:
        print("Missing SENTRY_URL environment variable")
        quit(1)
    sentry_sdk.init(sentry_url)

    redis_url = os.getenv("REDIS_URL", False)
    if not redis_url:
        print("Missing REDIS_URL environment variable")
        quit(1)

    # load large detector model
    global detecter
    detecter = Detecter()

    # start worker
    rq_conn = redis.from_url(redis_url)
    with Connection(rq_conn):
        worker = Worker(list(map(CustomQueue, REDIS_QS)))
        worker.work()
