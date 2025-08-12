# main.py
# pip install spotipy icalendar python-dateutil requests
import os
from datetime import date, datetime, timedelta
import uuid
import requests

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from icalendar import Calendar, Event

# CONFIG
PLAYLIST_ID = "77Dvuh1ffwAUINmjRmPfMd"  # your playlist id
START_DATE = date(2024, 8, 7)           # starting date
OUTPATH = "docs/song_of_the_day.ics"
CAL_NAME = "Song of the Day"

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")  # Add to GitHub secrets

if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
    raise SystemExit("Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET in env (or GitHub secrets).")

# Spotify auth
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
    """Try YouTube Data API first, else return search results link."""
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
    # Fallback to YouTube search link
    safe_query = query.replace(" ", "+")
    return f"https://www.youtube.com/results?search_query={safe_query}"

# Fetch playlist tracks
items = get_all_playlist_tracks(sp, PLAYLIST_ID)
tracks = []
for item in items:
    track = item.get("track")
    if not track:
        continue
    track_url = track.get("external_urls", {}).get("spotify")
    title = track.get("name", "Unknown Title")
    artist = ", ".join(a.get("name", "Unknown Artist") for a in track.get("artists", []))
    tracks.append({"title": title, "artist": artist, "url": track_url})

# Load existing calendar if it exists
if os.path.exists(OUTPATH):
    with open(OUTPATH, "rb") as f:
        cal = Calendar.from_ical(f.read())
else:
    cal = Calendar()
    cal.add("prodid", "-//Song of the Day Calendar//example.com//")
    cal.add("version", "2.0")
    cal.add("X-WR-CALNAME", CAL_NAME)

# Build sets of existing events
existing_urls = set()
existing_dates = set()
for comp in cal.walk():
    if comp.name == "VEVENT":
        url = comp.get("url")
        if url:
            existing_urls.add(str(url))
        dt = comp.get("dtstart").dt
        if isinstance(dt, datetime):
            dt = dt.date()
        existing_dates.add(dt)

# Add tracks to calendar
d = START_DATE
added = 0
for t in tracks:
    unique_url = t["url"] if t["url"] else f"missing-spotify-{uuid.uuid4()}"
    if unique_url in existing_urls:
        continue

    while d in existing_dates:
        d += timedelta(days=1)

    ev = Event()
    ev.add("uid", f"{uuid.uuid4()}@songofday")
    ev.add("dtstamp", datetime.utcnow())
    ev.add("dtstart", d)
    ev.add("dtend", d + timedelta(days=1))

    # Summary
    if t["url"]:
        ev.add("summary", f"{t['title']} - {t['artist']}")
    else:
        ev.add("summary", "Missing - Missing")

    # Description
    description = f"{t['artist']}"
    if t["url"]:
        description += f" — Spotify: {t['url']}"
    else:
        description += " — Spotify link missing"

    youtube_url = get_youtube_video_link(t['title'], t['artist'], YOUTUBE_API_KEY)
    if youtube_url:
        description += f"\nYouTube: {youtube_url}"

    ev.add("description", description)
    ev.add("url", t["url"] if t["url"] else "")

    cal.add_component(ev)
    existing_dates.add(d)
    existing_urls.add(unique_url)
    d += timedelta(days=1)
    added += 1

# Save calendar
os.makedirs(os.path.dirname(OUTPATH), exist_ok=True)
with open(OUTPATH, "wb") as f:
    f.write(cal.to_ical())

print(f"Done — added {added} new events to {OUTPATH}")