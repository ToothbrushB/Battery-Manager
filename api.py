import os
from flask import Blueprint, Response, jsonify, request
import sqlalchemy
from models import *
from redis import Redis
from rq import Queue, Repeat
from rq import job
import rq
import sync
import tba_sync
import tba as tba_client
import netifaces as ni 
from helpers import ping
from preferences import get_preference, get_allowed_checkout_assets, get_hidden_asset_ids

redisq = Queue(connection=Redis(os.getenv("REDIS_HOST", "localhost"), port=os.getenv("REDIS_PORT", 6379)))
api = Blueprint("api", __name__, url_prefix="/api")

engine = sqlalchemy.create_engine(os.getenv("DATABASE_URL"))
Base.metadata.create_all(engine)
ensure_battery_checkout_columns(engine)

def ensure_periodic_job(job_id: str, func, interval_seconds: int):
    """Ensure a single periodic job exists for RQ worker --with-scheduler."""

    try:
        existing_job = job.Job.fetch(job_id, connection=redisq.connection)
        if existing_job:
            status = existing_job.get_status(refresh=False)
            if status not in {"finished", "failed", "stopped", "canceled"}:
                return existing_job
            existing_job.delete()
            redisq.connection.delete(f"rq:job:{job_id}")
    except rq.exceptions.NoSuchJobError:
        existing_job = None

    return redisq.enqueue(
        func,
        job_id=job_id,
        # RQ Repeat requires an integer for `times`; use a very large value
        # to provide effectively continuous scheduling.
        repeat=Repeat(times=2_147_483_647, interval=interval_seconds),
    )


ensure_periodic_job("periodic_ping", ping, 5)
sync_job = ensure_periodic_job("periodic_hardware_sync", sync.download_hardware_changes, 60)
tba_sync_job = ensure_periodic_job("periodic_tba_sync", tba_sync.download_match_updates, 60)
with sqlalchemy.orm.Session(engine) as db_session:
    kv_entry = db_session.get(KVStoreDb, "last_sync_job_id")
    if kv_entry is None:
        kv_entry = KVStoreDb(key="last_sync_job_id", value=sync_job.id)
        db_session.add(kv_entry)
    else:
        kv_entry.value = sync_job.id
    kv = db_session.get(KVStoreDb, "last_tba_sync_job_id")
    if kv is None:
        db_session.add(KVStoreDb(key="last_tba_sync_job_id", value=tba_sync_job.id))
    else:
        kv.value = tba_sync_job.id
    db_session.commit()

CHECKIN_PENDING_MARKER = "__checkin__"


def increment_cycle_count_for_checkout(db_session: sqlalchemy.orm.Session, asset: Asset) -> None:
    """Increment mapped cycle-count custom field on checkout if configured."""

    mapping = (
        db_session.query(FieldMappingDb)
        .filter(FieldMappingDb.name == "Battery Cycle Count")
        .first()
    )
    if mapping is None or not mapping.db_column_name:
        return

    custom_field = db_session.get(CustomFieldDb, mapping.db_column_name)
    if custom_field is None or not asset.custom_fields:
        return

    field_asset = asset.custom_fields.get(custom_field.name)
    if field_asset is None:
        return

    raw_value = field_asset.value
    try:
        current_count = int(float(str(raw_value).strip())) if raw_value not in (None, "") else 0
    except (TypeError, ValueError):
        current_count = 0

    field_asset.value = str(current_count + 1)

