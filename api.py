import os
from flask import Blueprint, Response, jsonify, request
import sqlalchemy
from models import *
from redis import Redis
from rq import Queue, Repeat
from rq_scheduler import Scheduler
from rq import job
import rq
import sync
import netifaces as ni 
import socket
from helpers import ping

redisq = Queue(connection=Redis())
scheduler = Scheduler(queue=redisq, connection=redisq.connection)
api = Blueprint("api", __name__, url_prefix="/api")

engine = sqlalchemy.create_engine(os.getenv("DATABASE_URL"))

scheduler.schedule(scheduled_time=datetime.now(), func=ping, interval=60, repeat=None, queue_name='default')
scheduler.schedule(scheduled_time=datetime.now(), func=sync.download_hardware_changes, interval=300, repeat=None, queue_name='default')

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
                    sync_job = job.Job.fetch(kv_entry.value, connection=Redis())
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
    if request.method == "GET":
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
            if data["batteryLocation"] is not None and data["batteryLocation"] != "":
                try:
                    result.location = int(data["batteryLocation"])
                    unpacked.location = Location(int(data["batteryLocation"]))
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
            
            result.remote_data = msgspec.msgpack.encode(unpacked)
            result.sync_status = "local_updated"
            result.local_modified_at = datetime.now().timestamp()
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
                sync_job = job.Job.fetch(kv_entry.value, connection=Redis())
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
