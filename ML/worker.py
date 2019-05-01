from classifier import Classifier
from detecter import Detecter
from settings import config, functions

import logging
import os
import redis
from threading import Thread
from rq import Worker, Queue, Connection
from rq.contrib.sentry import register_sentry
from raven import Client
from raven.transport.http import HTTPTransport
import sqlalchemy.pool as pool

logging.basicConfig(level='CRITICAL')

listen = ['high', 'medium', 'low']
redis_url = os.getenv('REDISTOGO_URL', 'redis://localhost:6379')
rq_conn = redis.from_url(redis_url)

classifiers = {}
no_classifier_jobs = {}
detecter = None

# db pool
def get_conn():
    return functions.connect(config.DB["username"], config.DB["password"], config.DB["db"])

mypool = pool.QueuePool(get_conn, max_overflow=10, pool_size=5)

def main():
    global detecter
    detecter = Detecter()

    with Connection(rq_conn):
        worker = MainWorker(list(map(Queue, listen)))

        # use sentry with worker
        client = Client(config.SENTRY_URL, transport=HTTPTransport)
        register_sentry(client, worker)

        # start worker
        worker.work()


class MainWorker(Worker):
    def execute_job(self, job, queue):
        if 'hashed_username' in job.kwargs:
            type = job.kwargs.pop('type') # Don't care about the type anymore
            hashed_username = job.kwargs['hashed_username']
            if type == 'detect':
                if hashed_username in classifiers:
                    db_conn = mypool.connect()
                    if 'member_id' in job.kwargs:
                        # training image
                        num_trained = functions.Team.get_num_trained_last_hr(db_conn, hashed_username)
                        num_allowed = functions.Team.get(db_conn, hashed_username)['max_train_imgs_per_hr']
                        if num_trained >= num_allowed:
                            logging.warning("User (%s) has uploaded too many images.", hashed_username)
                            return

                    detecter.run(classifier=classifiers[hashed_username], conn=db_conn, **job.kwargs)
                else:
                    logging.error("No classifier to run detector with. Reconnect websocket.")

                    # TODO force reconect all sockets
                    # socket = functions.create_socket()

                    # add to failed classification jobs
                    if hashed_username in no_classifier_jobs:
                        no_classifier_jobs[hashed_username].append((job, queue))
                    else:
                        no_classifier_jobs[hashed_username] = [(job, queue)]
            elif type == 'train':
                if hashed_username in classifiers:
                    db_conn = mypool.connect()
                    thread = Thread(target=classifiers[hashed_username].train, args=(db_conn,))
                    thread.daemon = True
                    thread.start()
            elif type == 'add':
                classifiers[hashed_username] = Classifier(hashed_username)
                logging.info('Added classifier for %s', hashed_username)

                # enque 'detect' jobs that have been pending the addition of this classifier
                # if hashed_username in no_classifier_jobs:
                #     for arr in no_classifier_jobs[hashed_username]:
                #         job, queue = arr
                #         queue.enqueue_job(job)
            elif type == 'remove':
                # remove classifier
                classifiers.pop(hashed_username, None)
                logging.info('Removed classifier for %s', hashed_username)


if __name__ == '__main__':
    main()