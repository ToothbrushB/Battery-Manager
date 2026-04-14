import os

import sqlalchemy
from redis import Redis
from rq import Queue


_ENGINE = None
_REDIS = None
_QUEUE = None


def get_engine():
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = sqlalchemy.create_engine(os.getenv("DATABASE_URL"))
    return _ENGINE


def get_redis():
    global _REDIS
    if _REDIS is None:
        _REDIS = Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=os.getenv("REDIS_PORT", 6379),
        )
    return _REDIS


def get_queue():
    global _QUEUE
    if _QUEUE is None:
        _QUEUE = Queue(connection=get_redis())
    return _QUEUE