@api.route("/sync", methods=["POST", "GET"])
def trigger_sync():
    """Trigger a sync operation"""
    if request.method == "POST":
        sync_job = redisq.enqueue(sync.download_hardware_changes)
        with sqlalchemy.orm.Session(engine) as db_session:
            kv_entry = db_session.get(KVStoreDb, "last_sync_job_id")
            if kv_entry is None:
                kv_entry = KVStoreDb(key="last_sync_job_id", value=sync_job.id)
                db_session.add(kv_entry)
            else:
                kv_entry.value = sync_job.id
            db_session.commit()
        return jsonify({"status": "Queued", "message": "Sync initiated"}), 202 # 202 for accepted/in processing
    else: 
        with sqlalchemy.orm.Session(engine) as db_session:
            kv_entry = db_session.get(KVStoreDb, "last_sync_job_id")
            if kv_entry is not None:
                try:
                    sync_job = job.Job.fetch(kv_entry.value, connection=Redis(os.getenv("REDIS_HOST", "localhost"), port=os.getenv("REDIS_PORT", 6379)))
                except rq.exceptions.NoSuchJobError:
                    sync_job = None
            else:
                sync_job = None
            if sync_job is None:
                return jsonify({"status": "No sync job initiated"}), 500
            status = sync_job.get_status()
            return jsonify({"status": status}), 200

@api.route("/qr_scan", methods=["POST"])
def qr_scan():
    """Handle QR code scan"""
    input = request.json.get("qr_data")
    if "/hardware/" in input:  # this is a url in the form of /hardware/{id}
        id = input.split("/hardware/")[1]
        return get_battery_info(id)
    elif "/location/" in input:  # this is a url in the form of /location/{id}
        id = input.split("/location/")[1]
        return jsonify({"message": "Location QR codes not yet supported", "status": "error"}), 400
    elif input.regex_match("^[0-9]+$"):  # this is just an id
        id = int(input)
        return get_battery_info(id)
    else:
        return jsonify({"message": "Invalid QR code data", "status": "error"}), 400

@api.route("/register_tag", methods=["POST"])
def register_tag():
    """Register a new NFC tag to a battery"""
    data = request.json
    battery_id = data.get("battery_id")
    tag_id = data.get("tag_id")
    if not battery_id or not tag_id:
        return jsonify({"message": "Battery ID and Tag ID are required", "status": "error"}), 400
    with sqlalchemy.orm.Session(engine) as db_session:
        battery = db_session.get(BatteryDb, battery_id)
        if not battery:
            return jsonify({"message": "Battery not found", "status": "error"}), 404
        battery.nfc_tag = tag_id
        db_session.commit()
    return jsonify({"message": "Tag registered successfully", "status": "success"}), 200

@api.route("/reader/<int:reader_id>", methods=["GET", "POST"])
def reader_info(reader_id):
    """Retrieve reader information by ID"""
    if request.method == "GET":
        pass  # interact with the NFC reader

