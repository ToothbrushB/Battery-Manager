import os
import dotenv
dotenv_file = dotenv.find_dotenv()
dotenv.load_dotenv(dotenv_file)

from flask import Flask, flash, redirect, render_template, request, session
from flask_seasurf import SeaSurf
from flask_session import Session
from flask_talisman import Talisman
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import snipe_it_get, snipe_it_post
from api import api
from models import *
import sqlalchemy
engine = sqlalchemy.create_engine(os.getenv("DATABASE_URL"))

# Configure application
app = Flask(__name__)
csrf = SeaSurf(app)
app.register_blueprint(api)
# Talisman setup Source - https://stackoverflow.com/a
# Posted by user21344659
# Retrieved 2026-01-07, License - CC BY-SA 4.0
SELF = "'self'"
csp = {
        'default-src': SELF,
        'img-src': '*',
        'script-src': [SELF,],
        'style-src': [SELF,],
        'font-src': [SELF,],
    }

nonce_list = ['default-src', 'script-src']

talisman = Talisman(app, content_security_policy=csp, content_security_policy_nonce_in=nonce_list)
###

app.secret_key = os.getenv("FLASK_SECRET_KEY")


config = [
        {
            "legend": "Snipe-IT Settings",
            "settings": [
                {
                    "id": "snipe-url",
                    "name": "snipe-url",
                    "label": "Snipe-IT URL",
                    "type": "text",
                    "value": "placeholder-url-here",
                },
                {
                    "id": "snipe-api-key",
                    "name": "snipe-api-key",
                    "label": "Snipe-IT API Key",
                    "type": "text",
                    "value": "your-api-key-here",
                }
            ]
        },
        {
            "legend": "TBA Settings",
            "settings": [
                {
                    "id": "tba-url",
                    "name": "tba-url",
                    "label": "TBA URL",
                    "type": "text",
                    "value": "placeholder-url-here",
                },
                {
                    "id": "tba-api-key",
                    "name": "tba-api-key",
                    "label": "TBA API Key",
                    "type": "text",
                    "value": "your-api-key-here",
                },
                {
                    "id": "tba-event-key",
                    "name": "tba-event-key",
                    "label": "TBA Event Key",
                    "type": "text",
                    "value": "your-event-key-here",
                },
                {
                    "id": "tba-team-key",
                    "name": "tba-team-key",
                    "label": "TBA Team Key",
                    "type": "text",
                    "value": "your-team-key-here",
                }
            ]
        },
        
    ]

def load_settings():
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
    return render_template("index.html")

@app.route("/list_view", methods=["GET"])
def list_view():
    with engine.connect() as connection:
        query = sqlalchemy.select(BatteryDb)
        result = connection.execute(query).fetchall()
        
    # filter responses based on model id for batteries only

    return render_template("list_view.html", batteries=[BatteryView.from_battery_db(row) for row in result])


@app.route("/settings", methods=["GET", "POST"])
def settings():
    if request.method == "POST":
        for section in config:
            for setting in section["settings"]:
                new_value = request.form.get(setting["name"])
                if new_value:
                    os.environ[setting["id"].upper().replace("-", "_")] = new_value
                    dotenv.set_key(dotenv_file, setting["id"].upper().replace("-", "_"), new_value)
                    setting["value"] = new_value
        flash("Settings updated successfully!", "success")
        return redirect("/settings")
    return render_template("settings.html", config=config)

@app.route("/load_matches", methods=["GET"])
def load_matches():
    
    return render_template("load_matches.html")

@app.route("/grid_view", methods=["GET"])
def grid_view():
    return render_template("grid_view.html")

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
        rows = cursor.execute(
            "SELECT * FROM users WHERE username = ?", (request.form.get("username"))
        ).fetchall()

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            flash("Invalid username and/or password.", "error")
            return render_template("login.html")

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

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

