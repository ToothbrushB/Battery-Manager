from __future__ import annotations

from datetime import datetime

import msgspec
import sqlalchemy

from core import get_engine
from models import (
    Asset,
    BatteryDb,
    CustomFieldDb,
    FieldMappingDb,
    MatchBatteryAssignmentDb,
    MatchDb,
    record_battery_history,
)


class TbaService:
    def _clear_match_key_for_existing_assignments(
        self, db_session: sqlalchemy.orm.Session, match_key: str, field_name: str
    ) -> None:
        previous_assignments = (
            db_session.query(MatchBatteryAssignmentDb).filter_by(match_key=match_key).all()
        )
        for prev_assignment in previous_assignments:
            prev_battery = db_session.get(BatteryDb, prev_assignment.battery_id)
            if not prev_battery or not prev_battery.remote_data:
                continue
            asset = msgspec.msgpack.decode(prev_battery.remote_data, type=Asset)
            if asset.custom_fields and field_name in asset.custom_fields:
                asset.custom_fields[field_name].value = ""
                prev_battery.remote_data = msgspec.msgpack.encode(asset)
                prev_battery.sync_status = "local_updated"
                prev_battery.local_modified_at = str(datetime.now().timestamp())
                record_battery_history(db_session, prev_battery)

    def assign_battery_to_match(self, payload: dict) -> tuple[dict[str, str], int]:
        match_key = payload.get("match_key")
        battery_id = payload.get("battery_id")
        multi_assign = bool(payload.get("multi_assign"))
        battery_ids_payload = (
            payload.get("battery_ids") if isinstance(payload.get("battery_ids"), list) else []
        )

        if not match_key:
            return ({"message": "match_key is required", "status": "error"}, 400)

        with sqlalchemy.orm.Session(get_engine()) as db_session:
            match = db_session.get(MatchDb, match_key)
            if not match:
                return ({"message": "Match not found", "status": "error"}, 404)

            match_field_mapping = db_session.query(FieldMappingDb).filter_by(name="Match Key").first()
            if not match_field_mapping:
                return ({"message": "Match field mapping not found", "status": "error"}, 400)

            custom_field = (
                db_session.query(CustomFieldDb)
                .filter_by(db_column_name=match_field_mapping.db_column_name)
                .first()
            )
            if not custom_field:
                return ({"message": "Custom field for Match Key not found", "status": "error"}, 400)

            match_field_mapping_name = custom_field.name

            if multi_assign:
                selected_ids: list[int] = []
                seen: set[int] = set()
                for raw in battery_ids_payload:
                    if raw in (None, ""):
                        continue
                    try:
                        battery_int = int(raw)
                    except (TypeError, ValueError):
                        return ({"message": "Invalid battery id", "status": "error"}, 400)
                    if battery_int in seen:
                        return ({"message": "Duplicate battery selected", "status": "error"}, 400)
                    seen.add(battery_int)
                    selected_ids.append(battery_int)

                if not selected_ids:
                    self._clear_match_key_for_existing_assignments(
                        db_session, match.key, match_field_mapping_name
                    )
                db_session.query(MatchBatteryAssignmentDb).filter_by(match_key=match.key).delete()
                match.assigned_battery_id = selected_ids[0] if selected_ids else None

                for idx, selected_id in enumerate(selected_ids):
                    battery = db_session.get(BatteryDb, selected_id)
                    if not battery:
                        return (
                            {"message": f"Battery {selected_id} not found", "status": "error"},
                            404,
                        )

                    db_session.add(
                        MatchBatteryAssignmentDb(
                            match_key=match.key,
                            battery_id=selected_id,
                            sort_order=idx,
                            created_at=str(datetime.now().timestamp()),
                        )
                    )

                    if battery.remote_data:
                        asset = msgspec.msgpack.decode(battery.remote_data, type=Asset)
                        if asset.custom_fields and match_field_mapping_name in asset.custom_fields:
                            asset.custom_fields[match_field_mapping_name].value = match_key
                        battery.remote_data = msgspec.msgpack.encode(asset)

                    battery.sync_status = "local_updated"
                    battery.local_modified_at = str(datetime.now().timestamp())
                    record_battery_history(db_session, battery)
            else:
                if not battery_id:
                    self._clear_match_key_for_existing_assignments(
                        db_session, match.key, match_field_mapping_name
                    )
                db_session.query(MatchBatteryAssignmentDb).filter_by(match_key=match.key).delete()
                match.assigned_battery_id = int(battery_id) if battery_id else None

                if battery_id:
                    battery = db_session.get(BatteryDb, int(battery_id))
                    if not battery:
                        return ({"message": "Battery not found", "status": "error"}, 404)

                    if battery.remote_data:
                        asset = msgspec.msgpack.decode(battery.remote_data, type=Asset)
                        if asset.custom_fields and match_field_mapping_name in asset.custom_fields:
                            asset.custom_fields[match_field_mapping_name].value = match_key
                        battery.remote_data = msgspec.msgpack.encode(asset)

                    battery.sync_status = "local_updated"
                    battery.local_modified_at = str(datetime.now().timestamp())
                    record_battery_history(db_session, battery)

            db_session.commit()

        return ({"message": "Battery assignment updated", "status": "success"}, 200)