@api.route("/battery/<int:battery_id>", methods=["GET", "PUT"])
def get_battery_info(battery_id):
    """Retrieve battery information by ID"""
    if request.method == "GET" or request.method == "POST":
        with sqlalchemy.orm.Session(engine) as db_session:
            result = db_session.get(BatteryDb, battery_id)
            
            if result:
                result = BatteryView.from_battery_db(result)
                for name, custom_field in result.custom_fields.items():
                    result.custom_fields[name].custom_field = db_session.get(CustomFieldDb, custom_field.field).toCustomField()
                return Response(
                    msgspec.json.encode(result),
                    200,
                    mimetype="application/json",
                )
            else:
                return jsonify({"message": "Battery not found", "status": "error"}), 404
    elif request.method == "PUT":
        data = request.json
        with sqlalchemy.orm.Session(engine) as db_session:
            result = db_session.get(BatteryDb, battery_id)
            if not result:
                return jsonify({"message": "Battery not found", "status": "error"}), 404
            # Update fields
            unpacked = msgspec.msgpack.decode(result.remote_data, type=Asset)
            if "batteryLocation" in data and data["batteryLocation"]:
                try:
                    result.location = int(data["batteryLocation"])
                    unpacked.location = msgspec.msgpack.decode(db_session.get(LocationDb, int(data["batteryLocation"])).remote_data, type=Location)
                except ValueError:
                    return jsonify({"message": "Invalid location ID", "status": "error"}), 400
            if data["batteryStatusSelect"] is not None and data["batteryStatusSelect"] != "":
                try:
                    result.statusLabel = int(data["batteryStatusSelect"])
                    status_label_db = db_session.get(StatusLabelDb, int(data["batteryStatusSelect"]))
                    if status_label_db is None:
                        return jsonify({"message": "Status label not found", "status": "error"}), 400
                    unpacked.status_label = status_label_db.toStatusLabelAsset()
                except ValueError:
                    return jsonify({"message": "Invalid status label ID", "status": "error"}), 400
            if data["batteryNotes"] is not None:
                result.notes = data["batteryNotes"]
                unpacked.notes = data["batteryNotes"]
            for db_name, value in data.items(): # update custom fields
                if db_name.startswith("_snipeit_"):
                    field = db_session.get(CustomFieldDb, db_name)
                    if field is not None:
                        unpacked.custom_fields[field.name].value = value
                    else:
                        return jsonify({"message": f"Custom field {db_name} not found", "status": "error"}), 400
            checkout_target = data.get("batteryCheckoutTarget")
            if checkout_target == "":
                checkout_target = None
            if (
                checkout_target
                and result.checked_out_to_asset_id
                and checkout_target != result.checked_out_to_asset_id
            ):
                return jsonify({
                    "message": "Battery is already checked out to another asset. Check it in first before assigning a different asset.",
                    "status": "error",
                }), 409
            if checkout_target and checkout_target != result.checked_out_to_asset_id:
                increment_cycle_count_for_checkout(db_session, unpacked)
                result.checked_out_to_asset_id = checkout_target
                result.checkout_pending_asset_id = checkout_target
                try:
                    assigned_id = int(checkout_target)
                except (TypeError, ValueError):
                    assigned_id = None
                if assigned_id is not None:
                    unpacked.assigned_to = Assignee(
                        id=assigned_id, name=None, type="asset"
                    )
            elif not checkout_target:
                was_checked_out = bool(result.checked_out_to_asset_id)
                result.checked_out_to_asset_id = None
                result.checkout_pending_asset_id = CHECKIN_PENDING_MARKER if was_checked_out else None
                unpacked.assigned_to = None
            
            result.remote_data = msgspec.msgpack.encode(unpacked)
            result.sync_status = "local_updated"
            result.local_modified_at = datetime.now().timestamp()
            record_battery_history(db_session, result)
            db_session.commit()
        return jsonify({"message": "Battery updated successfully", "status": "success"}), 200


@api.route("/custom_fields", methods=["GET"])
def get_custom_fields():
    """Retrieve all custom fields"""
    with engine.connect() as connection:
        query = sqlalchemy.select(CustomFieldDb)
        result = connection.execute(query).fetchall()
        custom_fields = []
        for row in result:
            field = msgspec.msgpack.decode(row.remote_data, type=CustomField)
            field.config = (
                CustomFieldConfig(row.config) if row.config else CustomFieldConfig.HIDE
            )
            custom_fields.append(field)
        return Response(
            msgspec.json.encode(custom_fields), 200, mimetype="application/json"
        )


@api.route("/locations", methods=["GET"])
def get_locations():
    """Retrieve all locations"""
    with engine.connect() as connection:
        query = sqlalchemy.select(LocationDb)
        result = connection.execute(query).fetchall()
        locations = []
        for row in result:
            location = msgspec.msgpack.decode(row.remote_data, type=Location)
            location.allowed = row.allowed
            locations.append(location)
        return Response(
            msgspec.json.encode(locations), 200, mimetype="application/json"
        )
        
@api.route("/status_labels", methods=["GET"])
def get_status_labels():
    with engine.connect() as connection:
        query = sqlalchemy.select(StatusLabelDb)
        result = connection.execute(query).fetchall()
        status_labels = []
        for row in result:
            status_label = msgspec.msgpack.decode(row.remote_data, type=StatusLabel)
            status_label.allowed = row.allowed
            status_labels.append(status_label)
        return Response(
            msgspec.json.encode(status_labels), 200, mimetype="application/json"
        )
        


