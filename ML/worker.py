from classifier import Classifier
from detecter import Detecter
from utils import config, functions, db

import os
import redis
from threading import Thread
from rq import Worker, Queue, Connection
from rq.contrib.sentry import register_sentry
from raven import Client
from raven.transport.http import HTTPTransport
import sentry_sdk

from utils.logs import logger

sentry_sdk.init(os.getenv(config.SENTRY_URL))

listen = ["high", "medium", "low"]
redis_url = os.getenv("REDISTOGO_URL", "redis://localhost:6379")
rq_conn = redis.from_url(redis_url)

classifiers = {}
no_classifier_jobs = {}
detecter: Detecter = None


def main():
    global detecter
    detecter = Detecter()

    with Connection(rq_conn):
        worker = MainWorker(list(map(Queue, listen)))  # TODO this replaces queue

        # add sentry logging to worker
        client = Client(config.SENTRY_URL, transport=HTTPTransport)
        register_sentry(client, worker)

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

                    # TODO force reconnect all sockets

                    # add to failed classification jobs
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
    main()
