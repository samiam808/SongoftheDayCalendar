# main.py
# pip install spotipy icalendar python-dateutil requests
import os
from datetime import date, datetime, timedelta
import uuid
import requests
import hashlib
import re

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from icalendar import Calendar, Event

# CONFIG
PLAYLIST_ID = "77Dvuh1ffwAUINmjRmPfMd"  # your playlist id
START_DATE = date(2022, 8, 6)           # starting date
OUTPATH = "docs/song_of_the_day.ics"
CAL_NAME = "Song of the Day"

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")  # Add this to your GitHub secrets

if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
    raise SystemExit("Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET in env (or GitHub secrets).")

# Spotify client credentials
auth_mgr = SpotifyClientCredentials(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET
)
sp = spotipy.Spotify(auth_manager=auth_mgr, requests_timeout=15)

def get_all_playlist_tracks(sp, playlist_id):
    results = sp.playlist_tracks(playlist_id)
    items = results.get("items", [])
    while results.get("next"):
        results = sp.next(results)
        items.extend(results.get("items", []))
    return items

def get_youtube_video_link(title, artist, api_key):
    """Return direct YouTube video link via API, fallback to search URL."""
    query = f"{title} {artist}"
    if api_key:
        url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "maxResults": 1,
            "key": api_key
        }
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            items = data.get("items")
            if items:
                video_id = items[0]["id"]["videoId"]
                return f"https://www.youtube.com/watch?v={video_id}"
        except Exception as e:
            print(f"Warning: YouTube API request failed for '{query}': {e}")

    # Fallback: YouTube search results page
    return f"https://www.youtube.com/results?search_query={title.replace(' ', '+')}+{artist.replace(' ', '+')}"

def get_unique_id(track):
    """Return a stable unique ID based on Spotify URL or hash of title-artist."""
    if track["url"]:
        return track["url"]
    else:
        unique_str = f"{track['title']} - {track['artist']}"
        return "missing-" + hashlib.md5(unique_str.encode('utf-8')).hexdigest()

# Fetch playlist tracks
items = get_all_playlist_tracks(sp, PLAYLIST_ID)

tracks = []
for item in items:
    track = item.get("track")
    if not track:
        continue
    external_urls = track.get("external_urls", {})
    track_url = external_urls.get("spotify")
    title = track.get("name", "Unknown Title")
    artist = ", ".join([a.get("name", "Unknown Artist") for a in track.get("artists", [])])
    tracks.append({"title": title, "artist": artist, "url": track_url})

# Load existing calendar if exists
if os.path.exists(OUTPATH):
    with open(OUTPATH, "rb") as f:
        cal = Calendar.from_ical(f.read())
else:
    cal = Calendar()
    cal.add("prodid", "-//Song of the Day Calendar//example.com//")
    cal.add("version", "2.0")
    cal.add("X-WR-CALNAME", CAL_NAME)

# Track existing unique IDs and dates to prevent duplicates
existing_ids = set()
existing_dates = set()
for comp in cal.walk():
    if comp.name == "VEVENT":
        dt = comp.get("dtstart").dt
        if isinstance(dt, datetime):
            dt = dt.date()
        existing_dates.add(dt)

        description = comp.get("description")
        summary = comp.get("summary")

        spotify_url = None
        if description:
            desc_str = str(description)
            m = re.search(r"Spotify: (https?://[^\s]+)", desc_str)
            if m:
                spotify_url = m.group(1)

        if spotify_url:
            existing_ids.add(spotify_url)
        elif summary:
            unique_str = str(summary)
            existing_ids.add("missing-" + hashlib.md5(unique_str.encode('utf-8')).hexdigest())

# Add new tracks to calendar
d = START_DATE
added = 0
for t in tracks:
    unique_id = get_unique_id(t)
    if unique_id in existing_ids:
        continue  # Skip duplicates

    while d in existing_dates:
        d += timedelta(days=1)

    ev = Event()
    ev.add("uid", f"{uuid.uuid4()}@songofday")
    ev.add("dtstamp", datetime.utcnow())
    ev.add("dtstart", d)
    ev.add("dtend", d + timedelta(days=1))

    # Summary
    if t["title"] and t["artist"]:
        ev.add("summary", f"{t['title']} - {t['artist']}")
    else:
        ev.add("summary", "Missing - Missing")

    # Description (Spotify link or missing)
    if t["url"]:
        description = f"{t['artist']} — Spotify: {t['url']}"
    else:
        description = f"{t['artist']} — Spotify link missing"

    ev.add("description", description)

    # YouTube link (for URL field only)
    youtube_url = get_youtube_video_link(t['title'], t['artist'], YOUTUBE_API_KEY)
    ev.add("url", youtube_url)

    cal.add_component(ev)
    existing_dates.add(d)
    existing_ids.add(unique_id)
    d += timedelta(days=1)
    added += 1

# Save calendar
os.makedirs(os.path.dirname(OUTPATH), exist_ok=True)
with open(OUTPATH, "wb") as f:
    f.write(cal.to_ical())

print(f"Done — added {added} new events to {OUTPATH}")
