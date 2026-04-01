import httpx
from preferences import get_preference

TBA_BASE_URL = "https://www.thebluealliance.com/api/v3"
_timeout = httpx.Timeout(30.0, connect=5.0)


def _get_headers():
    return {
        'X-TBA-Auth-Key': get_preference('tba-api-key') or '',
        'Accept': 'application/json',
    }


def tba_request(endpoint: str):
    """Synchronous TBA API GET request."""
    try:
        response = httpx.get(TBA_BASE_URL + endpoint, headers=_get_headers(), timeout=_timeout)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception:
        return None


def get_team(team_key: str):
    """Get team information."""
    return tba_request(f'/team/{team_key}')


def get_team_events(team_key: str, year: int):
    """Fetch events for a team in a given year."""
    return tba_request(f'/team/{team_key}/events/{year}')


def get_event_matches(event_key: str):
    """Fetch all matches for an event."""
    return tba_request(f'/event/{event_key}/matches')


def get_team_event_matches(team_key: str, event_key: str):
    """Fetch a team's matches at a specific event."""
    return tba_request(f'/team/{team_key}/event/{event_key}/matches')