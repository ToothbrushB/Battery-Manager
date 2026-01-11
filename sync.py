from __future__ import annotations
import asyncio
from datetime import datetime
import dotenv
import sqlalchemy
from sqlalchemy.orm import Session
from models import *
from helpers import *
import msgspec


dotenv_file = dotenv.find_dotenv()
dotenv.load_dotenv(dotenv_file)

engine = sqlalchemy.create_engine(os.getenv("DATABASE_URL"))
Base.metadata.create_all(engine)

def download_hardware_changes():
    
    assets = asyncio.run(fetch_all(Asset, '/hardware', params={"model_id": int(os.getenv("BATTERY_MODEL_ID"))}))
    field_data = msgspec.json.decode(asyncio.run(snipe_it_get_async('/fields')).text, type=Paginated[CustomField])
    locations = asyncio.run(fetch_all(Location, '/locations'))
    status_labels = asyncio.run(fetch_all(StatusLabel, '/statuslabels'))

    with Session(engine) as session:
        for asset in assets: # add all batteries to the db
            existing = session.get(BatteryDb, asset.id)
            
            if existing is None: # new battery
                session.add(BatteryDb.fromAsset(asset))
            else: # existing battery, update with latest change
                if (existing.local_modified_at if existing.local_modified_at is not None else 0) > datetime.strptime(asset.updated_at.datetime, "%Y-%m-%d %H:%M:%S").timestamp():
                    
                    # need to sync the other way
                    continue
                existing = BatteryDb.fromAsset(asset)
                existing.sync_status = "remote_updated"
        session.commit()
    
        for field in field_data.rows: 
            existing = session.get(CustomFieldDb, field.db_column_name)
            if existing is None: # new field
                session.add(CustomFieldDb.fromCustomField(field))
            else: # existing field, update with latest change
                existing = CustomFieldDb.fromCustomField(field)
                existing.sync_status = "remote_updated"
        session.commit()
        
        
        for location in locations:
            existing = session.get(LocationDb, location.id)
            if existing is None: # new location
                session.add(LocationDb.fromLocation(location))
            else: # existing location, update with latest change
                existing = LocationDb.fromLocation(location)
        session.commit()
        
        for status_label in status_labels:
            existing = session.get(StatusLabelDb, status_label.id)
            if existing is None: # new status label
                session.add(StatusLabelDb.fromStatusLabel(status_label))
            else: # existing status label, update with latest change
                existing = StatusLabelDb.fromStatusLabel(status_label)
        session.commit()
        

async def batch_update_assets(assets: list[Asset]):
    semaphore = asyncio.Semaphore(10) # limit to 10 concurrent requests
    async with httpx.AsyncClient() as client: # reuse the same client for all requests
        tasks = []
        for asset in assets:
            tasks.append(snipe_it_put_async(f"/hardware/{asset.id}", data=msgspec.json.encode(asset), client=client, semaphore=semaphore))
    return await asyncio.gather(*tasks) # wait for all tasks to complete

# assume conflicts are handled elsewhere TODO. 
def upload_hardware_changes():
    with Session(engine) as session:
        batteries = session.query(BatteryDb).where(BatteryDb.sync_status.is_("local_updated")).all()
        assets = [msgspec.msgpack.decode(battery.remote_data, type=Asset) for battery in batteries]
        asyncio.run(batch_update_assets(assets))