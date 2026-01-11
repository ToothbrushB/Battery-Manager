import os
from flask import Blueprint, Response, jsonify, request
import sqlalchemy
from models import *
from redis import Redis
from rq import Queue

rq = Queue(connection=Redis())
api = Blueprint("api", __name__, url_prefix="/api")

engine = sqlalchemy.create_engine(os.getenv("DATABASE_URL"))
with open("schema.sql") as f, engine.connect() as connection:
    statements = f.read().split(";")
    for statement in statements:
        if statement.strip():
            connection.execute(sqlalchemy.text(statement))
    connection.commit()
import sync


@api.route("/sync", methods=["GET"])
def get_sync_status():
    """Retrieve current sync status"""
    return (
        jsonify(
            {
                "status": "Ok",
                "last_sync": "2024-06-01T12:00:00Z",
                "message": "Sync completed successfully",
            }
        ),
        200,
    )


@api.route("/sync", methods=["POST"])
def trigger_sync():
    """Trigger a sync operation"""
    rq.enqueue(sync.download_hardware_changes)
    return jsonify({"status": "In Progress", "message": "Sync initiated"}), 202


@api.route("/qr_scan", methods=["POST"])
def qr_scan():
    """Handle QR code scan"""
    # TODO: Implement QR scan handling logic here
    input = request.json.get("qr_data")
    if "/hardware/" in input:  # this is a url in the form of /hardware/{id}
        id = input.split("/hardware/")[1]
        return get_battery_info(id)
    elif "/location/" in input:  # this is a url in the form of /location/{id}
        id = input.split("/location/")[1]
        return jsonify({"error": "Location QR codes not yet supported"}), 400
    elif input.regex_match("^[0-9]+$"):  # this is just an id
        id = int(input)
        return get_battery_info(id)
    else:
        return jsonify({"error": "Invalid QR code data"}), 400


@api.route("/battery/<int:battery_id>", methods=["GET", "PATCH"])
def get_battery_info(battery_id):
    """Retrieve battery information by ID"""
    if request.method == "GET":
        with engine.connect() as connection:
            query = sqlalchemy.select(BatteryDb).where(BatteryDb.id == battery_id)
            result = connection.execute(query).fetchone()
            if result:
                return Response(
                    msgspec.json.encode(BatteryView.from_battery_db(result)),
                    200,
                    mimetype="application/json",
                )
            else:
                return jsonify({"error": "Battery not found"}), 404
    elif request.method == "PATCH":
        data = request.json
        with engine.connect() as connection:
            query = sqlalchemy.select(BatteryDb).where(BatteryDb.id == battery_id)
            result = connection.execute(query).fetchone()
            if not result:
                return jsonify({"error": "Battery not found"}), 404
            # TODO finish this


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
            locations.append(location)
        return Response(
            msgspec.json.encode(locations), 200, mimetype="application/json"
        )


@api.route("/status", methods=["GET"])
def get_status():
    return jsonify(
        {
            "status": {
                "name": "Operational",
                "icon": "check-circle",
                "network": {
                    "status": "Online",
                    "icon": "wifi",
                    "ip_address": ["POPULATE WITH ACTUAL IPS"],
                    "ping": "POPULATE WITH ACTUAL PING",
                },
                "sync": {
                    "status": "Ok",
                    "icon": "cloud-check",
                    "last_sync": "2024-06-01T12:00:00Z",
                },
            }
        }
    )
