import json
import os
import dotenv
from redis import Redis

dotenv_file = dotenv.find_dotenv()
dotenv.load_dotenv(dotenv_file)

from flask import Flask, flash, redirect, render_template, request, session
from flask_seasurf import SeaSurf
import flask_session
from flask_talisman import Talisman
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import snipe_it_get, snipe_it_post
from api import api
from models import *
import sqlalchemy


engine = sqlalchemy.create_engine(os.getenv("DATABASE_URL"))
Base.metadata.create_all(engine)

# Configure application
app = Flask(__name__)
csrf = SeaSurf(app)
app.register_blueprint(api)
app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_REDIS'] = Redis()
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


def load_settings():
    with sqlalchemy.orm.Session(engine) as session:
        existing_mappings = session.query(FieldMappingDb).all()
        if len(existing_mappings) == 0:
            session.add(FieldMappingDb(
                name="Battery Usage Type",
                db_column_name="",
            ))
            session.add(FieldMappingDb(
                name="Battery Voltage Curve",
                db_column_name="",
            ))
        session.commit()
    for section in config:
        for setting in section["settings"]:
            setting["value"] = os.getenv(setting["id"].upper().replace("-", "_"))


load_settings()


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
def index():
    with sqlalchemy.orm.Session(engine) as db_session:
        recommended_batteries = db_session.query(BatteryDb).limit(5).all()
        return render_template("index.html", recommended_batteries=recommended_batteries)


@app.route("/list_view", methods=["GET"])
def list_view():
    with engine.connect() as connection:
        query = sqlalchemy.select(BatteryDb)
        result = connection.execute(query).fetchall()

    # filter responses based on model id for batteries only

    return render_template(
        "list_view.html", batteries=[BatteryView.from_battery_db(row) for row in result]
    )


@app.route("/settings", methods=["GET", "POST"])
def settings():
    with sqlalchemy.orm.Session(engine) as sql_session:
        existing_fields = sql_session.query(CustomFieldDb).all()
        existing_locations = (
            sql_session.query(LocationDb).where(LocationDb.is_parent == True).all()
        )
        existing_statuses = sql_session.query(StatusLabelDb).all()
        existing_mappings = sql_session.query(FieldMappingDb).all()
        if request.method == "POST":
            for section in config:
                for setting in section["settings"]:
                    new_value = request.form.get(setting["name"])
                    if new_value:
                        os.environ[setting["id"].upper().replace("-", "_")] = new_value
                        dotenv.set_key(
                            dotenv_file,
                            setting["id"].upper().replace("-", "_"),
                            new_value,
                        )
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
            sql_session.commit()
            flash("Settings updated successfully!", "success")
            return redirect("/settings")
        else:
            return render_template(
                "settings.html",
                config=config,
                custom_fields=existing_fields,
                locations=existing_locations,
                statuses=existing_statuses,
                mappings=existing_mappings,
            )


@app.route("/load_matches", methods=["GET"])
def load_matches():
    return render_template("load_matches.html")


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


