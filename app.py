import os
import subprocess
from datetime import datetime
import sqlalchemy
from models import *
engine = sqlalchemy.create_engine(os.getenv("DATABASE_URL"))
Base.metadata.create_all(engine)
ensure_battery_checkout_columns(engine)
ensure_battery_history_columns(engine)
ensure_tba_match_battery_assignment_table(engine)


import json
from redis import Redis

from flask import Flask, flash, redirect, render_template, request, session
from flask_seasurf import SeaSurf
import flask_session
from flask_talisman import Talisman
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import snipe_it_get, snipe_it_post
from api import api
from preferences import (
    get_preference,
    set_preference,
    load_settings_from_config,
    get_hidden_asset_ids,
)


# Configure application
app = Flask(__name__)
csrf = SeaSurf(app)
app.register_blueprint(api)
app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_REDIS'] = Redis(host=os.getenv("REDIS_HOST", "localhost"), port=os.getenv("REDIS_PORT", 6379))
flask_session.Session(app)

# Talisman setup Source - https://stackoverflow.com/a
# Posted by user21344659
# Retrieved 2026-01-07, License - CC BY-SA 4.0
SELF = "'self'"
csp = {
    "default-src": SELF,
    "img-src": "*",
    "script-src": [
        SELF,
    ],
    "style-src": [
        SELF,
    ],
    "font-src": [
        SELF,
    ],
}

nonce_list = ["default-src", "script-src"]

talisman = Talisman(
    app, content_security_policy=csp, content_security_policy_nonce_in=nonce_list
)

app.secret_key = os.getenv("FLASK_SECRET_KEY")

config = json.load(open("config.json"))

# Initialize settings from config file
load_settings_from_config()


def get_git_describe() -> str:
    """Return repository version string similar to `git describe --dirty`."""
    try:
        output = subprocess.check_output(
            ["git", "describe", "--dirty"],
            cwd=os.path.dirname(os.path.abspath(__file__)),
            stderr=subprocess.DEVNULL,
            text=True,
        )
        value = (output or "").strip()
        return value or "unknown"
    except Exception:
        return "unknown"


@app.context_processor
def inject_build_info():
    return {"git_describe": get_git_describe()}


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
def index():
    hidden_ids = get_hidden_asset_ids()
    tracked_team_keys = get_preference("tba-team-key") or ""

    def format_elapsed(seconds: float) -> str:
        seconds = max(0, int(seconds))
        days, rem = divmod(seconds, 86400)
        hours, rem = divmod(rem, 3600)
        minutes, _ = divmod(rem, 60)
        if days > 0:
            return f"{days}d {hours}h"
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"

    with sqlalchemy.orm.Session(engine) as db_session:
        query = db_session.query(BatteryDb)
        if hidden_ids:
            query = query.filter(BatteryDb.id.notin_(hidden_ids))
        batteries = query.all()

        battery_views: list[BatteryView] = [BatteryView.from_battery_db(b) for b in batteries]
        current_status_by_battery: dict[int, str] = {}
        for battery in battery_views:
            status_name = (
                battery.status_label.name
                if battery.status_label and battery.status_label.name
                else "Unknown"
            )
            current_status_by_battery[battery.id] = status_name

        status_start_ts: dict[int, float] = {}
        histories = (
            db_session.query(BatteryHistoryDb)
            .filter(BatteryHistoryDb.battery_id.in_([b.id for b in battery_views]))
            .order_by(BatteryHistoryDb.battery_id.asc(), BatteryHistoryDb.recorded_at.desc())
            .all()
        ) if battery_views else []

        done_batteries: set[int] = set()
        for entry in histories:
            battery_id = entry.battery_id
            if battery_id in done_batteries:
                continue
            current_status = current_status_by_battery.get(battery_id, "Unknown")
            entry_status = entry.status_name or "Unknown"
            try:
                entry_ts = float(entry.recorded_at) if entry.recorded_at else datetime.now().timestamp()
            except (TypeError, ValueError):
                entry_ts = datetime.now().timestamp()

            if battery_id not in status_start_ts and entry_status == current_status:
                status_start_ts[battery_id] = entry_ts
            elif battery_id in status_start_ts and entry_status != current_status:
                done_batteries.add(battery_id)

        now_ts = datetime.now().timestamp()
        status_columns_map: dict[str, list[dict]] = {}
        for battery in battery_views:
            status_name = current_status_by_battery.get(battery.id, "Unknown")
            start_ts = status_start_ts.get(battery.id)
            if start_ts is None:
                try:
                    start_ts = float(battery.local_modified_at) if battery.local_modified_at else now_ts
                except (TypeError, ValueError):
                    start_ts = now_ts
            elapsed = max(0.0, now_ts - start_ts)
            status_columns_map.setdefault(status_name, []).append(
                {
                    "id": battery.id,
                    "name": battery.name or "Unnamed Battery",
                    "asset_tag": battery.asset_tag or "",
                    "location": battery.location.name if battery.location else "Unassigned",
                    "elapsed_seconds": elapsed,
                    "elapsed_display": format_elapsed(elapsed),
                }
            )

        status_columns = []
        for status_name in sorted(status_columns_map.keys()):
            cards = sorted(
                status_columns_map[status_name],
                key=lambda c: c["elapsed_seconds"],
                reverse=True,
            )
            status_columns.append(
                {
                    "status": status_name,
                    "count": len(cards),
                    "cards": cards,
                }
            )

        return render_template(
            "index.html",
            status_columns=status_columns,
            tracked_team_keys=tracked_team_keys,
        )


