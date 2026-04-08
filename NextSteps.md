# Battery Manager Next Steps

## Purpose
This document outlines a practical, prioritized cleanup and refactor plan for the current codebase, aligned with common production best practices for Flask services and modern web applications.

It includes:
- Immediate defects and behavior risks found during code review
- Structural refactors to improve reliability and maintainability
- Security, testing, observability, and delivery improvements
- Suggested execution order so work can be delivered incrementally

## High-Level Assessment
The project has grown significantly in capability (history tracking, checkout/check-in lifecycle, TBA integration, match-to-battery assignments), but most implementation is still monolithic and side-effect heavy. There are concrete runtime defects, API/frontend contract drift, and several reliability/security concerns that should be addressed before adding additional major features.

## Immediate Findings (Prioritized)

### Critical (Fix First)
1. Undefined variable in single battery assignment path
- Evidence: `api.py:651` uses `match_field_mapping_name` in the non-multi assignment path, but it is only set in the multi branch (`api.py:618`).
- Risk: Runtime `NameError` when assigning one battery from the Load Matches flow.
- Fix:
  - Resolve field mapping once before branch logic.
  - Guard against missing mapping and missing custom field in asset payload.

2. Frontend calls non-existent endpoint when loading assignable batteries
- Evidence: `static/tba.js:419` calls `/api/batteries` while backend defines `/api/battery`.
- Risk: Assignment modal cannot load battery options; user-visible failure.
- Fix:
  - Change request path to `/api/battery` or add alias route for backward compatibility.
  - Add API integration tests for all JS-used endpoints.

3. Load Matches JS references DOM nodes that do not exist in template
- Evidence: `static/tba.js:101` assumes `manualEntryToggle`, `eventKeyManual`, and `eventSelect` exist; no such IDs exist in templates.
- Risk: TypeError on button click, breaking match loading flow.
- Fix:
  - Add the missing controls to `templates/load_matches.html` or make JS resilient with null checks and fallback behavior.

4. Incorrect variable updated after successful remote upload
- Evidence: `sync.py:230` sets `existing.sync_status = "remote_uploaded"` inside a loop over `battery`; this likely updates stale variable state.
- Risk: Sync metadata inconsistency and incorrect UI/state reporting.
- Fix:
  - Change to `db_battery.sync_status = "remote_uploaded"`.
  - Add a regression test around local->remote upload status transitions.

### High
5. Authentication decorator is defined but not applied to sensitive routes
- Evidence: `helpers.py` defines `login_required`, but there are no route usages in `app.py`.
- Risk: Settings/history/modification pages can be accessed without login depending on deployment assumptions.
- Fix:
  - Apply `@login_required` to `settings`, `history`, `history/clear`, `load_matches`, and other non-public pages.
  - Add route-level access tests.

6. Import-time side effects create schema and schedule jobs
- Evidence: `app.py`, `api.py`, and `sync.py` run DB setup and scheduler setup at import time.
- Risk: Hard-to-debug startup behavior, duplicate scheduling, test pollution, worker/web process coupling.
- Fix:
  - Introduce app factory pattern (`create_app`) and explicit startup hooks.
  - Move scheduler bootstrap to a dedicated worker entrypoint.

7. Helper defaults evaluate preferences at function definition time
- Evidence: repeated `api_key=get_preference(...)` and `snipe_url=get_preference(...)` defaults in `helpers.py`.
- Risk: stale config values after settings changes until process restart.
- Fix:
  - Replace default args with `None`, resolve preferences inside function body each call.

8. Debug file written on every Snipe-IT GET
- Evidence: `helpers.py:47` writes `debug_response.json` for each `snipe_it_get`.
- Risk: disk churn, accidental data leakage, noisy environments.
- Fix:
  - Remove unconditional write; gate under debug config flag or structured logger at debug level.

### Medium
9. Duplicate model type declaration and incorrect repr
- Evidence: `models.py` defines `Company` twice; `LocationDb.__repr__` references non-existent `email_address`.
- Risk: maintainability and confusion for type/model introspection.
- Fix:
  - Deduplicate `Company` struct.
  - Correct repr fields.

10. Broad exception handling without logging context
- Evidence: broad `except Exception` in `app.py`, `tba.py`, `reader.py`.
- Risk: hidden root causes and difficult incident diagnosis.
- Fix:
  - Catch known exceptions where possible.
  - Log structured context with stack traces.

11. No automated tests in repository
- Evidence: no test files discovered.
- Risk: regressions likely as features evolve.
- Fix:
  - Add unit tests for parser/util logic and integration tests for key API routes.

12. Requirements not version-pinned
- Evidence: `requirements.txt` has unpinned packages.
- Risk: non-reproducible builds and dependency drift.
- Fix:
  - Pin dependencies using `pip-tools` (`requirements.in` + compiled `requirements.txt`).

## Refactor Roadmap

