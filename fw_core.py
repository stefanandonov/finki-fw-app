from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import requests

BASE_URL = "http://fw.finki.ukim.mk"
TIMEOUT = 15


def _fetch_by_name(path):
    response = requests.get(f"{BASE_URL}/data/rest/{path}", timeout=TIMEOUT)
    response.raise_for_status()
    return {item['name']: item for item in response.json()}


def fetch_labs():
    return _fetch_by_name("lab")


def fetch_profiles():
    return _fetch_by_name("firewall_profile")


def to_utc_iso(local_dt):
    """Aware (or naive, treated as already UTC) datetime -> `YYYY-MM-DDTHH:MM:SS.000Z`."""
    return local_dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def local_to_utc_iso(date, time, tz_name):
    local_dt = datetime.combine(date, time).replace(tzinfo=ZoneInfo(tz_name))
    return to_utc_iso(local_dt)


def build_payload(name, lab, profile, time_from, time_to):
    """`lab` and `profile` are the full objects returned by the REST endpoints."""
    return {
        "name": name,
        "lab": lab,
        "firewallProfile": profile,
        "timeFrom": time_from,
        "timeTo": time_to,
    }


def create_reservation(token, cookie, payload):
    response = requests.post(
        f"{BASE_URL}/data/rest/reservation",
        json=payload,
        headers={"Authorization": token, "Cookie": cookie},
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    return response
