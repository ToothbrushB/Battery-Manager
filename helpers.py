import requests

from flask import redirect, render_template, session
from functools import wraps

def snipe_it_get(endpoint, api_key, snipe_url):
    headers = {
        "accept": "application/json",
        "Authorization": "Bearer " + api_key,
        "Accept": "application/json"
    }
    response = requests.get(snipe_url + endpoint, headers=headers)
    return (response.status_code, response.json())

def snipe_it_post(endpoint, api_key, snipe_url, data):
    headers = {
        "accept": "application/json",
        "Authorization": "Bearer " + api_key,
        "Accept": "application/json"
    }
    response = requests.post(snipe_url + endpoint, headers=headers, json=data)
    return (response.status_code, response.json())


def apology(message, code=400):
    """Render message as an apology to user."""

    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [
            ("-", "--"),
            (" ", "-"),
            ("_", "__"),
            ("?", "~q"),
            ("%", "~p"),
            ("#", "~h"),
            ("/", "~s"),
            ('"', "''"),
        ]:
            s = s.replace(old, new)
        return s

    return render_template("apology.html", top=code, bottom=escape(message)), code

