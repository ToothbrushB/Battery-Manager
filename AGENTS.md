# Battery Manager - Project Documentation

## Overview

Battery Manager is a Flask-based web application designed to manage batteries for FRC (FIRST Robotics Competition) teams. It provides a user-friendly interface for tracking battery inventory, status, locations, and custom fields while synchronizing with a Snipe-IT asset management server.

### Key Features
- Real-time synchronization with Snipe-IT asset management
- QR code scanning for quick battery lookup
- Custom field management and display
- Location and status tracking
- User authentication and session management
- Background job processing with Redis Queue
- RESTful API for frontend interactions

---

## Technology Stack

### Backend
- **Flask 3.1.2** - Web framework
- **SQLAlchemy 2.0.44** - ORM for database operations
- **Redis 7.0.1** - Caching and session storage
- **RQ (Redis Queue) 2.6.1** - Background task processing
- **RQ Scheduler 0.14.0** - Scheduled job management

### Frontend
- **Bootstrap 5.x** - UI framework
- **html5-qrcode** - QR code scanning functionality
- **Chart.js** - Data visualization
- **D3.js** - Advanced visualizations
- **Feather Icons** - Icon library

### Security
- **Flask-SeaSurf 2.0.0** - CSRF protection
- **Flask-Talisman 1.1.0** - Security headers and CSP
- **Werkzeug 3.1.4** - Password hashing

### Data & Communication
- **msgspec 0.20.0** - Fast JSON/MessagePack serialization
- **httpx 0.28.1** - Async HTTP client for Snipe-IT integration

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                       Flask Application                      │
├─────────────────────────────────────────────────────────────┤
│  app.py (Main Routes)  │  api.py (REST API)                 │
├─────────────────────────────────────────────────────────────┤
│  helpers.py            │  preferences.py  │  sync.py        │
├─────────────────────────────────────────────────────────────┤
│                    SQLAlchemy ORM Layer                      │
│                      (models.py)                             │
├─────────────────────────────────────────────────────────────┤
│                    SQLite Database                           │
└─────────────────────────────────────────────────────────────┘
         ↕                    ↕                    ↕
   Redis/RQ Queue      Snipe-IT Server      Frontend Templates
