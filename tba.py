import os
import httpx
from preferences import get_preference


headers = {
    'X-TBA-AUTH-KEY': get_preference('tba-api-key'),
    'Accept': 'application/json'
}

def get_team(team_key):
    url = f'https://www.thebluealliance.com/api/v3/team/{team_key}'
    response = httpx.get(url, headers=headers)
    if response.status_code == 200:
        events = response.json()
        return events
    else:
        return None
    
def tba_request(endpoint):
    url = get_preference('tba-url') + endpoint
    response = httpx.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        return data
    else:
        return None