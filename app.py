import os
import dotenv
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import snipe_it_get, snipe_it_post
from api import api
import sqlite3

connection = sqlite3.connect('database.db', check_same_thread=False)
cursor = connection.cursor()

# Configure application
app = Flask(__name__)
app.register_blueprint(api)

dotenv_file = dotenv.find_dotenv()
dotenv.load_dotenv(dotenv_file)
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

@app.context_processor
def inject_status():
    return {"status": {"name": "Operational", "positive": True, "icon": "check-circle", "network": "Online", "sync": {"name": "Sync Status", "status": "Ok", "icon": "cloud-check", "last_sync": "2024-06-01T12:00:00Z"}}}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/list_view", methods=["GET"])
def list_view():
    (status, resp) = snipe_it_get("/hardware", os.getenv("SNIPE_API_KEY"), os.getenv("SNIPE_URL"), params={"model_id": 1, "limit": 1000})
    if status != 200:
        flash("Error fetching data from Snipe-IT: {}".format(resp), "error")
        
    # filter responses based on model id for batteries only

    return render_template("list_view.html", batteries=resp['rows'])


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