def get_ip_addresses(): #code snippet from ai overview
    ip_info = {}
    for interface in ni.interfaces():
        # Get addresses for the interface, specifically IPv4 (AF_INET)
        addresses = ni.ifaddresses(interface).get(ni.AF_INET)
        if addresses:
            # Each interface can have multiple addresses. We take the first one here.
            # 'addr' is the key for the IP address in the dictionary
            ip_address = addresses[0]['addr']
            ip_info[interface] = ip_address
    return ip_info

@api.route("/status", methods=["GET"])
def get_status():
    
    with sqlalchemy.orm.Session(engine) as db_session:
        kv_entry = db_session.get(KVStoreDb, "last_sync_job_id")
        if kv_entry is not None:
            try:
                sync_job = job.Job.fetch(kv_entry.value, connection=Redis(os.getenv("REDIS_HOST", "localhost"), port=os.getenv("REDIS_PORT", 6379)))
            except rq.exceptions.NoSuchJobError:
                sync_job = None
        else:
            sync_job = None
        kv_entry = db_session.get(KVStoreDb, "ping_rtt_ms")
        if kv_entry is not None:
            ping_rtt_ms = float(kv_entry.value)
        else:
            ping_rtt_ms = -1.0
    status = {
            "status": {
                "name": "Operational",
                "icon": "check-circle",
                "network": {
                    "status": "Online" if ping_rtt_ms >= 0 else "Offline",
                    "icon": "wifi",
                    "ip_address": list(get_ip_addresses().values()),
                    "ping": ping_rtt_ms,
                },
                "sync": {
                    "status": sync_job.get_status() if sync_job is not None else "Unknown",
                    "icon": "cloud-check",
                    "last_sync": sync_job.ended_at.isoformat() if sync_job is not None and sync_job.ended_at else "In Progress",
                },
            }
        }
    
    return jsonify(
        status
    )


@api.route("/batteries", methods=["GET"])
def get_batteries():
    """Retrieve batteries filtered by allowed statuses and locations."""
    hidden_asset_ids = get_hidden_asset_ids()
    checkout_asset_names = {
        str(item.get("id")): item.get("name", "")
        for item in get_allowed_checkout_assets()
        if item.get("id")
    }
    with sqlalchemy.orm.Session(engine) as db_session:
        allowed_status_ids = {s.id for s in db_session.query(StatusLabelDb).filter_by(allowed=True).all()}
        allowed_parent_ids = {l.id for l in db_session.query(LocationDb).filter_by(allowed=True).all()}
        allowed_child_ids = {
            l.id for l in db_session.query(LocationDb).all()
            if l.parent_id in allowed_parent_ids
        }
        all_allowed_loc_ids = allowed_parent_ids | allowed_child_ids

        result = []
        for b in db_session.query(BatteryDb).all():
            if b.id in hidden_asset_ids:
                continue
            if not b.remote_data:
                continue
            asset = msgspec.msgpack.decode(b.remote_data, type=Asset)
            status_id = asset.status_label.id if asset.status_label else None
            location_id = asset.location.id if asset.location else None
            status_ok = not allowed_status_ids or status_id in allowed_status_ids
            location_ok = not all_allowed_loc_ids or location_id in all_allowed_loc_ids
            if status_ok and location_ok:
                result.append({
                    'id': b.id,
                    'name': b.name,
                    'asset_tag': b.asset_tag,
                    'status': asset.status_label.name if asset.status_label else None,
                    'location': asset.location.name if asset.location else None,
                    'checked_out_to_asset_id': b.checked_out_to_asset_id,
                    'checked_out_to_asset_name': checkout_asset_names.get(str(b.checked_out_to_asset_id), None) if b.checked_out_to_asset_id else None,
                })
        return jsonify(result)


@api.route("/checkout_targets", methods=["GET"])
def get_checkout_targets():
    return jsonify(get_allowed_checkout_assets())


@api.route("/tba/events", methods=["GET"])
def get_tba_events():
    """Fetch team events from TBA API."""
    team_key = request.args.get('team_key')
    year = request.args.get('year', datetime.now().year)
    if not team_key:
        return jsonify({"message": "team_key is required", "status": "error"}), 400

    events = tba_client.get_team_events(team_key, int(year))
    if events is None:
        return jsonify({"message": "Failed to fetch events from TBA. Check your API key and team key.", "status": "error"}), 503

    events.sort(key=lambda e: e.get('start_date', ''))
    return jsonify(events)


