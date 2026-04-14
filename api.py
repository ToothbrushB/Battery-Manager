import os
import re
from datetime import datetime
from flask import Blueprint, Response, jsonify, request, session
import sqlalchemy
import msgspec
from models import *
from rq import job

import rq
import sync
import tba_sync
import tba as tba_client
import netifaces as ni 
from helpers import format_elapsed
from preferences import get_preference, get_allowed_checkout_assets, get_hidden_asset_ids
from core import get_engine, get_redis, get_queue
from bootstrap_scheduler import ensure_periodic_job
from services import get_battery_service, get_tba_service
from functools import wraps

api = Blueprint("api", __name__, url_prefix="/api")


def api_success(message: str | None = None, data=None, status_code: int = 200):
    payload = {"status": "success"}
    if message is not None:
        payload["message"] = message
    if data is not None:
        payload["data"] = data
    return jsonify(payload), status_code


def api_error(message: str, status_code: int = 400, details=None):
    payload = {"status": "error", "message": message}
    if details is not None:
        payload["details"] = details
    return jsonify(payload), status_code


def api_login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if session.get("user_id") is None:
            return api_error("Authentication required", 401)
        return f(*args, **kwargs)

    return wrapper


def api_admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        username = session.get("user_id")
        if username is None:
            return api_error("Authentication required", 401)
        with sqlalchemy.orm.Session(get_engine()) as db_session:
            user = db_session.get(UserDb, username)
            if user is None or (user.role or "viewer") != "admin":
                return api_error("Admin access required", 403)
        return f(*args, **kwargs)

    return wrapper

@api.route("/v1/sync", methods=["POST", "GET"])
@api.route("/sync", methods=["POST", "GET"])
def trigger_sync():
    """Trigger a sync operation"""
    if request.method == "POST":
        if session.get("user_id") is None:
            return api_error("Authentication required", 401)
        with sqlalchemy.orm.Session(get_engine()) as db_session:
            user = db_session.get(UserDb, session.get("user_id"))
            if user is None or (user.role or "viewer") != "admin":
                return api_error("Admin access required", 403)
        sync_job = ensure_periodic_job("periodic_hardware_sync", sync.download_hardware_changes, 60)
        with sqlalchemy.orm.Session(get_engine()) as db_session:
            kv_entry = db_session.get(KVStoreDb, "last_sync_job_id")
            if kv_entry is None:
                kv_entry = KVStoreDb(key="last_sync_job_id", value=sync_job.id)
                db_session.add(kv_entry)
            else:
                kv_entry.value = sync_job.id
            db_session.commit()
        return api_success("Sync initiated", data={"job_status": "queued"}, status_code=202)
    else: 
        with sqlalchemy.orm.Session(get_engine()) as db_session:
            kv_entry = db_session.get(KVStoreDb, "last_sync_job_id")
            if kv_entry is not None:
                try:
                    sync_job = job.Job.fetch(kv_entry.value, connection=get_redis())
                except rq.exceptions.NoSuchJobError:
                    sync_job = None
            else:
                sync_job = None
            if sync_job is None:
                return api_error("No sync job initiated", 500)
            status = sync_job.get_status()
            return api_success(data={"job_status": status})

@api.route("/v1/location", methods=["GET"])
@api.route("/location", methods=["GET"])
def location_info():
    with sqlalchemy.orm.Session(get_engine()) as db_session:
        locations = db_session.query(LocationDb).all()
        location_list = []
        for loc in locations:
            decoded = msgspec.msgpack.decode(loc.remote_data, type=Location)
            decoded.allowed = loc.allowed
            location_list.append(decoded)
        return Response(
            msgspec.json.encode(location_list), 200, mimetype="application/json"
        )

@api.route("/v1/location/<int:location_id>", methods=["GET"])
@api.route("/location/<int:location_id>", methods=["GET"])
def get_location_info(location_id):
    with sqlalchemy.orm.Session(get_engine()) as db_session:
        loc = db_session.get(LocationDb, location_id)
        if not loc:
            return api_error("Location not found", 404)
        decoded = msgspec.msgpack.decode(loc.remote_data, type=Location)
        decoded.allowed = loc.allowed
        return Response(
            msgspec.json.encode(decoded), 200, mimetype="application/json"
        )

