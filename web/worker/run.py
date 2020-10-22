import django

django.setup()

from rq import Connection
import worker
from worker.queue import MyQueue, MyWorker, REDIS_QS
from web.settings import REDIS_CONN
from worker.detecter import Detecter

if __name__ == "__main__":
    # load large detector model
    worker.detecter = Detecter()

    # start worker
    with Connection(REDIS_CONN):
        worker = MyWorker(list(map(MyQueue, REDIS_QS)))
        worker.work()
