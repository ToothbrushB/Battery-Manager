from __future__ import annotations
import asyncio
from datetime import datetime
import sqlalchemy
from sqlalchemy.orm import Session
from models import *
from helpers import *
import msgspec

engine = sqlalchemy.create_engine(os.getenv("DATABASE_URL"))
Base.metadata.create_all(engine)


async def batch_update_assets(assets: list[Asset]):
    semaphore = asyncio.Semaphore(10) # limit to 10 concurrent requests
    async with httpx.AsyncClient() as client: # reuse the same client for all requests
        tasks = []
        for asset in assets:
            data = {
                "notes": asset.notes,
                "location_id": asset.location.id if asset.location else None,
                "status_id": asset.status_label.id if asset.status_label else None,
                # "assigned_user": asset.assigned_user,
                # "assigned_location": asset.assigned_location,
                # "assigned_asset": asset.assigned_asset
            }
            for k,v in asset.custom_fields.items():
                data[v.field] = v.value
            tasks.append(snipe_it_put_async(f"/hardware/{asset.id}", data=data, client=client, semaphore=semaphore))
            
        return await asyncio.gather(*tasks) # wait for all tasks to complete

def download_hardware_changes():
    assets = asyncio.run(fetch_all(Asset, '/hardware', params={"model_id": int(get_preference("battery-model-id") or 0)}))
    field_data = msgspec.json.decode(asyncio.run(snipe_it_get_async('/fields')).text, type=Paginated[CustomField])
    locations = asyncio.run(fetch_all(Location, '/locations'))
    status_labels = asyncio.run(fetch_all(StatusLabel, '/statuslabels'))
    
    assets_to_upload = []
    with Session(engine) as session:
        for asset in assets: # add all batteries to the db
            existing = session.get(BatteryDb, asset.id)
            if existing is None: # new battery
                obj = BatteryDb.fromAsset(asset)
                obj.sync_status = "new"
                session.add(obj)
            else: # existing battery, update with latest change
                if (float(existing.local_modified_at) if existing.local_modified_at is not None else 0) > datetime.strptime(asset.updated_at.datetime, "%Y-%m-%d %H:%M:%S").timestamp(): # if there is a local change
                    print(f"Local change detected for asset {asset.id}, skipping download")
                    assets_to_upload.append(existing)
                    existing.sync_status = "remote_uploaded"
                    continue
                existing = BatteryDb.fromAsset(asset, existing)
                existing.sync_status = "remote_updated"
                existing.local_modified_at = None
        session.commit()
    
        for field in field_data.rows: 
            existing = session.get(CustomFieldDb, field.db_column_name)
            if existing is None: # new field
                session.add(CustomFieldDb.fromCustomField(field))
            else: # existing field, update with latest change
                field.config = existing.config # preserve local config
                existing = CustomFieldDb.fromCustomField(field, existing)
                existing.sync_status = "remote_updated"
        session.commit()
        
        
        for location in locations:
            existing = session.get(LocationDb, location.id)
            if existing is None: # new location
                session.add(LocationDb.fromLocation(location))
            else: # existing location, update with latest change
                location.allowed = existing.allowed
                existing = LocationDb.fromLocation(location, existing)
        session.commit()
        
        for status_label in status_labels:
            existing = session.get(StatusLabelDb, status_label.id)
            if existing is None: # new status label
                session.add(StatusLabelDb.fromStatusLabel(status_label))
            else: # existing status label, update with latest change
                existing = StatusLabelDb.fromStatusLabel(status_label, existing)
        session.commit()
    
        asyncio.run(batch_update_assets([msgspec.msgpack.decode(battery.remote_data, type=Asset) for battery in assets_to_upload]))
        
if __name__ == "__main__":
    download_hardware_changes()