## Phase 0: Stabilization (1-2 days)
1. Fix critical runtime issues (#1-#4 above).
2. Apply minimal auth protections for sensitive pages and mutation endpoints.
3. Remove debug file writes and add baseline structured logging.
4. Add a smoke test script for:
- `/api/status`
- `/api/battery`
- `/api/tba/matches`
- `/api/tba/assign_battery`

Deliverable:
- App runs without obvious UI flow breakages in Load Matches and assignment modal.

## Phase 1: Service Boundaries and App Initialization (2-4 days)
1. Introduce app factory:
- `app/__init__.py` with `create_app(config)`
- Blueprints registered in factory
- Extension initialization isolated (CSRF, session, talisman)
2. Extract startup responsibilities:
- `bootstrap_db.py` for schema checks/migrations
- `bootstrap_scheduler.py` for RQ periodic jobs
3. Remove import-time DB and job side effects from modules.

Deliverable:
- Predictable startup for web, worker, and tests.

## Phase 2: Data and Domain Layer Cleanup (3-5 days)
1. Split large model/data contract file:
- `domain/snipe_types.py` (msgspec structs)
- `db/models.py` (SQLAlchemy models)
- `db/migrations.py` (table/column migration helpers)
2. Add repository/service layer:
- `services/battery_service.py`
- `services/sync_service.py`
- `services/tba_service.py`
3. Normalize timestamps:
- Store numeric or timezone-aware datetime consistently (avoid mixed string/float semantics).

Deliverable:
- Fewer cross-concerns in route handlers, easier testing.

## Phase 3: API Contract Hardening (2-3 days)
1. Define explicit response schemas (Pydantic or msgspec output structs).
2. Standardize endpoint naming (`/api/battery` vs `/api/batteries`).
3. Add validation and defensive handling for missing JSON fields in mutation routes.
4. Version the API if needed (`/api/v1`).

Deliverable:
- Stable API surface for JS clients and future integrations.

## Phase 4: Frontend Reliability and UX Hardening (2-4 days)
1. Remove hidden assumptions in JS DOM selectors.
2. Introduce lightweight frontend module organization:
- `static/js/api-client.js`
- `static/js/views/tba.js`
- `static/js/views/battery-modal.js`
3. Add graceful empty-state and retry behavior for all async operations.
4. Add linting/prettier and CI checks for frontend assets.

Deliverable:
- Fewer runtime JS errors, easier future UI work.

## Phase 5: Security and Operations (2-4 days)
1. Tighten CSP:
- Avoid `img-src *` unless required.
- Keep nonce usage, add explicit origins.
2. Secret management:
- Validate `FLASK_SECRET_KEY` presence on startup; fail fast if missing.
3. Role/permission model:
- Distinguish read-only vs admin actions (settings, history clear, assignments).
4. Observability:
- structured JSON logs
- request IDs
- error tracking hooks
- health endpoints for web/worker dependencies.

Deliverable:
- Better security posture and operational support.

## Coding Standards and Best Practices to Adopt
1. No import-time side effects beyond constants and definitions.
2. Single responsibility per module.
3. No broad catches without logging and re-raise strategy.
4. Typed interfaces for service boundaries.
5. Explicit dependency versions and lock files.
6. CI quality gates:
- formatter (black)
- import sorter (isort)
- linter (ruff)
- type checking (mypy, as practical)
- unit/integration tests.

## Suggested Test Plan

### Unit Tests
1. Preference parsing (`get_allowed_checkout_assets`, `get_hidden_asset_ids`).
2. Sync time formatting and status elapsed calculations.
3. Assignment branch logic and mapping lookups.

### Integration/API Tests
1. Battery read/update with custom fields.
2. Checkout/check-in transitions and cycle count increments.
3. TBA sync and match assignment (single and multi modes).
4. History persistence behavior and clear-history authorization.

### UI Smoke Tests (Playwright or Selenium-lite)
1. Open battery modal from list/home.
2. Load matches and assign battery.
3. Trigger sync and observe status updates.

## Technical Debt Backlog (After Stabilization)
1. Move from ad-hoc schema alteration to Alembic migrations.
2. Introduce domain events for history snapshots instead of route-level direct calls.
3. Add caching strategy for read-heavy endpoints.
4. Introduce background retry/backoff policy for external API calls.
5. Add bounded polling and circuit breaker logic for third-party APIs.

## Proposed Work Breakdown by Sprint

### Sprint 1
1. Critical defects and auth hardening.
2. Logging cleanup and endpoint contract fixes.
3. Basic integration tests for key flows.

### Sprint 2
1. App factory and startup refactor.
2. Service-layer extraction and model split.
3. CI pipeline quality checks.

### Sprint 3
1. Security tightening and role model.
2. Frontend module cleanup and resilience improvements.
3. Observability and operational runbooks.

## Acceptance Criteria for Cleanup Initiative
1. No known critical/high runtime defects from this review remain.
2. Assignment flows (single/multi) work end-to-end from UI.
3. Auth guards in place for admin/sensitive workflows.
4. All major API routes covered by automated integration tests.
5. Startup path is deterministic and free of import-time job creation side effects.
6. Documentation updated and matches shipped behavior.

## Notes
This plan intentionally prioritizes reliability and correctness before broader architecture changes. That order should reduce rework while enabling safer feature development.
