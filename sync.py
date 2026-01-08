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

async def fetch_asset(asset_id: int, client: httpx.AsyncClient, semaphore: asyncio.Semaphore) -> Asset: # semaphore idea from AI
    async with semaphore:
        response = await snipe_it_get_async(f'/hardware/{asset_id}', client=client)
        print(f"Fetched asset {asset_id} in {response.elapsed}s")
        asset = msgspec.json.decode(response.text, type=Asset)
        return asset

async def fetch_all_assets(asset_ids: list[int]) -> list[Asset]:
    semaphore = asyncio.Semaphore(10) # limit to 5 concurrent requests
    async with httpx.AsyncClient() as client: # reuse the same client for all requests
        tasks = [fetch_asset(asset_id, client=client, semaphore=semaphore) for asset_id in asset_ids]
        return await asyncio.gather(*tasks) # wait for all tasks to complete
def download_hardware_changes():
    print("Starting hardware sync...")
    with Session(engine) as session:
        encoder = msgspec.msgpack.Encoder()
        offset = 0
        # if you fetch only a few, you get the full dataset back
        data = msgspec.json.decode(snipe_it_get('/hardware', params={"limit":5, "offset": offset, "model_id": int(os.getenv("BATTERY_MODEL_ID"))}).text, type=Paginated[Asset])
        while len(data.rows) < data.total: # get all the pages
            offset += 5
            next_page = msgspec.json.decode(snipe_it_get('/hardware', params={"limit":5, "offset": offset, "model_id": int(os.getenv("BATTERY_MODEL_ID"))}).text, type=Paginated[Asset])
            data.rows.extend(next_page.rows)
        
        
        # print("Fetched", len(data.rows), "battery assets from Snipe-IT")
        # assets = asyncio.run(fetch_all_assets([asset.id for asset in data.rows])) # start fetching all assets asynchronously
        
        for asset in data.rows: # add all batteries to the db
            existing = session.get(BatteryDb, asset.id)
            
            if existing is None: # new battery
                session.add(BatteryDb(id=asset.id,
                asset_tag=asset.asset_tag,
                name=asset.name,
                location_id=asset.location.id if asset.location else None,
                remote_data=encoder.encode(asset), # store the full asset data as msgpack
                remote_modified_at=datetime.strptime(asset.updated_at.datetime, "%Y-%m-%d %H:%M:%S").timestamp(),
                last_synced_at=None,
                local_modified_at=None,
                sync_status="new"))
            else: # existing battery, update with latest change
                if (existing.local_modified_at if existing.local_modified_at is not None else 0) > datetime.strptime(asset.updated_at.datetime, "%Y-%m-%d %H:%M:%S").timestamp():
                    
                    # need to sync the other way
                    continue
                existing.asset_tag = asset.asset_tag
                existing.name = asset.name
                existing.location_id = asset.location.id if asset.location else None
                existing.remote_data = encoder.encode(asset)
                existing.remote_modified_at = asset.updated_at.datetime
                existing.sync_status = "updated"
        session.commit()
        

download_hardware_changes()