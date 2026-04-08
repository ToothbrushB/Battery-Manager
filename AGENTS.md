# Battery Manager - Project Documentation

## Overview

Battery Manager is a Flask application for managing FRC batteries synced from Snipe-IT. It now includes battery history tracking, checkout/check-in workflows, and The Blue Alliance (TBA) match assignment support in addition to core inventory views.

## Key Features

- Snipe-IT battery synchronization (download + upload of local edits)
- QR code scan workflow for battery lookup
- Editable custom fields with per-field visibility modes
- Allowed status/location filtering and hidden battery support
- Battery checkout/check-in to allowed assets
- Battery history snapshots with assignment/location/status change visibility
- TBA integration:
  - Event and match synchronization
  - Single and multi-battery assignment per match
  - Homepage sections for active and completed assigned batteries
- Background jobs via Redis Queue for ping, hardware sync, and TBA sync
- REST API used by frontend pages and modals

---

## Technology Stack

### Backend
- Flask 3.x
- SQLAlchemy 2.x
- Redis + RQ
- msgspec
- httpx
- pythonping

### Frontend
- Bootstrap 5
- html5-qrcode
- Chart.js
- D3.js
- Feather Icons

### Security
- Flask-SeaSurf (CSRF)
- Flask-Talisman (CSP + security headers)
- Werkzeug password hashing

---

## Architecture Overview

```
Flask App
├── app.py                  # Page routes + auth + settings pages
├── api.py                  # REST API blueprint
├── sync.py                 # Snipe-IT sync + upload/check-in/check-out
├── tba_sync.py             # TBA match cache synchronization
├── tba.py                  # TBA client wrapper
├── preferences.py          # Preference and field mapping management
├── helpers.py              # HTTP helpers, ping, utilities
└── models.py               # SQLAlchemy models + msgspec DTOs
```

Data stores:
- Primary SQL database (SQLite by default)
- Redis (session store + queue backend)

---

## Core Components

### 1. Main App (`app.py`)

Primary page routes:
- `/` Home dashboard:
  - Batteries by status with elapsed time in current status
  - Batteries assigned to upcoming/completed matches
- `/list_view` Table view
- `/grid_view` Placeholder grid view
- `/history` Battery change history table (recent entries)
- `/history/clear` Clear history entries
- `/settings` Preferences, field configuration, allowed locations/statuses, hidden batteries
- `/load_matches` Match page with assignment workflow
- `/login`, `/register`, `/logout`

Notable behavior:
- Build/version string in footer via `git describe`
- No-cache response headers on all responses

### 2. API Blueprint (`api.py`)

Core endpoints:
- Sync and status:
  - `GET/POST /api/sync`
  - `GET /api/status`
- Batteries:
  - `GET /api/battery`
  - `GET/PUT /api/battery/<battery_id>`
  - `GET /api/checkout_targets`
- Metadata:
  - `GET /api/locations`
  - `GET /api/location`
  - `GET /api/location/<location_id>`
  - `GET /api/status_labels`
  - `GET /api/custom_fields`
  - `GET /api/field_mappings`
- Scan and tagging:
  - `POST /api/qr_scan`
  - `POST /api/register_tag`
- TBA:
  - `GET /api/tba/events`
  - `GET /api/tba/matches`
  - `POST /api/tba/assign_battery`
  - `GET/POST /api/tba/sync`

### 3. Sync Engine (`sync.py`)

`download_hardware_changes()` performs:
1. Pull assets/fields/locations/status labels from Snipe-IT.
2. Merge into local DB with conflict handling.
3. Queue local-modified batteries for remote upload.
4. Process pending checkouts/check-ins.
5. Upload local changes in batches.

### 4. TBA Sync (`tba_sync.py`, `tba.py`)

- Pulls match data for configured event key.
- Upserts `MatchDb` rows while preserving assignment state.
- Updates `last_tba_sync_at` in key-value storage.

### 5. Preferences (`preferences.py`)

- Persists settings from `config.json` into DB.
- Manages:
  - allowed checkout assets preference
  - hidden battery asset IDs
  - field mapping defaults (Usage Type, Voltage Curve, Cycle Count, Match Key)

