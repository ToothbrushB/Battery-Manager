from __future__ import annotations
import os
from datetime import datetime
import sqlalchemy
from sqlalchemy.orm import Session
from models import Base, EventDb, MatchDb, KVStoreDb
import tba
from preferences import get_preference

engine = sqlalchemy.create_engine(os.getenv("DATABASE_URL"))
Base.metadata.create_all(engine)


def download_match_updates():
    """Download match data from TBA and update local MatchDb cache."""
    event_key = get_preference('tba-event-key')
    if not event_key or event_key in ('', 'your-event-key-here'):
        return {'status': 'skipped', 'message': 'No event key configured'}

    matches_data = tba.get_event_matches(event_key)
    if matches_data is None:
        return {'status': 'error', 'message': 'Failed to fetch matches from TBA (using cached data)'}

    with Session(engine) as session:
        # Ensure EventDb row exists
        event_db = session.get(EventDb, event_key)
        if event_db is None:
            session.add(EventDb(key=event_key))

        for match_data in matches_data:
            key = match_data.get('key')
            if not key:
                continue
            existing = session.get(MatchDb, key)
            if existing is None:
                session.add(MatchDb.from_tba_match(match_data))
            else:
                existing.update_from_tba(match_data)

        # Record sync timestamp
        kv = session.get(KVStoreDb, 'last_tba_sync_at')
        if kv is None:
            session.add(KVStoreDb(key='last_tba_sync_at', value=str(datetime.now().timestamp())))
        else:
            kv.value = str(datetime.now().timestamp())

        session.commit()

    return {'status': 'success', 'message': f'Updated {len(matches_data)} matches for {event_key}'}


if __name__ == "__main__":
    result = download_match_updates()
    print(result)