@app.route("/list_view", methods=["GET"])
def list_view():
    hidden_ids = get_hidden_asset_ids()
    with engine.connect() as connection:
        query = sqlalchemy.select(BatteryDb)
        if hidden_ids:
            query = query.where(BatteryDb.id.notin_(hidden_ids))
        result = connection.execute(query).fetchall()

    # filter responses based on model id for batteries only

    return render_template(
        "list_view.html", batteries=[BatteryView.from_battery_db(row) for row in result]
    )


@app.route("/history", methods=["GET"])
def history():
    with sqlalchemy.orm.Session(engine) as db_session:
        display_fields = (
            db_session.query(CustomFieldDb)
            .filter(
                CustomFieldDb.config.in_(
                    [CustomFieldConfig.DISPLAY.value, CustomFieldConfig.EDIT.value]
                )
            )
            .order_by(CustomFieldDb.name.asc())
            .all()
        )

        entries = (
            db_session.query(BatteryHistoryDb)
            .order_by(BatteryHistoryDb.recorded_at.desc())
            .limit(200)
            .all()
        )

        entries = list(reversed(entries))

        history_rows = []
        previous_by_battery: dict[int, BatteryHistoryDb] = {}
        for entry in entries:
            timestamp = None
            if entry.recorded_at:
                try:
                    timestamp = datetime.fromtimestamp(float(entry.recorded_at)).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                except (ValueError, TypeError):
                    timestamp = entry.recorded_at

            assignment_change = ""
            previous = previous_by_battery.get(entry.battery_id)
            if previous is not None:
                prev_checkout = previous.checkout_asset_id or ""
                curr_checkout = entry.checkout_asset_id or ""
                prev_location = previous.location_name or ""
                curr_location = entry.location_name or ""

                if prev_checkout != curr_checkout:
                    if curr_checkout:
                        assignment_change = f"Checked out to asset {curr_checkout}"
                    else:
                        location_suffix = f" at {curr_location}" if curr_location else ""
                        assignment_change = f"Checked in{location_suffix}"
                elif prev_location != curr_location and curr_location:
                    assignment_change = f"Moved to location {curr_location}"

            history_rows.append(
                {
                    "id": entry.id,
                    "battery_id": entry.battery_id,
                    "battery_name": entry.name,
                    "asset_tag": entry.asset_tag,
                    "notes": entry.notes,
                    "timestamp": timestamp,
                    "status_name": entry.status_name,
                    "location_name": entry.location_name,
                    "checkout_asset_id": entry.checkout_asset_id,
                    "assignment_change": assignment_change,
                    "custom_fields": entry.custom_field_values(),
                }
            )
            previous_by_battery[entry.battery_id] = entry

    history_rows.reverse()

    return render_template(
        "history.html",
        history_entries=history_rows,
        display_fields=display_fields,
    )


@app.route("/history/clear", methods=["POST"])
def clear_history():
    with sqlalchemy.orm.Session(engine) as db_session:
        db_session.query(BatteryHistoryDb).delete()
        db_session.commit()
    flash("History cleared.", "success")
    return redirect("/history")