@api.route("/v1/qr_scan", methods=["POST"])
@api.route("/qr_scan", methods=["POST"])
def qr_scan():
    """Handle QR code scan"""
    qr_data = str((request.json or {}).get("qr_data") or "").strip()
    if not qr_data:
        return api_error("Invalid QR code data", 400)

    if "/hardware/" in qr_data:  # this is a url in the form of /hardware/{id}
        match = re.search(r"/hardware/(\d+)", qr_data)
        if not match:
            return api_error("Invalid hardware QR code data", 400)
        id = int(match.group(1))
        return get_battery_info(id)
    elif "/location/" in qr_data:  # this is a url in the form of /location/{id}
        id = qr_data.split("/location/")[1]
        return api_error("Location QR codes not yet supported", 400)
    elif re.fullmatch(r"\d+", qr_data):  # this is just an id
        id = int(qr_data)
        return get_battery_info(id)
    else:
        return api_error("Invalid QR code data", 400)

@api.route("/v1/register_tag", methods=["POST"])
@api.route("/register_tag", methods=["POST"])
@api_admin_required
def register_tag():
    """Register a new NFC tag to a battery"""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return api_error("JSON body is required", 400)
    battery_id = data.get("battery_id")
    tag_id = data.get("tag_id")
    if not battery_id or not tag_id:
        return api_error("Battery ID and Tag ID are required", 400)
    with sqlalchemy.orm.Session(get_engine()) as db_session:
        battery = db_session.get(BatteryDb, battery_id)
        if not battery:
            return api_error("Battery not found", 404)
        battery.nfc_tag = tag_id
        db_session.commit()
    return api_success("Tag registered successfully")

@api.route("/v1/reader/<int:reader_id>", methods=["GET", "POST"])
@api.route("/reader/<int:reader_id>", methods=["GET", "POST"])
def reader_info(reader_id):
    """Retrieve reader information by ID"""
    if request.method == "GET":
        pass  # interact with the NFC reader

@api.route("/v1/battery/<int:battery_id>", methods=["GET", "PUT"])
@api.route("/v1/batteries/<int:battery_id>", methods=["GET", "PUT"])
@api.route("/battery/<int:battery_id>", methods=["GET", "PUT"])
@api.route("/batteries/<int:battery_id>", methods=["GET", "PUT"])
def get_battery_info(battery_id):
    """Retrieve battery information by ID"""
    if request.method == "GET":
        result = get_battery_service().get_battery(battery_id)
        if result is None:
            return api_error("Battery not found", 404)
        return Response(
            msgspec.json.encode(result),
            200,
            mimetype="application/json",
        )
    elif request.method == "PUT":
        username = session.get("user_id")
        if username is None:
            return api_error("Authentication required", 401)
        with sqlalchemy.orm.Session(get_engine()) as db_session:
            user = db_session.get(UserDb, username)
            if user is None or (user.role or "viewer") != "admin":
                return api_error("Admin access required", 403)
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return api_error("JSON body is required", 400)
        response, status_code = get_battery_service().update_battery(battery_id, data)
        return jsonify(response), status_code


@api.route("/v1/custom_fields", methods=["GET"])
@api.route("/custom_fields", methods=["GET"])
def get_custom_fields():
    """Retrieve all custom fields"""
    with get_engine().connect() as connection:
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


@api.route("/v1/locations", methods=["GET"])
@api.route("/locations", methods=["GET"])
def get_locations():
    """Retrieve all locations"""
    only_allowed_param = (request.args.get("onlyAllowed") or "").strip().lower()
    only_allowed = only_allowed_param in {"1", "true", "yes", "on"}

    with get_engine().connect() as connection:
        query = sqlalchemy.select(LocationDb)
        if only_allowed:
            allowed_parent_ids = (
                sqlalchemy.select(LocationDb.id)
                .where(LocationDb.allowed.is_(True))
                .scalar_subquery()
            )
            query = query.where(
                sqlalchemy.or_(
                    LocationDb.allowed.is_(True),
                    LocationDb.parent_id.in_(allowed_parent_ids),
                )
            )
        result = connection.execute(query).fetchall()
        locations = []
        for row in result:
            location = msgspec.msgpack.decode(row.remote_data, type=Location)
            location.allowed = row.allowed
            locations.append(location)
        return Response(
            msgspec.json.encode(locations), 200, mimetype="application/json"
        )
        
