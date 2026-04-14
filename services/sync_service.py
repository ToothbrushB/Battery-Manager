from __future__ import annotations

import sync
import tba_sync


class SyncService:
    """Service wrapper for sync-related workflows.

    This keeps route handlers decoupled from module-level sync functions
    and gives us a stable extension point for future orchestration logic.
    """

    def sync_hardware(self):
        return sync.download_hardware_changes()

    def sync_tba_matches(self):
        return tba_sync.download_match_updates()
