import httpx
from flask import redirect, render_template, session
from functools import wraps
import os
import dotenv
dotenv_file = dotenv.find_dotenv()
dotenv.load_dotenv(dotenv_file)
timeout = httpx.Timeout(30.0, connect=5.0)
def snipe_it_get(endpoint, api_key=os.getenv("SNIPE_API_KEY"), snipe_url=os.getenv("SNIPE_URL"), params=None):
    headers = {
        "accept": "application/json",
        "Authorization": "Bearer " + api_key,
        "Accept": "application/json"
    }
        
    response = httpx.get(snipe_url + endpoint, headers=headers, params=params, timeout=timeout)
    with open('debug_response.json', 'w') as f:
        f.write(response.text)
    return response

async def snipe_it_get_async(endpoint, api_key=os.getenv("SNIPE_API_KEY"), snipe_url=os.getenv("SNIPE_URL"), client=None, params=None):
    headers = {
        "accept": "application/json",
        "Authorization": "Bearer " + api_key,
        "Accept": "application/json"
    }
    client = client if client is not None else httpx.AsyncClient()
    return await client.get(snipe_url + endpoint, headers=headers, params=params, timeout=timeout)

def snipe_it_post(endpoint, api_key=os.getenv("SNIPE_API_KEY"), snipe_url=os.getenv("SNIPE_URL"), data=None):
    headers = {
        "accept": "application/json",
        "Authorization": "Bearer " + api_key,
        "Accept": "application/json"
    }
    response = httpx.post(snipe_url + endpoint, headers=headers, json=data, timeout=timeout)
    return response

def snipe_it_put(endpoint, api_key=os.getenv("SNIPE_API_KEY"), snipe_url=os.getenv("SNIPE_URL"), data=None):
    headers = {
        "accept": "application/json",
        "Authorization": "Bearer " + api_key,
        "Accept": "application/json"
    }
    response = httpx.put(snipe_url + endpoint, headers=headers, json=data, timeout=timeout)
    return response


def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/latest/patterns/viewdecorators/
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function


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