### 6. Models (`models.py`)

Primary tables:
- `UserDb`
- `BatteryDb`
- `BatteryHistoryDb`
- `LocationDb`
- `StatusLabelDb`
- `CustomFieldDb`
- `PreferenceDb`
- `FieldMappingDb`
- `KVStoreDb`
- `EventDb`
- `MatchDb`
- `MatchBatteryAssignmentDb`

Schema helper functions currently ensure missing columns/tables at runtime:
- checkout columns
- history columns
- match assignment table

---

## Current Workflows

### Battery Update Workflow
1. User opens battery modal.
2. User edits status/location/notes/custom fields/checkout target.
3. Frontend sends `PUT /api/battery/<id>`.
4. API updates stored asset payload, marks `sync_status=local_updated`, records history entry.
5. Next sync uploads update to Snipe-IT.

### Checkout/Check-in Workflow
1. User chooses checkout target (or clears it).
2. API updates local checkout state and pending marker.
3. Sync worker posts checkout/check-in to Snipe-IT.
4. Pending marker is cleared on success and history reflects transition.

### Match Assignment Workflow
1. User opens Load Matches page and syncs/loads matches.
2. User assigns one or multiple batteries to a match.
3. Assignment rows are stored in `MatchBatteryAssignmentDb`.
4. Mapped custom field (`Match Key`) is updated on assigned batteries.
5. Homepage shows assigned batteries by active vs completed matches.

---

## Background Jobs (RQ)

Current periodic scheduling in `api.py`:
- `periodic_ping` every 5s (`helpers.ping`)
- `periodic_hardware_sync` every 60s (`sync.download_hardware_changes`)
- `periodic_tba_sync` every 60s (`tba_sync.download_match_updates`)

Job IDs are tracked in `KVStoreDb` for status polling.

---

## Frontend Pages and Assets

Templates:
- `templates/index.html` - Home dashboard with status columns + assigned batteries
- `templates/list_view.html` - List/table battery view
- `templates/grid_view.html` - Grid placeholder
- `templates/history.html` - Change history
- `templates/load_matches.html` - Match management and assignment
- `templates/settings.html` - Preferences and admin settings

Primary scripts:
- `static/sync.js` - status polling, battery modal, updates
- `static/qr_reader.js` - scan workflow
- `static/tba.js` - event/match loading + assignment UI

---

## Configuration

### Environment Variables
- `DATABASE_URL`
- `REDIS_HOST`
- `REDIS_PORT`
- `FLASK_SECRET_KEY`

### Database-Backed Preferences (Examples)
- `snipe-url`
- `snipe-api-key`
- `battery-model-id`
- `asset-checkout-allowed`
- `tba-api-key`
- `tba-event-key`
- `tba-team-key`

---

## Known Caveats / Technical Debt

- Several modules perform DB setup and scheduler setup at import time.
- Auth decorators are defined but not consistently enforced on all routes.
- API/frontend contract drift exists in some places (example: singular vs plural battery endpoint naming).
- Some UI controls expected by JS are not present in template markup.
- Runtime schema mutation helpers should eventually be replaced with proper migrations.
- Test coverage is currently minimal.

---

## Planned / Incomplete Areas

1. Grid view battery cart mapping (drag/drop and spatial management)
2. Hardware reader integration beyond prototype usage
3. Deeper battery analytics and reporting
4. Stronger role-based access model and auditing controls

---

## Development Setup

```bash
# 1) Create and activate environment
python -m venv .venv
source .venv/bin/activate

# 2) Install dependencies
pip install -r requirements.txt

# 3) Configure environment variables in .env

# 4) Start Redis
redis-server

# 5) Run Flask app
flask run
```

Optional:
- `rq-dashboard` for queue visibility

---

## Support References

- Snipe-IT API: https://snipe-it.readme.io/reference
- TBA API v3: https://www.thebluealliance.com/apidocs/v3
- Flask: https://flask.palletsprojects.com/
- Python RQ: https://python-rq.org/

---

Last Updated: April 8, 2026