```

---

## Core Components

### 1. Main Application (`app.py`)

**Purpose**: Primary Flask application with user-facing routes

**Key Routes**:
- `/` - Homepage with recommended batteries
- `/list_view` - Table view of all batteries
- `/grid_view` - Grid/card layout view
- `/settings` - Configuration interface
- `/login`, `/register`, `/logout` - Authentication
- `/load_matches` - Match schedule integration (planned)

**Features**:
- Session management with Redis
- CSRF protection via SeaSurf
- Content Security Policy (CSP) with Flask-Talisman
- User authentication with password hashing
- Settings management for custom fields, locations, statuses

### 2. API Blueprint (`api.py`)

**Purpose**: RESTful API endpoints for frontend and background operations

**Endpoints**:
- `POST/GET /api/sync` - Trigger or check status of Snipe-IT sync
- `POST /api/qr_scan` - Process QR code scans
- `POST /api/register_tag` - Register NFC tags to batteries

**Background Jobs**:
- Scheduled sync with Snipe-IT every 5 minutes (300s)
- Periodic ping checks every 60 seconds
- Job tracking via Redis Queue

### 3. Data Models (`models.py`)

**Database Tables** (SQLAlchemy ORM):

| Table | Purpose |
|-------|---------|
| `UserDb` | User authentication credentials |
| `BatteryDb` | Battery assets with sync status |
| `LocationDb` | Physical locations (hierarchical) |
| `StatusLabelDb` | Battery status types |
| `CustomFieldDb` | Configurable fields for batteries |
| `PreferenceDb` | Application settings/preferences |
| `KVStoreDb` | Key-value storage for app state |
| `FieldMappingDb` | Special field mappings |

**Sync Status Tracking**:
- `new` - Newly downloaded from Snipe-IT
- `remote_updated` - Updated from remote server
- `remote_uploaded` - Local changes uploaded to server
- Timestamps: `local_modified_at`, `remote_modified_at`, `last_synced_at`

**Data Transfer Objects** (msgspec Structs):
- `Asset`, `Battery`, `Location`, `StatusLabel`, `CustomField`
- `User`, `Company`, `Department`, `Manufacturer`
- Optimized serialization with msgspec (JSON/MessagePack)

### 4. Synchronization Engine (`sync.py`)

**Purpose**: Bi-directional sync between local database and Snipe-IT

**Key Function**: `download_hardware_changes()`
1. Fetches assets from Snipe-IT (filtered by battery model ID)
2. Downloads custom fields, locations, status labels
3. Processes location hierarchy (parent-child relationships)
4. Detects local changes and prevents overwrite
5. Queues modified batteries for upload

**Conflict Resolution**:
- Compares `local_modified_at` vs `remote_modified_at`
- Prioritizes local changes over remote updates
- Flags conflicts with `sync_status`

### 5. Helper Functions (`helpers.py`)

**Snipe-IT Integration**:
- `snipe_it_get()` - Synchronous GET requests
- `snipe_it_get_async()` - Async GET with httpx
- `snipe_it_put_async()` - Async PUT for updates
- `fetch_all()` - Paginated data fetching with concurrency control

**Utilities**:
- `ping()` - Network connectivity checks

### 6. Preferences System (`preferences.py`)

**Purpose**: Centralized configuration management

**Functions**:
- `get_preference(key)` - Retrieve setting value
- `set_preference(key, value)` - Update/create setting
- `load_settings_from_config()` - Initialize from `config.json`

**Common Preferences**:
- `snipe-api-key` - Authentication for Snipe-IT
- `snipe-url` - Snipe-IT server base URL
- `battery-model-id` - Filter for battery assets
- `tba-api-key` - The Blue Alliance API key (for match scheduling)

### 7. The Blue Alliance Integration (`tba.py`)

**Purpose**: Fetch FRC competition data

**Status**: Partially implemented
- `get_team(team_key)` - Get team information
- `tba_request(endpoint)` - Generic TBA API calls

**Planned Features**:
- Match schedule sync
- Battery allocation based on match timeline

### 8. Hardware Reader (`reader.py`)

**Purpose**: I2C hardware integration for automated tracking

**Component**: TCA9548A I2C multiplexer support

**Status**: Prototype/experimental
- Intended for automatic battery location detection
- NFC tag registration support in API

---

## Database Schema

### Entity Relationships

```
UserDb (authentication)

BatteryDb
  ├─ location_id → LocationDb.id
  └─ Custom fields (stored in remote_data blob)

LocationDb (self-referential)
  └─ parent_id → LocationDb.id

StatusLabelDb (status types)

CustomFieldDb (field definitions)
  └─ config (HIDE/DISPLAY/EDIT)

PreferenceDb (key-value settings)

FieldMappingDb (special field mappings)
  └─ db_column_name
```

### Custom Fields Configuration

Each custom field has a `config` enum:
- `HIDE` - Not displayed to users
- `DISPLAY` - Read-only display
- `EDIT` - User-editable field

---

## Frontend Structure

### Templates (Jinja2)

| Template | Purpose |
|----------|---------|
| `layout.html` | Base template with navigation, CSP nonces |
| `index.html` | Homepage with recommended batteries |
| `list_view.html` | Tabular battery listing |
| `grid_view.html` | Card-based battery display |
| `settings.html` | Admin configuration interface |
| `login.html` / `register.html` | Authentication forms |
| `modals.html` | Reusable modal dialogs |
| `load_matches.html` | Match schedule viewer (planned) |

### Static Assets

**JavaScript**:
- `qr_reader.js` - QR code scanning implementation
- `sync.js` - Frontend sync status polling
- `chart.umd.min.js` - Charting library
- `d3.min.js` - Data visualization

**Stylesheets**:
- `bootstrap.min.css` - UI framework
- `bootstrap-icons.min.css` - Icons
- `styles.css` - Custom styles

---

## Key Workflows

### 1. Sync Workflow

```
1. RQ Scheduler triggers sync.download_hardware_changes() every 5 minutes
2. Fetch assets from Snipe-IT API (filtered by model_id)
3. Fetch custom fields, locations, status labels
4. For each entity:
   a. Check if exists in local DB
   b. If new → Create with sync_status="new"
   c. If exists → Compare timestamps
      - Local changes detected? Queue for upload
      - Remote newer? Update local copy
