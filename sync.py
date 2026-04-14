from __future__ import annotations
import asyncio
import logging
from datetime import datetime
import sqlalchemy
from sqlalchemy.orm import Session
import httpx
from models import *
from helpers import *
import msgspec
from core import get_engine

CHECKIN_PENDING_MARKER = "__checkin__"


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
            
        return await asyncio.gather(*tasks, return_exceptions=True) # wait for all tasks to complete


async def batch_checkout_assets(checkouts: list[tuple[int, str]]):
    if not checkouts:
        return []
    semaphore = asyncio.Semaphore(5)
    async with httpx.AsyncClient() as client:
        tasks = []
        for battery_id, target_asset_id in checkouts:
            payload = {
                "checkout_to_type": "asset",
                "assigned_asset": target_asset_id,
                "note": "Checked out via Battery Manager",
            }
            tasks.append(
                snipe_it_post_async(
                    f"/hardware/{battery_id}/checkout",
                    data=payload,
                    client=client,
                    semaphore=semaphore,
                )
            )
        return await asyncio.gather(*tasks, return_exceptions=True)


async def batch_checkin_assets(battery_ids: list[int]):
    if not battery_ids:
        return []
    semaphore = asyncio.Semaphore(5)
    async with httpx.AsyncClient() as client:
        tasks = []
        for battery_id in battery_ids:
            payload = {
                "note": "Checked in via Battery Manager",
            }
            tasks.append(
                snipe_it_post_async(
                    f"/hardware/{battery_id}/checkin",
                    data=payload,
                    client=client,
                    semaphore=semaphore,
                )
            )
        return await asyncio.gather(*tasks, return_exceptions=True)