@api.route("/v1/status_labels", methods=["GET"])
@api.route("/status_labels", methods=["GET"])
def get_status_labels():
    with get_engine().connect() as connection:
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
        
        
@api.route("/v1/field_mappings", methods=["GET"])
@api.route("/field_mappings", methods=["GET"])
def get_field_mappings():
    with get_engine().connect() as connection:
        query = sqlalchemy.select(FieldMappingDb)
        result = connection.execute(query).fetchall()
        
        #turn result into json array
        field_mappings = []
        for row in result:
            field_mapping = {
                "id": row.id,
                "name": row.name,
                "db_column_name": row.db_column_name,
            }
            field_mappings.append(field_mapping)
            
        return Response(
            msgspec.json.encode(field_mappings), 200, mimetype="application/json"
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

@api.route("/v1/status", methods=["GET"])
@api.route("/status", methods=["GET"])
def get_status():
    
    with sqlalchemy.orm.Session(get_engine()) as db_session:
        kv_entry = db_session.get(KVStoreDb, "last_sync_job_id")
        if kv_entry is not None:
            try:
                sync_job = job.Job.fetch(kv_entry.value, connection=get_redis())
            except rq.exceptions.NoSuchJobError:
                sync_job = None
        else:
            sync_job = None
        kv_entry = db_session.get(KVStoreDb, "ping_rtt_ms")
        if kv_entry is not None:
            ping_rtt_ms = float(kv_entry.value)
        else:
            ping_rtt_ms = -1.0
    allOk = ping_rtt_ms >= 0 and (sync_job is not None and sync_job.get_status() in ["finished", "queued", "started"])
    status = {
        "status": {
            "name": "Operational" if allOk else "Problem",
            "icon": "check-circle" if allOk else "exclamation-triangle",
            "network": {
                "status": "Online" if ping_rtt_ms >= 0 else "Offline",
                "icon": "wifi",
                "ip_address": list(get_ip_addresses().values()),
                "ping": ping_rtt_ms,
            },
            "sync": {
                "status": sync_job.get_status() if sync_job is not None else "Unknown",
                "icon": "cloud-check" if sync_job is not None and sync_job.get_status() in ["finished", "queued", "started"] else "cloud-exclamation",
                "last_sync": (
                    format_elapsed(max(0.0, datetime.now().timestamp() - sync_job.ended_at.timestamp()))
                    if sync_job is not None and getattr(sync_job, "ended_at", None)
                    else ("In Progress" if sync_job is not None else None)
                ),
            },
        }
    }
    
    return jsonify(
        status
    )


@api.route("/v1/health/web", methods=["GET"])
@api.route("/health/web", methods=["GET"])
def health_web():
    checks = {
        "database": {"ok": False},
        "redis": {"ok": False},
    }

    try:
        with get_engine().connect() as connection:
            connection.execute(sqlalchemy.text("SELECT 1"))
        checks["database"]["ok"] = True
    except Exception as exc:
        checks["database"]["error"] = str(exc)

    try:
        get_redis().ping()
        checks["redis"]["ok"] = True
    except Exception as exc:
        checks["redis"]["error"] = str(exc)

    healthy = all(item["ok"] for item in checks.values())
    status_code = 200 if healthy else 503
    state = "healthy" if healthy else "unhealthy"
    return api_success(data={"component": "web", "state": state, "checks": checks}, status_code=status_code)


@api.route("/v1/health/worker", methods=["GET"])
@api.route("/health/worker", methods=["GET"])
def health_worker():
    checks = {
        "redis": {"ok": False},
        "worker": {"ok": False},
    }

    workers = []
    try:
        redis_conn = get_redis()
        redis_conn.ping()
        checks["redis"]["ok"] = True
        workers = rq.Worker.all(connection=redis_conn)
        checks["worker"]["ok"] = len(workers) > 0
        checks["worker"]["worker_count"] = len(workers)
    except Exception as exc:
        checks["redis"]["error"] = str(exc)

    if checks["worker"]["ok"]:
        worker_names = [worker.name for worker in workers]
        checks["worker"]["workers"] = worker_names

    healthy = checks["redis"]["ok"] and checks["worker"]["ok"]
    status_code = 200 if healthy else 503
    state = "healthy" if healthy else "unhealthy"
    return api_success(data={"component": "worker", "state": state, "checks": checks}, status_code=status_code)




@api.route("/v1/battery", methods=["GET"])
@api.route("/v1/batteries", methods=["GET"])
@api.route("/battery", methods=["GET"])
@api.route("/batteries", methods=["GET"])
def get_batteries():
    """Retrieve batteries filtered by allowed statuses and locations."""
    def parse_ts(value: str | None) -> float | None:
        if not value:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    hidden_asset_ids = get_hidden_asset_ids()
    checkout_asset_names = {
        str(item.get("id")): item.get("name", "")
        for item in get_allowed_checkout_assets()
        if item.get("id")
    }
    with sqlalchemy.orm.Session(get_engine()) as db_session:
        allowed_status_ids = {s.id for s in db_session.query(StatusLabelDb).filter_by(allowed=True).all()}
        allowed_parent_ids = {l.id for l in db_session.query(LocationDb).filter_by(allowed=True).all()}
        allowed_child_ids = {
            l.id for l in db_session.query(LocationDb).all()
            if l.parent_id in allowed_parent_ids
        }
        all_allowed_loc_ids = allowed_parent_ids | allowed_child_ids

        all_batteries = db_session.query(BatteryDb).all()
        visible_battery_ids = [b.id for b in all_batteries if b.id not in hidden_asset_ids]
        history_entries_by_battery: dict[int, list[BatteryHistoryDb]] = {}
        if visible_battery_ids:
            history_entries = (
                db_session.query(BatteryHistoryDb)
                .filter(BatteryHistoryDb.battery_id.in_(visible_battery_ids))
                .order_by(BatteryHistoryDb.battery_id.asc(), BatteryHistoryDb.recorded_at.desc())
                .all()
            )
            for entry in history_entries:
                history_entries_by_battery.setdefault(entry.battery_id, []).append(entry)

        now_ts = datetime.now().timestamp()

        result = []
        for b in all_batteries:
            if b.id in hidden_asset_ids:
                continue
            if not b.remote_data:
                continue
            asset = msgspec.msgpack.decode(b.remote_data, type=Asset)
            custom_field_values = {}
            if asset.custom_fields:
                for field_asset in asset.custom_fields.values():
                    if field_asset and field_asset.field:
                        custom_field_values[field_asset.field] = field_asset.value
            status_id = asset.status_label.id if asset.status_label else None
            location_id = asset.location.id if asset.location else None
            status_ok = not allowed_status_ids or status_id in allowed_status_ids or status_id is None
            location_ok = not all_allowed_loc_ids or location_id in all_allowed_loc_ids or location_id is None
            if status_ok and location_ok:
                location_elapsed_seconds = None
                location_elapsed_display = None
                current_location_name = asset.location.name if asset.location else None
                if current_location_name:
                    location_history_entries = history_entries_by_battery.get(b.id, [])
                    location_start_ts = None
                    for entry in location_history_entries:
                        if (entry.location_name or "") == current_location_name:
                            ts = parse_ts(entry.recorded_at)
                            if ts is not None:
                                location_start_ts = ts
                        elif location_start_ts is not None:
                            break
                    if location_start_ts is not None:
                        location_elapsed_seconds = max(0.0, now_ts - location_start_ts)
                        location_elapsed_display = format_elapsed(location_elapsed_seconds)

                result.append({
                    'id': b.id,
                    'name': b.name,
                    'asset_tag': b.asset_tag,
                    'status': asset.status_label.name if asset.status_label else None,
                    'location': asset.location.name if asset.location else None,
                    'location_id': location_id,
                    'location_elapsed_seconds': location_elapsed_seconds,
                    'location_elapsed_display': location_elapsed_display,
                    'checked_out_to_asset_id': b.checked_out_to_asset_id,
                    'checked_out_to_asset_name': checkout_asset_names.get(str(b.checked_out_to_asset_id), None) if b.checked_out_to_asset_id else None,
                    'custom_field_values': custom_field_values,
                })
        return jsonify(result)


@api.route("/v1/checkout_targets", methods=["GET"])
@api.route("/checkout_targets", methods=["GET"])
def get_checkout_targets():
    return jsonify(get_allowed_checkout_assets())


@api.route("/v1/tba/events", methods=["GET"])
@api.route("/tba/events", methods=["GET"])
def get_tba_events():
    """Fetch team events from TBA API."""
    team_key = request.args.get('team_key')
    year_raw = request.args.get('year', datetime.now().year)
    if not team_key:
        return api_error("team_key is required", 400)
    try:
        year = int(year_raw)
    except (TypeError, ValueError):
        return api_error("year must be an integer", 400)

    events = tba_client.get_team_events(team_key, year)
    if events is None:
        return api_error("Failed to fetch events from TBA. Check your API key and team key.", 503)

    events.sort(key=lambda e: e.get('start_date', ''))
    return jsonify(events)


@api.route("/v1/tba/matches", methods=["GET"])
@api.route("/tba/matches", methods=["GET"])
def get_tba_matches():
    """Retrieve matches for an event from the local cache."""
    event_key = request.args.get('event_key') or get_preference('tba-event-key')
    if not event_key or event_key == 'your-event-key-here':
        return jsonify({'matches': [], 'last_synced_at': None, 'event_key': None})

    with sqlalchemy.orm.Session(get_engine()) as db_session:
        matches = []
        for m in db_session.query(MatchDb).filter_by(event_key=event_key).all():
            d = m.to_dict()
            assignment_rows = (
                db_session.query(MatchBatteryAssignmentDb)
                .filter_by(match_key=m.key)
                .order_by(MatchBatteryAssignmentDb.sort_order.asc(), MatchBatteryAssignmentDb.id.asc())
                .all()
            )
            assigned_batteries = []
            for assignment in assignment_rows:
                battery = db_session.get(BatteryDb, assignment.battery_id)
                if battery:
                    assigned_batteries.append(
                        {"id": battery.id, "name": battery.name, "asset_tag": battery.asset_tag}
                    )

            if not assigned_batteries and m.assigned_battery_id:
                battery = db_session.get(BatteryDb, m.assigned_battery_id)
                if battery:
                    assigned_batteries.append(
                        {"id": battery.id, "name": battery.name, "asset_tag": battery.asset_tag}
                    )

            d['assigned_batteries'] = assigned_batteries
            d['assigned_battery'] = assigned_batteries[0] if assigned_batteries else None
            matches.append(d)

        kv = db_session.get(KVStoreDb, 'last_tba_sync_at')
        last_synced_at = kv.value if kv else None

    return jsonify({'matches': matches, 'last_synced_at': last_synced_at, 'event_key': event_key})


@api.route("/v1/tba/assign_battery", methods=["POST"])
@api.route("/tba/assign_battery", methods=["POST"])
@api_admin_required
def assign_battery_to_match():
    """Assign battery/batteries to a match and update local sync state."""
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return api_error("JSON body is required", 400)
    response, status_code = get_tba_service().assign_battery_to_match(payload)
    return jsonify(response), status_code


@api.route("/v1/tba/sync", methods=["POST", "GET"])
@api.route("/tba/sync", methods=["POST", "GET"])
def trigger_tba_sync():
    """Trigger or check status of TBA match sync."""
    if request.method == "POST":
        username = session.get("user_id")
        if username is None:
            return api_error("Authentication required", 401)
        with sqlalchemy.orm.Session(get_engine()) as db_session:
            user = db_session.get(UserDb, username)
            if user is None or (user.role or "viewer") != "admin":
                return api_error("Admin access required", 403)
        sync_job = get_queue().enqueue(tba_sync.download_match_updates)
        with sqlalchemy.orm.Session(get_engine()) as db_session:
            kv = db_session.get(KVStoreDb, "last_tba_sync_job_id")
            if kv is None:
                db_session.add(KVStoreDb(key="last_tba_sync_job_id", value=sync_job.id))
            else:
                kv.value = sync_job.id
            db_session.commit()
        return api_success("TBA sync initiated", data={"job_status": "queued"}, status_code=202)
    else:
        with sqlalchemy.orm.Session(get_engine()) as db_session:
            kv = db_session.get(KVStoreDb, "last_tba_sync_job_id")
            if kv is not None:
                try:
                    sync_job = job.Job.fetch(kv.value, connection=get_redis())
                except rq.exceptions.NoSuchJobError:
                    sync_job = None
            else:
                sync_job = None
        if sync_job is None:
            return api_error("No TBA sync job initiated", 404)
        return api_success(data={"job_status": sync_job.get_status()})