5. Batch upload modified assets to Snipe-IT
```

### 2. QR Code Scan Workflow

```
1. User scans QR code via html5-qrcode (qr_reader.js)
2. Frontend sends code to POST /api/qr_scan
3. API parses QR data:
   - URL format: /hardware/{id} or /location/{id}
   - Numeric: Battery ID
4. Return battery details from BatteryDb
5. Display in frontend modal/view
```

### 3. Settings Update Workflow

```
1. User navigates to /settings (requires authentication)
2. Load current preferences from PreferenceDb
3. Display custom fields with HIDE/DISPLAY/EDIT toggles
4. Display locations with "allowed" checkboxes
5. Display status labels with "allowed" checkboxes
6. On submit (POST /settings):
   a. Update preferences
   b. Update field configs
   c. Update allowed locations/statuses
   d. Commit to database
```

---

## Configuration Files

### `config.json`

Structured settings template loaded into database:
```json
[
  {
    "section": "Snipe-IT Integration",
    "settings": [
      {"id": "snipe-url", "name": "Snipe-IT URL", "value": ""},
      {"id": "snipe-api-key", "name": "API Key", "value": ""}
    ]
  }
]
```

### `.env` (Environment Variables)

Required variables:
- `DATABASE_URL` - SQLAlchemy connection string
- `REDIS_HOST` - Redis server hostname
- `REDIS_PORT` - Redis port (default 6379)
- `FLASK_SECRET_KEY` - Session encryption key

### `Dockerfile`

Containerization support for deployment

---

## Security Features

### Authentication
- Password hashing with Werkzeug's `generate_password_hash()`
- Session-based authentication stored in Redis
- User registration with password confirmation

### CSRF Protection
- Flask-SeaSurf generates CSRF tokens
- Tokens required for all POST requests

### Content Security Policy
- Flask-Talisman enforces CSP headers
- Nonces for inline scripts/styles
- Restricts resource loading to trusted sources

### Session Security
- Redis-backed sessions (server-side storage)
- `no-cache` headers on all responses
- Secure session cookies

---

## Background Jobs (Redis Queue)

### Scheduled Jobs

| Job | Interval | Function |
|-----|----------|----------|
| Ping check | 60s | `helpers.ping()` |
| Snipe-IT sync | 300s (5min) | `sync.download_hardware_changes()` |

### Job Management
- Jobs tracked in Redis with unique IDs
- Job status stored in `KVStoreDb` (e.g., `last_sync_job_id`)
- Status checks via `/api/sync` endpoint
- RQ Dashboard available for monitoring (`rq-dashboard` package)

---

## API Reference

### Sync Status Endpoint

**GET/POST `/api/sync`**

GET Response:
```json
{
  "status": "queued|started|finished|failed"
}
```

POST Response:
```json
{
  "status": "Queued",
  "message": "Sync initiated"
}
```

### QR Scan Endpoint

**POST `/api/qr_scan`**

Request:
```json
{
  "qr_data": "/hardware/123" | "123"
}
```

Response:
```json
{
  "id": 123,
  "name": "Battery #5",
  "asset_tag": "BAT-005",
  "location": {...},
  "status": {...},
  "custom_fields": {...}
}
```

### NFC Tag Registration

**POST `/api/register_tag`**

Request:
```json
{
  "battery_id": 123,
  "tag_id": "A1B2C3D4"
}
```

Response:
```json
{
  "status": "success",
  "message": "Tag registered"
}
```

---

## Development Setup

### Prerequisites
1. Python 3.10+
2. Redis server
3. SQLite (or PostgreSQL for production)
4. Snipe-IT instance with API access

### Installation Steps

```bash
# 1. Install Redis
brew install redis  # macOS
# or apt-get install redis  # Linux

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your settings

# 5. Initialize database
python -c "from app import app; app.app_context().push()"

# 6. Start Redis
redis-server

# 7. Run Flask application
flask run

