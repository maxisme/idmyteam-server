from classifier import Classifier
from detecter import Detecter
from settings import config, functions, db

import os
import redis
from threading import Thread
from rq import Worker, Queue, Connection
from rq.job import Job
from rq.contrib.sentry import register_sentry
from raven import Client
from raven.transport.http import HTTPTransport
import sentry_sdk

from settings.logs import logger

sentry_sdk.init(os.getenv(config.SENTRY_URL))


classifiers = {}
detecter: Detecter = None


def main():
    global detecter
    detecter = Detecter()
    listen = ["high", "medium", "low"]

    with Connection(redis.from_url(os.getenv("REDISTOGO_URL", "redis://localhost:6379"))):
        worker = Worker(queues=list(map(Queue, listen)), job_class=CustomJob)

        # add sentry logging to worker
        client = Client(config.SENTRY_URL, transport=HTTPTransport)
        register_sentry(client, worker)

        # start worker
        worker.work()


class CustomJob(Job):
    def _execute(self):
        if "hashed_username" in self.kwargs:
            type = self.kwargs.pop("type")
            hashed_username = self.kwargs["hashed_username"]

            if type == "detect":
                if hashed_username in classifiers:
                    db_conn = db.pool.raw_connection()
                    if "member_id" in self.kwargs:
                        # image used for training
                        num_trained = functions.Team.get_num_trained_last_hr(
                            db_conn, hashed_username
                        )
                        num_allowed = functions.Team.get(
                            db_conn, username=hashed_username
                        )["max_train_imgs_per_hr"]
                        if num_trained >= num_allowed:
                            logger.warning(f"User {hashed_username} has uploaded too many images.")
                            return
                    db_conn.close()

                    detecter.run(
                        classifier=classifiers[hashed_username],
                        **self.kwargs
                    )
                else:
                    raise Exception(f"{hashed_username} has no classifier to run detector with. Reconnect websocket.")

            elif type == "train":
                if hashed_username in classifiers:
                    thread = Thread(
                        target=classifiers[hashed_username].train
                    )
                    thread.daemon = True
                    thread.start()
                else:
                    logger.error(f"Asked to train team that is not connected to ws {hashed_username}")

            elif type == "add":
                # add Classifier to group of classifiers stored in memory
                classifiers[hashed_username] = Classifier(hashed_username)
                logger.info(f"Added classifier for {hashed_username}")

            elif type == "remove":
                # remove classifier
                classifiers.pop(hashed_username, None)
                logger.info(f"Removed classifier for {hashed_username}")
        return self.func(*self.args, **self.kwargs)


if __name__ == "__main__":
    main()