def download_hardware_changes():
    assets = asyncio.run(fetch_all(Asset, '/hardware', params={"model_id": int(get_preference("battery-model-id") or 0)}))
    field_data = msgspec.json.decode(asyncio.run(snipe_it_get_async('/fields')).text, type=Paginated[CustomField])
    locations = asyncio.run(fetch_all(Location, '/locations'))
    status_labels = asyncio.run(fetch_all(StatusLabel, '/statuslabels'))
    
    assets_to_upload = []
    with Session(get_engine()) as session:  
        for field in field_data.rows: 
            existing = session.get(CustomFieldDb, field.db_column_name)
            if existing is None: # new field
                session.add(CustomFieldDb.fromCustomField(field))
            else: # existing field, update with latest change
                field.config = existing.config # preserve local config
                existing = CustomFieldDb.fromCustomField(field, existing)
                existing.sync_status = "remote_updated"
        session.commit()
        
        # Sort locations to process parents before children (respects FK constraint)
        sorted_locations = []
        locations_by_id = {loc.id: loc for loc in locations}
        processed_ids = set()
        
        def can_process(location: Location) -> bool:
            """Check if location's parent has been processed or doesn't exist"""
            return location.parent is None or location.parent.id in processed_ids
        
        # Keep processing until all locations are handled
        remaining = locations[:]
        while remaining:
            # Find locations that can be processed in this iteration
            processable = [loc for loc in remaining if can_process(loc)]
            
            if not processable and remaining:
                # Circular dependency or missing parent - process remaining as-is
                logging.warning(f"Warning: {len(remaining)} locations have unresolved dependencies")
                processable = remaining
            
            for location in processable:
                sorted_locations.append(location)
                processed_ids.add(location.id)
                remaining.remove(location)
        
        for location in sorted_locations:
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
        
        for asset in assets: # add all batteries to the db
            existing = session.get(BatteryDb, asset.id)
            if existing is None: # new battery
                obj = BatteryDb.fromAsset(asset)
                obj.sync_status = "new"
                session.add(obj)
                record_battery_history(session, obj)
            else: # existing battery, update with latest change
                if (float(existing.local_modified_at) if existing.local_modified_at is not None else 0) > datetime.strptime(asset.updated_at.datetime, "%Y-%m-%d %H:%M:%S").timestamp(): # if there is a local change
                    logging.info(f"Local change detected for asset {asset.id}, skipping download")
                    assets_to_upload.append(existing)
                    continue
                existing = BatteryDb.fromAsset(asset, existing)
                existing.sync_status = "remote_updated"
                existing.local_modified_at = None
                record_battery_history(session, existing)
        session.commit()

        pending_checkouts: list[tuple[int, str]] = []
        pending_checkins: list[int] = []
        for battery in (
            session.query(BatteryDb)
            .filter(BatteryDb.checkout_pending_asset_id.isnot(None))
            .all()
        ):
            if battery.checkout_pending_asset_id == CHECKIN_PENDING_MARKER:
                pending_checkins.append(battery.id)
            elif battery.checkout_pending_asset_id:
                pending_checkouts.append((battery.id, battery.checkout_pending_asset_id))

        if pending_checkins:
            responses = asyncio.run(batch_checkin_assets(pending_checkins))
            for battery_id, response in zip(pending_checkins, responses):
                if isinstance(response, Exception):
                    logging.error(f"Check-in failed for battery {battery_id}: {response}")
                    continue
                response_text = (response.text or "").lower()
                already_checked_in = (
                    "already checked in" in response_text
                    or "not checked out" in response_text
                )
                if (response.status_code >= 300 or response.json().get("status") != "success") and not already_checked_in:
                    logging.error(
                        f"Check-in failed for battery {battery_id}: {response.status_code} {response.text}"
                    )
                    continue
                if already_checked_in:
                    logging.info(f"Check-in already satisfied for battery {battery_id}; clearing pending marker")
                else:
                    logging.info(f"Check-in successful for battery {battery_id}")
                db_battery = session.get(BatteryDb, battery_id)
                if db_battery:
                    db_battery.checked_out_to_asset_id = None
                    db_battery.checkout_pending_asset_id = None
            session.commit()

        if pending_checkouts:

            responses = asyncio.run(batch_checkout_assets(pending_checkouts))
            for (battery_id, _), response in zip(pending_checkouts, responses):
                if isinstance(response, Exception):
                    logging.error(f"Checkout failed for battery {battery_id}: {response}")
                    continue
                if response.status_code >= 300 or response.json().get("status") != "success":
                    logging.error(
                        f"Checkout failed for battery {battery_id}: {response.status_code} {response.text}"
                    )
                    continue
                logging.info(f"Checkout successful for battery {battery_id}")
                db_battery = session.get(BatteryDb, battery_id)
                if db_battery:
                    db_battery.checkout_pending_asset_id = None
            session.commit()

        responses = asyncio.run(batch_update_assets([msgspec.msgpack.decode(battery.remote_data, type=Asset) for battery in assets_to_upload]))
        for battery, response in zip(assets_to_upload, responses):
            if isinstance(response, Exception):
                logging.error(f"Update failed for battery {battery.id}: {response}")
                continue
            if response.status_code >= 300 or response.json().get("status") != "success":
                logging.error(
                    f"Update failed for battery {battery.id}: {response.status_code} {response.text}"
                )
                continue
            logging.info(f"Update successful for battery {battery.id}")
            db_battery = session.get(BatteryDb, battery.id)
            if db_battery:
                db_battery.local_modified_at = None
                db_battery.sync_status = "remote_uploaded"
    if rq.get_current_job(): # then need to close DBAPI connections to prevent connection leaks in rq workers
        with sqlalchemy.orm.Session(get_engine()) as db_session:
            kv_entry = db_session.get(KVStoreDb, "last_sync_job_id")
            if kv_entry is None:
                kv_entry = KVStoreDb(key="last_sync_job_id", value=rq.get_current_job().id)
                db_session.add(kv_entry)
            else:
                kv_entry.value = rq.get_current_job().id
            db_session.commit()
        get_engine().dispose()


        
if __name__ == "__main__":
    download_hardware_changes()