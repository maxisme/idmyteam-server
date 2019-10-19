from settings import functions, config
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool


def get_conn():
    return functions.DB.conn(
        config.DB["username"], config.DB["password"], config.DB["db"]
    )


pool = create_engine(creator=get_conn, poolclass=QueuePool, pool_recycle=3600)
