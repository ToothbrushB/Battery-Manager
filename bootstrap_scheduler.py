import rq
from rq import Repeat
from rq import job

from core import get_queue


def ensure_periodic_job(job_id: str, func, interval_seconds: int):
    queue = get_queue()
    try:
        existing_job = job.Job.fetch(job_id, connection=queue.connection)
        if existing_job:
            status = existing_job.get_status(refresh=False)
            if status not in {"finished", "failed", "stopped", "canceled"}:
                return existing_job
            existing_job.delete()
            queue.connection.delete(f"rq:job:{job_id}")
    except rq.exceptions.NoSuchJobError:
        pass

    return queue.enqueue(
        func,
        job_id=job_id,
        repeat=Repeat(times=2_147_483_647, interval=interval_seconds),
    )


def ensure_periodic_jobs():
    # Imported lazily to avoid startup cycles.
    import sync
    import tba_sync
    from helpers import ping
    import sqlalchemy
    from models import KVStoreDb
    from core import get_engine

    sync_job = ensure_periodic_job("periodic_hardware_sync", sync.download_hardware_changes, 60)
    tba_sync_job = ensure_periodic_job("periodic_tba_sync", tba_sync.download_match_updates, 60)
    ensure_periodic_job("periodic_ping", ping, 5)

    with sqlalchemy.orm.Session(get_engine()) as db_session:
        kv_entry = db_session.get(KVStoreDb, "last_sync_job_id")
        if kv_entry is None:
            kv_entry = KVStoreDb(key="last_sync_job_id", value=sync_job.id)
            db_session.add(kv_entry)
        else:
            kv_entry.value = sync_job.id

        tba_kv_entry = db_session.get(KVStoreDb, "last_tba_sync_job_id")
        if tba_kv_entry is None:
            tba_kv_entry = KVStoreDb(key="last_tba_sync_job_id", value=tba_sync_job.id)
            db_session.add(tba_kv_entry)
        else:
            tba_kv_entry.value = tba_sync_job.id
        db_session.commit()
