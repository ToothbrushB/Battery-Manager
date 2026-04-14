from __future__ import annotations

from services.battery_service import BatteryService
from services.sync_service import SyncService
from services.tba_service import TbaService

_battery_service: BatteryService | None = None
_sync_service: SyncService | None = None
_tba_service: TbaService | None = None


def get_battery_service() -> BatteryService:
    global _battery_service
    if _battery_service is None:
        _battery_service = BatteryService()
    return _battery_service


def get_sync_service() -> SyncService:
    global _sync_service
    if _sync_service is None:
        _sync_service = SyncService()
    return _sync_service


def get_tba_service() -> TbaService:
    global _tba_service
    if _tba_service is None:
        _tba_service = TbaService()
    return _tba_service