@app.route("/settings", methods=["GET", "POST"])
def settings():
    with sqlalchemy.orm.Session(engine) as sql_session:
        existing_fields = sql_session.query(CustomFieldDb).all()
        existing_locations = (
            sql_session.query(LocationDb).where(LocationDb.is_parent == True).all()
        )
        existing_statuses = sql_session.query(StatusLabelDb).all()
        existing_mappings = sql_session.query(FieldMappingDb).all()
        existing_batteries = sql_session.query(BatteryDb).order_by(BatteryDb.name.asc()).all()
        hidden_asset_ids = get_hidden_asset_ids()
        if request.method == "POST":
            for section in config:
                for setting in section["settings"]:
                    new_value = request.form.get(setting["name"])
                    if new_value:
                        set_preference(setting["id"], new_value)
                        setting["value"] = new_value
            for field in existing_fields:
                new_config = request.form.get(f"field_{field.db_column_name}")
                if new_config and new_config != field.config:
                    field.config = new_config
            for location in existing_locations:
                allowed = f"{location.id}" in request.form.getlist('allowed_locations')
                if allowed != location.allowed:
                    location.allowed = allowed
            for status in existing_statuses:
                allowed = f"{status.id}" in request.form.getlist('allowed_statuses')
                if allowed != status.allowed:
                    status.allowed = allowed
            for mapping in existing_mappings:
                column = request.form.get(f"special_{mapping.id}")
                if column and column != mapping.db_column_name:
                    mapping.db_column_name = column

            hidden_assets = request.form.getlist("hidden_assets")
            normalized_hidden = []
            for asset_id in hidden_assets:
                try:
                    normalized_hidden.append(str(int(asset_id)))
                except (TypeError, ValueError):
                    continue
            set_preference("hidden-asset-ids", ",".join(sorted(set(normalized_hidden), key=int)))
            sql_session.commit()
            flash("Settings updated successfully!", "success")
            return redirect("/settings")
        else:
            # Update config with current preference values from database
            for section in config:
                for setting in section["settings"]:
                    current_value = get_preference(setting["id"])
                    if current_value is not None:
                        setting["value"] = current_value
            
            return render_template(
                "settings.html",
                config=config,
                custom_fields=existing_fields,
                locations=existing_locations,
                statuses=existing_statuses,
                mappings=existing_mappings,
                batteries=existing_batteries,
                hidden_asset_ids=hidden_asset_ids,
            )


@app.route("/load_matches", methods=["GET"])
def load_matches():
    from datetime import datetime as dt
    with sqlalchemy.orm.Session(engine) as db_session:
        event_key = get_preference('tba-event-key') or ''
        team_key = get_preference('tba-team-key') or ''
        matches = []
        if event_key and event_key != 'your-event-key-here':
            for m in db_session.query(MatchDb).filter_by(event_key=event_key).all():
                d = m.to_dict()
                assignment_rows = (
                    db_session.query(MatchBatteryAssignmentDb)
                    .filter_by(match_key=m.key)
                    .order_by(MatchBatteryAssignmentDb.sort_order.asc(), MatchBatteryAssignmentDb.id.asc())
                    .all()
                )
                assigned_batteries = []
                for assignment in assignment_rows:
                    battery = db_session.get(BatteryDb, assignment.battery_id)
                    if battery:
                        assigned_batteries.append(
                            {"id": battery.id, "name": battery.name, "asset_tag": battery.asset_tag}
                        )

                if not assigned_batteries and m.assigned_battery_id:
                    battery = db_session.get(BatteryDb, m.assigned_battery_id)
                    if battery:
                        assigned_batteries.append(
                            {"id": battery.id, "name": battery.name, "asset_tag": battery.asset_tag}
                        )

                d['assigned_batteries'] = assigned_batteries
                d['assigned_battery'] = assigned_batteries[0] if assigned_batteries else None
                matches.append(d)
        kv = db_session.get(KVStoreDb, 'last_tba_sync_at')
        last_synced_at = kv.value if kv else None
    return render_template(
        "load_matches.html",
        matches=matches,
        event_key=event_key,
        team_key=team_key,
        current_year=dt.now().year,
        last_synced_at=last_synced_at,
    )


@app.route("/grid_view", methods=["GET"])
def grid_view():
    return render_template("grid_view.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "GET":
        return render_template("register.html")
    else:
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        if not username:
            flash("Must Give Username", "error")
            return render_template("register.html")

        if not password:
            flash("Must Give Password", "error")
            return render_template("register.html")

        if not confirmation:
            flash("Must Give Confirmation", "error")
            return render_template("register.html")

        if password != confirmation:
            flash("Password Do Not Match", "error")
            return render_template("register.html")

        hash = generate_password_hash(password)

        try:
            with sqlalchemy.orm.Session(engine) as db_session:
                db_session.add(UserDb(username=username, password=hash))
                db_session.commit()
                new_user = username
                
        except Exception as e:
            print(e)
            flash("Username already exists", "error")
            return render_template("register.html")
        session["user_id"] = new_user

        return redirect("/")

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            flash("Username is required.", "error")
            return render_template("login.html")

        # Ensure password was submitted
        elif not request.form.get("password"):
            flash("Password is required.", "error")
            return render_template("login.html")

        # Query database for username
        with sqlalchemy.orm.Session(engine) as db_session:
            existing = db_session.get(UserDb, request.form.get("username"))

            # Ensure username exists and password is correct
            if not existing or not check_password_hash(
                existing.password, request.form.get("password")
            ):
                flash("Invalid username and/or password.", "error")
                return render_template("login.html")

            # Remember which user has logged in
            session["user_id"] = existing.username

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