# 8. (Optional) Run RQ Dashboard
rq-dashboard
```

### Database Initialization

Database tables are automatically created on first run via:
```python
Base.metadata.create_all(engine)
```

---

## Planned Features (TODO)

Based on README and code comments:

1. **Grid View Location Mapping**
   - Visual representation of battery cart
   - Drag-and-drop battery placement

2. **Match Schedule Integration**
   - Sync with The Blue Alliance API
   - Allocate batteries to matches
   - Automated checkout recommendations

3. **Hardware Integration**
   - Automatic location detection via I2C sensors
   - NFC tag reading for check-in/check-out
   - Real-time battery status from hardware

4. **Enhanced Reporting**
   - Battery usage statistics
   - Cycle count tracking
   - Health/degradation metrics

---

## File Structure Summary

```
Battery Manager/
├── app.py                  # Main Flask application
├── api.py                  # REST API blueprint
├── models.py               # SQLAlchemy models & msgspec DTOs
├── helpers.py              # Utility functions & Snipe-IT client
├── sync.py                 # Sync engine
├── preferences.py          # Settings management
├── tba.py                  # The Blue Alliance integration
├── reader.py               # Hardware I2C reader
├── config.json             # Settings template
├── requirements.txt        # Python dependencies
├── Dockerfile              # Container configuration
├── schema.sql              # Database schema reference
├── README.md               # Basic project info
├── TODO                    # Feature backlog
├── templates/              # Jinja2 HTML templates
│   ├── layout.html
│   ├── index.html
│   ├── list_view.html
│   ├── grid_view.html
│   ├── settings.html
│   └── ...
├── static/                 # Frontend assets
│   ├── styles.css
│   ├── qr_reader.js
│   ├── sync.js
│   ├── bootstrap.*
│   ├── chart.umd.min.js
│   └── ...
└── models/                 # (Empty placeholder?)
```

---

## Common Development Tasks

### Adding a New Custom Field

1. Define field in Snipe-IT admin panel
2. Run sync to download field definition
3. Configure field visibility in `/settings`:
   - HIDE - Field not shown
   - DISPLAY - Read-only display
   - EDIT - User can modify

### Modifying Sync Behavior

Edit `sync.py`:
- Adjust sync interval in `api.py` scheduler
- Modify conflict resolution logic in `download_hardware_changes()`
- Add custom field processing rules

### Adding API Endpoints

1. Add route to `api.py` blueprint
2. Implement handler function
3. Update frontend JavaScript to call endpoint
4. Add CSRF exemption if needed: `@csrf.exempt`

### Customizing Views

1. Edit templates in `templates/`
2. Modify CSS in `static/styles.css`
3. Update JavaScript in `static/*.js`
4. Use Bootstrap 5 components for consistency

---

## Troubleshooting

### Sync Not Running
- Check Redis connection: `redis-cli ping`
- Verify RQ Scheduler is active: `rq-dashboard`
- Check logs for API errors

### Authentication Issues
- Verify `FLASK_SECRET_KEY` is set
- Clear Redis sessions: `redis-cli FLUSHALL`
- Check password hashing algorithm

### Snipe-IT Connection Errors
- Verify API key in preferences
- Check Snipe-IT URL format (include `/api/v1`)
- Test connectivity: `curl -H "Authorization: Bearer YOUR_KEY" SNIPE_URL/hardware`

### Database Migration
- Backup database: `cp battery.db battery.db.backup`
- Use SQLAlchemy migrations (Alembic) for schema changes
- Or recreate: `rm battery.db && python app.py`

---

## Contributing Guidelines

### Code Style
- Follow PEP 8 for Python code
- Use type hints where applicable
- Document functions with docstrings

### Testing
- Test sync operations with sample data
- Verify CSRF protection on forms
- Check mobile responsiveness

### Security
- Never commit `.env` file
- Rotate API keys regularly
- Validate user input server-side

---

## Support & Resources

- **Snipe-IT API Docs**: https://snipe-it.readme.io/reference
- **The Blue Alliance API**: https://www.thebluealliance.com/apidocs/v3
- **Flask Documentation**: https://flask.palletsprojects.com/
- **Redis Queue**: https://python-rq.org/

---

*Last Updated: March 12, 2026*
