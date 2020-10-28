# from worker.queue import enqueue
from idmyteam.idmyteam.helpers import random_str
from web.settings import CREDENTIAL_LEN


def create_credentials() -> str:
    # return bcrypt.hashpw(bytes(random_str(CREDENTIAL_LEN), encoding='utf8'), bcrypt.gensalt()).decode()
    return random_str(CREDENTIAL_LEN)
