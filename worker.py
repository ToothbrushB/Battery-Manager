from rq import Connection, Worker

from bootstrap_db import ensure_all_schemas
from bootstrap_scheduler import ensure_periodic_jobs
from core import get_redis


def main():
    ensure_all_schemas()
    ensure_periodic_jobs()

    with Connection(get_redis()):
        worker = Worker(["default"])
        worker.work(with_scheduler=True)


if __name__ == "__main__":
    main()
