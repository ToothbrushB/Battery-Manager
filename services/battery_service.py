from __future__ import annotations

from datetime import datetime
from typing import Any

import msgspec
import sqlalchemy

from core import get_engine
from models import (
    Asset,
    Assignee,
    BatteryDb,
    BatteryView,
    CustomFieldDb,
    FieldMappingDb,
    Location,
    LocationDb,
    StatusLabelDb,
    record_battery_history,
)


CHECKIN_PENDING_MARKER = "__checkin__"


class BatteryService:
    def get_battery(self, battery_id: int) -> BatteryView | None:
        with sqlalchemy.orm.Session(get_engine()) as db_session:
            battery = db_session.get(BatteryDb, battery_id)
            if not battery:
                return None

            view = BatteryView.from_battery_db(battery)
            if view.custom_fields:
                for name, custom_field in view.custom_fields.items():
                    db_custom_field = db_session.get(CustomFieldDb, custom_field.field)
                    if db_custom_field is not None:
                        view.custom_fields[name].custom_field = db_custom_field.toCustomField()
            return view

    def _increment_cycle_count_for_checkout(
        self, db_session: sqlalchemy.orm.Session, asset: Asset
    ) -> None:
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
            current_count = (
                int(float(str(raw_value).strip())) if raw_value not in (None, "") else 0
            )
        except (TypeError, ValueError):
            current_count = 0

        field_asset.value = str(current_count + 1)

    def update_battery(self, battery_id: int, data: dict[str, Any]) -> tuple[dict[str, str], int]:
        with sqlalchemy.orm.Session(get_engine()) as db_session:
            result = db_session.get(BatteryDb, battery_id)
            if not result:
                return ({"message": "Battery not found", "status": "error"}, 404)

            unpacked = msgspec.msgpack.decode(result.remote_data, type=Asset)
            if "batteryLocation" in data and data["batteryLocation"]:
                try:
                    result.location = int(data["batteryLocation"])
                    location_db = db_session.get(LocationDb, int(data["batteryLocation"]))
                    if location_db is None or not location_db.remote_data:
                        return ({"message": "Location not found", "status": "error"}, 400)
                    unpacked.location = msgspec.msgpack.decode(location_db.remote_data, type=Location)
                except ValueError:
                    return ({"message": "Invalid location ID", "status": "error"}, 400)

            if data.get("batteryStatusSelect") is not None and data.get("batteryStatusSelect") != "":
                try:
                    result.statusLabel = int(data["batteryStatusSelect"])
                    status_label_db = db_session.get(StatusLabelDb, int(data["batteryStatusSelect"]))
                    if status_label_db is None:
                        return ({"message": "Status label not found", "status": "error"}, 400)
                    unpacked.status_label = status_label_db.toStatusLabelAsset()
                except ValueError:
                    return ({"message": "Invalid status label ID", "status": "error"}, 400)

            if data.get("batteryNotes") is not None:
                result.notes = data["batteryNotes"]
                unpacked.notes = data["batteryNotes"]

            for db_name, value in data.items():
                if db_name.startswith("_snipeit_"):
                    field = db_session.get(CustomFieldDb, db_name)
                    if field is not None:
                        if not unpacked.custom_fields or field.name not in unpacked.custom_fields:
                            return (
                                {
                                    "message": f"Custom field '{field.name}' not initialized on this battery",
                                    "status": "error",
                                },
                                400,
                            )
                        unpacked.custom_fields[field.name].value = value
                    else:
                        return (
                            {"message": f"Custom field {db_name} not found", "status": "error"},
                            400,
                        )

            checkout_target = data.get("batteryCheckoutTarget")
            if checkout_target == "":
                checkout_target = None

            if (
                checkout_target
                and result.checked_out_to_asset_id
                and checkout_target != result.checked_out_to_asset_id
            ):
                return (
                    {
                        "message": "Battery is already checked out to another asset. Check it in first before assigning a different asset.",
                        "status": "error",
                    },
                    409,
                )

            if checkout_target and checkout_target != result.checked_out_to_asset_id:
                self._increment_cycle_count_for_checkout(db_session, unpacked)
                result.checked_out_to_asset_id = checkout_target
                result.checkout_pending_asset_id = checkout_target
                try:
                    assigned_id = int(checkout_target)
                except (TypeError, ValueError):
                    assigned_id = None
                if assigned_id is not None:
                    unpacked.assigned_to = Assignee(id=assigned_id, name=None, type="asset")
            elif not checkout_target:
                was_checked_out = bool(result.checked_out_to_asset_id)
                result.checked_out_to_asset_id = None
                result.checkout_pending_asset_id = CHECKIN_PENDING_MARKER if was_checked_out else None
                unpacked.assigned_to = None

            result.remote_data = msgspec.msgpack.encode(unpacked)
            result.sync_status = "local_updated"
            result.local_modified_at = str(datetime.now().timestamp())
            record_battery_history(db_session, result)
            db_session.commit()

        return ({"message": "Battery updated successfully", "status": "success"}, 200)
