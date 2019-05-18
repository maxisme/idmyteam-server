from settings import functions, config
from sqlalchemy import pool


def get_conn():
    return functions.DB.conn(
        config.DB["username"], config.DB["password"], config.DB["db"]
    )


pool = pool.QueuePool(get_conn, max_overflow=10, pool_size=5)
