import base64
import json
import os
import sys
import urllib.parse
import urllib.request
import requests
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

KOALA_URL = "https://api.koala." + os.environ["CANONICAL_HOSTNAME"] + "/activities/"
MAX_ACTIVITIES = 6
MAX_WEEKS_AHEAD = 3
TZ = ZoneInfo("Europe/Amsterdam")

def week_start(arg=None):
    if arg:
        return date.fromisoformat(arg)
    today = datetime.now(TZ).date()
    return today + timedelta(days=(7 - today.weekday()) % 7)

def retrieve_activities():
    req = urllib.request.Request(KOALA_URL, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)

def select(activities, start):
    # The upcoming activities starting Monday, even if they are planned in later weeks,
    # but no later than MAX_WEEKS_AHEAD (to prevent 'save the dates' activities from showing up). 
    end = start + timedelta(weeks=MAX_WEEKS_AHEAD)
    chosen = []
    for a in activities:
        if len(chosen) >= MAX_ACTIVITIES:
            break
        if not a.get("showInKoala", True):
            continue
        activity_start = datetime.fromisoformat(a["dateTimeStart"]).astimezone(TZ)
        if start <= activity_start.date() < end:
            chosen.append((activity_start, a["id"]))
    chosen.sort()
    return [activity_id for _, activity_id in chosen]

def retrieve_poster(activity_id):
    """Returns (content, content_type) or None if the activity has no poster."""
    req = urllib.request.Request(KOALA_URL + str(activity_id) + "/poster")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            content_type = resp.headers.get_content_type()
            return resp.read(), content_type
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        sys.exit(f"Koala error ({e.code}) while fetching poster {activity_id}")