@api.route("/tba/matches", methods=["GET"])
def get_tba_matches():
    """Retrieve matches for an event from the local cache."""
    event_key = request.args.get('event_key') or get_preference('tba-event-key')
    if not event_key or event_key == 'your-event-key-here':
        return jsonify({'matches': [], 'last_synced_at': None, 'event_key': None})

    with sqlalchemy.orm.Session(engine) as db_session:
        matches = []
        for m in db_session.query(MatchDb).filter_by(event_key=event_key).all():
            d = m.to_dict()
            if m.assigned_battery_id:
                battery = db_session.get(BatteryDb, m.assigned_battery_id)
                if battery:
                    d['assigned_battery'] = {'id': battery.id, 'name': battery.name, 'asset_tag': battery.asset_tag}
            matches.append(d)

        kv = db_session.get(KVStoreDb, 'last_tba_sync_at')
        last_synced_at = kv.value if kv else None

    return jsonify({'matches': matches, 'last_synced_at': last_synced_at, 'event_key': event_key})


@api.route("/tba/assign_battery", methods=["POST"])
def assign_battery_to_match():
    """Assign a battery to a match and update the battery notes for Snipe-IT sync."""
    data = request.json
    match_key = data.get('match_key')
    battery_id = data.get('battery_id')

    if not match_key:
        return jsonify({"message": "match_key is required", "status": "error"}), 400

    with sqlalchemy.orm.Session(engine) as db_session:
        match = db_session.get(MatchDb, match_key)
        if not match:
            return jsonify({"message": "Match not found", "status": "error"}), 404

        match.assigned_battery_id = int(battery_id) if battery_id else None

        if battery_id:
            battery = db_session.get(BatteryDb, int(battery_id))
            if not battery:
                return jsonify({"message": "Battery not found", "status": "error"}), 404

            if battery.remote_data:
                asset = msgspec.msgpack.decode(battery.remote_data, type=Asset)
                existing_notes = asset.notes or ''
                # Remove any previous match assignment line then append new one
                lines = [l for l in existing_notes.split('\n') if not l.startswith('Match: ')]
                lines.append(f'Match: {match_key}')
                asset.notes = '\n'.join(lines).strip()
                # TODO. Need to update battery usage type to "Competition"
                battery.remote_data = msgspec.msgpack.encode(asset)

            battery.sync_status = "local_updated"
            battery.local_modified_at = str(datetime.now().timestamp())
            record_battery_history(db_session, battery)
            

        db_session.commit()

    return jsonify({"message": "Battery assigned successfully", "status": "success"}), 200


@api.route("/tba/sync", methods=["POST", "GET"])
def trigger_tba_sync():
    """Trigger or check status of TBA match sync."""
    if request.method == "POST":
        sync_job = redisq.enqueue(tba_sync.download_match_updates)
        with sqlalchemy.orm.Session(engine) as db_session:
            kv = db_session.get(KVStoreDb, "last_tba_sync_job_id")
            if kv is None:
                db_session.add(KVStoreDb(key="last_tba_sync_job_id", value=sync_job.id))
            else:
                kv.value = sync_job.id
            db_session.commit()
        return jsonify({"status": "Queued", "message": "TBA sync initiated"}), 202
    else:
        with sqlalchemy.orm.Session(engine) as db_session:
            kv = db_session.get(KVStoreDb, "last_tba_sync_job_id")
            if kv is not None:
                try:
                    sync_job = job.Job.fetch(kv.value, connection=Redis(os.getenv("REDIS_HOST", "localhost"), port=os.getenv("REDIS_PORT", 6379)))
                except rq.exceptions.NoSuchJobError:
                    sync_job = None
            else:
                sync_job = None
        if sync_job is None:
            return jsonify({"status": "No TBA sync job initiated"}), 404
        return jsonify({"status": sync_job.get_status()}), 200
