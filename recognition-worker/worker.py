import os
from threading import Thread

import redis
import sentry_sdk
from classifier import Classifier
from detecter import Detecter
from raven import Client
from raven.transport.http import HTTPTransport
from rq import Worker, Queue, Connection
from rq.contrib.sentry import register_sentry

from utils import functions, db
from utils.logs import logger

# initialise sentry

# redis
listen = ["high", "medium", "low"]
# redis_url = os.getenv("REDISTOGO_URL", "redis://localhost:6379")
# rq_conn = redis.from_url(redis_url)

classifiers = {}
no_classifier_jobs = {}
detecter: Detecter = None
global detecter
detecter = Detecter()


def start_worker(redis_url, sentry_url):
    rq_conn = redis.from_url(redis_url)

    with Connection(rq_conn):
        worker = MainWorker(list(map(Queue, listen)))

        # add sentry logging to worker
        register_sentry(Client(sentry_url, transport=HTTPTransport), worker)

        # start worker
        worker.work()


class MainWorker(Worker):
    def execute_job(self, job, queue):
        if "hashed_username" in job.kwargs:
            type = job.kwargs.pop("type")
            hashed_username = job.kwargs["hashed_username"]
            if type == "detect":
                if hashed_username in classifiers:
                    db_conn = db.pool.raw_connection()
                    if "member_id" in job.kwargs:
                        # image used for training
                        num_trained = functions.Team.get_num_trained_last_hr(
                            db_conn, hashed_username
                        )
                        num_allowed = functions.Team.get(
                            db_conn, username=hashed_username
                        )["max_train_imgs_per_hr"]
                        if num_trained >= num_allowed:
                            logger.warning(
                                f"User {hashed_username} has uploaded too many images."
                            )
                            return
                    db_conn.close()

                    detecter.run(classifier=classifiers[hashed_username], **job.kwargs)
                else:
                    logger.error(
                        f"{hashed_username} has no classifier to run detector with. Reconnect websocket."
                    )

                    # TODO force a reconnect of client

                    # add to failed classification jobs # TODO put back on redis
                    if hashed_username in no_classifier_jobs:
                        no_classifier_jobs[hashed_username].append((job, queue))
                    else:
                        no_classifier_jobs[hashed_username] = [(job, queue)]
            elif type == "train":
                if hashed_username in classifiers:
                    thread = Thread(target=classifiers[hashed_username].train)
                    thread.daemon = True
                    thread.start()
                else:
                    logger.error(
                        f"Asked to train team that is not connected to ws {hashed_username}"
                    )
            elif type == "add":
                classifiers[hashed_username] = Classifier(hashed_username)
                logger.info(f"Added classifier for {hashed_username}")

                # enque 'detect' jobs that have been pending the addition of this classifier
                if hashed_username in no_classifier_jobs:
                    for arr in no_classifier_jobs[hashed_username]:
                        job, queue = arr
                        queue.enqueue_job(job)
            elif type == "remove":
                # remove classifier
                classifiers.pop(hashed_username, None)
                logger.info(f"Removed classifier for {hashed_username}")


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

    start_worker(redis_url, sentry_url)
