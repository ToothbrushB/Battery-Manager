import os
import dotenv
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology

# Configure application
app = Flask(__name__)

dotenv_file = dotenv.find_dotenv()
dotenv.load_dotenv(dotenv_file)
app.secret_key = os.getenv("FLASK_SECRET_KEY")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

@app.context_processor
def inject_status():
    return {"status": {"name": "Operational", "positive": True, "icon": "check-circle"}}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/list_view", methods=["GET"])
def list_view():
    return render_template("list_view.html")


@app.route("/settings", methods=["GET", "POST"])
def settings():
    config = [
        {
            "legend": "Snipe-IT Settings",
            "settings": [
                {
                    "id": "snipe-url",
                    "name": "snipe-url",
                    "label": "Snipe-IT URL",
                    "type": "text",
                    "value": "https://assets.yourorghere.org/api/v1/",
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
                    "value": "https://www.thebluealliance.com/api/v3",
                },
                {
                    "id": "tba-api-key",
                    "name": "tba-api-key",
                    "label": "TBA API Key",
                    "type": "text",
                    "value": "your-api-key-here",
                }
            ]
        }
    ]
    return render_template("settings.html", config=config)


@app.route("/grid_view", methods=["GET"])
def grid_view():
    return render_template("grid_view.html")
