import dotenv
import os
import requests

dotenv.load_dotenv()

headers = {
    'X-TBA-AUTH-KEY': os.getenv('TBA_API_KEY'),
    'Accept': 'application/json'
}

def get_team(team_key):
    url = f'https://www.thebluealliance.com/api/v3/team/{team_key}'
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        events = response.json()
        return events
    else:
        return None
    
def tba_request(endpoint):
    url = os.getenv('TBA_URL') + endpoint
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        return data
    else:
        return None