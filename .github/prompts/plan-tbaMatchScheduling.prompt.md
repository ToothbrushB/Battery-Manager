# Plan: The Blue Alliance Match Scheduling Integration

Integrate TBA API to allow users to view team matches at FRC events and assign batteries to specific matches. Match data syncs every 5 minutes via background job, batteries store match numbers in notes field, and the UI provides tabbed views of upcoming/completed/all matches with event selection from API or manual entry.

## Implementation Steps

### Phase 1: TBA API Client & Data Models (Parallel)

**Step 1.1** - Extend [tba.py](tba.py) with TBA API client functions
- Add `get_team_events(team_key, year)` - Fetch events for team in given year
- Add `get_event_matches(event_key)` - Fetch all matches for an event
- Add `get_team_event_matches(team_key, event_key)` - Fetch team's matches at event
- Update `tba_request()` to use `X-TBA-Auth-Key` header from preferences
- Use async httpx pattern from helpers.py (snipe_it_get_async as template)
- Add error handling for rate limits, network failures

**Step 1.2** - Add TBA data models to [models.py](models.py) (*parallel with 1.1*)
- Create msgspec structs: `Event`, `Match`, `MatchAlliance`, `TeamEventStatus`
- Create database models: `EventDb`, `MatchDb` with timestamps for sync tracking
- Fields for MatchDb: id, key, event_key, comp_level, match_number, set_number, predicted_time, actual_time, red_alliance, blue_alliance, winning_alliance, assigned_battery_id (foreign key), sync_status, last_synced_at
- Fields for EventDb: key, name, event_type, start_date, end_date, year, city, state_prov, country, is_active
- Add relationship: `MatchDb.assigned_battery` → `BatteryDb`

### Phase 2: Background Sync Infrastructure

**Step 2** - Implement TBA sync background job (*depends on 1.1, 1.2*)
- Create new file `tba_sync.py` following sync.py pattern
- Implement `download_match_updates()` function:
  - Get active event key from preferences (tba-event-key)
  - Fetch matches for event via TBA API
  - Compare timestamps to detect match status changes (completed vs upcoming)
  - Update MatchDb records (create new, update existing)
  - Return success/failure status
- Register in [api.py](api.py) with scheduler: `scheduler.schedule(func=download_match_updates, interval=300)` (5 minutes)
- Store job ID in KVStoreDb for status tracking

### Phase 3: API Endpoints

**Step 3** - Add TBA API endpoints to [api.py](api.py) (*depends on 2*)
- `GET /api/tba/events?team_key={key}&year={year}` - Fetch team events from TBA
- `GET /api/tba/matches?event_key={key}` - Fetch matches for event from database (with caching)
- `POST /api/tba/assign_battery` - Assign battery to match
  - Body: `{match_key: str, battery_id: int}`
  - Update `BatteryDb.remote_data` blob to add match_key to Asset.notes
  - Set battery `local_modified_at` to trigger Snipe-IT sync
  - Update `MatchDb.assigned_battery_id`
  - Return updated battery details
- `POST /api/tba/sync` - Manual sync trigger (similar to /api/sync pattern)

### Phase 4: User Interface

**Step 4.1** - Update [app.py](app.py) /load_matches route (*depends on 3*)
- Change to handle GET and POST methods
- GET: Query active event and matches from database, pass to template
- Load available batteries (filtered by allowed statuses/locations)
- Pass context: events (if any), matches, batteries, current team/event from preferences

**Step 4.2** - Build [templates/load_matches.html](templates/load_matches.html) (*depends on 4.1*)
- Event Selection section:
  - Team number input (loads from preferences)
  - Year selector (default to current year)
  - Event dropdown (populated via JavaScript from API)
  - Manual event key input with toggle
  - "Load Matches" button to switch events
- Match Display section (Bootstrap tabs):
  - Tab 1: "Upcoming" - matches with actual_time=null or future, sorted by predicted_time
  - Tab 2: "Completed" - matches with actual_time set, sorted by actual_time DESC
  - Tab 3: "All Matches" - complete list
- Match table columns: Match #, Type (Qual/Playoff), Time, Red Alliance, Blue Alliance, Assigned Battery, Actions
- "Assign Battery" button opens modal for each match
- Batteries should be assignable for all upcoming matches, not just the next one.

**Step 4.3** - Create modal for battery assignment (*parallel with 4.2*)
- Modal shows: Match details (number, time, alliances)
- Battery selector dropdown (filtered by status/location)
- Current assignment displayed if exists
- Submit button triggers API call

**Step 4.4** - Create [static/tba.js](static/tba.js) (*depends on 4.2*)
- `fetchTeamEvents(teamKey, year)` - Call /api/tba/events, populate dropdown
- `loadMatches(eventKey)` - Call /api/tba/matches, render tables in tabs
- `filterMatchesByStatus(matches, status)` - Client-side filtering for tabs
- `assignBattery(matchKey, batteryId)` - POST to /api/tba/assign_battery
- `openAssignmentModal(match)` - Populate modal with match details
- Follow patterns from qr_reader.js (fetch, CSRF, modals) and sync.js (toasts, error handling)

### Phase 5: Settings Integration

**Step 5** - Add team number to settings page (*depends on 4.1*)
- Verify [config.json](config.json) has TBA section (exists: tba-url, tba-api-key, tba-event-key, tba-team-key)
- Update [templates/settings.html](templates/settings.html) if needed to display team key field
- Ensure [preferences.py](preferences.py) loads TBA preferences correctly

## Critical Architecture to Reuse

- **Async API pattern**: [helpers.py snipe_it_get_async()](helpers.py#L144-L160) - Use httpx.AsyncClient for TBA requests
- **Background job**: [api.py scheduler setup](api.py#L11-L18) and [sync.py download_hardware_changes()](sync.py#L15-L80)
- **Job tracking**: [api.py sync endpoint](api.py#L25-L50) with KVStoreDb pattern
- **Battery updates**: [models.py BatteryDb.fromAsset()](models.py#L353) and [sync.py conflict resolution](sync.py#L64-L70)
- **Frontend modals**: [templates/modals.html](templates/modals.html) Bootstrap structure
- **CSRF handling**: [static/sync.js](static/sync.js) window.fetch override with auto-injection

## Critical Files to Modify

1. [tba.py](tba.py) - Complete rewrite with full API client
2. [models.py](models.py) - Add Event/Match structs and Db models (lines 183-250 for structs, 300-400 for Db models)
3. New file: `tba_sync.py` - Background sync job
4. [api.py](api.py) - Add 4 new endpoints + scheduler registration
5. [app.py](app.py) - Update /load_matches route (lines 145-146)
6. [templates/load_matches.html](templates/load_matches.html) - Complete rebuild
7. New file: `static/tba.js` - Frontend logic
8. [preferences.py](preferences.py) - Verify TBA preferences initialization (line 56 FieldMappingDb check)

## Verification Steps

1. **Verify background sync**: Start Redis and RQ worker, check rq-dashboard for TBA sync job running every 5 minutes
2. **Test event loading**: Navigate to /load_matches, enter team number (e.g., "frc254"), select year, verify events populate in dropdown
3. **Test manual event entry**: Toggle manual mode, enter event key (e.g., "2026casd"), verify matches load
4. **Test match tabs**: Click through Upcoming/Completed/All tabs, verify filtering works correctly
5. **Test battery assignment**: 
   - Click "Assign Battery" on match
   - Select battery from dropdown
   - Submit and verify match key appears in battery notes
   - Verify MatchDb.assigned_battery_id is set
6. **Verify Snipe-IT sync**: Wait for next sync cycle (or trigger manually), check Snipe-IT battery notes field contains match key
7. **Test match completion flow**: 
   - Find upcoming match in TBA that completes
   - Wait for sync (5 min)
   - Verify match moves from Upcoming to Completed tab
8. **Test error handling**:
   - Invalid team number → Show error toast
   - Network failure → Display cached data with warning
   - Invalid API key → Clear error message
   - TBA API rate limit → Graceful degradation

## Scope Boundaries

**Included**:
- Single event tracking at a time
- Match-to-battery assignment
- Three-tab match view (upcoming/completed/all)
- Background sync every 5 minutes
- Manual and auto-populated event selection
- Integration with existing Snipe-IT sync for battery notes
- Offline-first architecture (Offline mode with cached data if TBA API is unavailable)


**Excluded**:
- Multi-event tracking simultaneously
- Battery checkout/check-in workflow automation
- Match score display or analysis
- Battery recommendation engine based on usage patterns
- Push notifications for upcoming matches
- Historical match data from previous years (only current year/event)

## Decisions

- **Event selection**: Both dropdown (auto-populated from TBA) and manual text entry toggle
- **Battery usage types**: Use existing Snipe-IT status/custom field system (no new usage type column needed per user feedback)
- **Post-match handling**: Batteries remain assigned until manual check-in; Snipe-IT tracks history
- **Match display**: Three separate tabs for filtering (upcoming/completed/all)
- **Sync frequency**: Every 5 minutes during active events
- **Match data storage**: Local MatchDb cache with timestamps for incremental sync
- **Team configuration**: User-editable team key in settings, stored in PreferenceDb
- **Notes field format**: Store match key (e.g., "2026casd_qm15") in Asset.notes field for traceability and Snipe-IT sync
- **Alliance display**: Show team numbers for red/blue alliances in match table for context

## Further Considerations

1. **Offline mode fallback**: If TBA API is down, should we display cached data with staleness indicator? (Recommendation: Yes, show last_synced_at timestamp)
2. **Battery availability filtering**: Should assignment modal only show batteries at specific locations or with specific status labels? (Recommendation: Yes, filter by allowed locations and statuses from settings)
3. **Match reminder system**: Should the app show alerts for upcoming matches in next 30 minutes? (Recommendation: Yes, add to index.html recommended_batteries section)
