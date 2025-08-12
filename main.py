# main.py
# pip install spotipy icalendar python-dateutil
import os
from datetime import date, datetime, timedelta
import uuid

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from icalendar import Calendar, Event

# CONFIG - edit only if you want a different start date or filenames
PLAYLIST_ID = "77Dvuh1ffwAUINmjRmPfMd"  # your playlist id
START_DATE = date(2022, 8, 6)           # starting date
OUTPATH = "docs/song_of_the_day.ics"
CAL_NAME = "Song of the Day"

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
    raise SystemExit("Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET in env (or GitHub secrets).")

# Spotify client credentials (server-to-server, suitable for public playlists)
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

# Fetch tracks
items = get_all_playlist_tracks(sp, PLAYLIST_ID)

tracks = []
for item in items:
    track = item.get("track")
    if not track:
        continue
    external_urls = track.get("external_urls", {})
    track_url = external_urls.get("spotify")
    if not track_url:
        # Skip tracks without a Spotify URL (e.g., local files)
        continue
    title = track["name"]
    artist = ", ".join([a["name"] for a in track.get("artists", [])])
    tracks.append({"title": title, "artist": artist, "url": track_url})

# Load existing calendar (if any)
if os.path.exists(OUTPATH):
    with open(OUTPATH, "rb") as f:
        cal = Calendar.from_ical(f.read())
else:
    cal = Calendar()
    cal.add("prodid", "-//Song of the Day Calendar//example.com//")
    cal.add("version", "2.0")
    cal.add("X-WR-CALNAME", CAL_NAME)

# Build sets of already scheduled URLs and dates
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

# Add any new tracks to next open day
d = START_DATE
added = 0
for t in tracks:
    if t["url"] in existing_urls:
        continue  # already scheduled
    # find next free date (skip any date already in calendar)
    while d in existing_dates:
        d += timedelta(days=1)
    ev = Event()
    ev.add("uid", f"{uuid.uuid4()}@songofday")
    ev.add("dtstamp", datetime.utcnow())
    ev.add("dtstart", d)
    ev.add("dtend", d + timedelta(days=1))
    # User asked for "Song - Title" format; adjust here if you want "Artist - Title"
    ev.add("summary", f"Song - {t['title']}")
    ev.add("description", f"{t['artist']} — {t['url']}")
    ev.add("url", t["url"])
    cal.add_component(ev)
    existing_dates.add(d)
    existing_urls.add(t["url"])
    d += timedelta(days=1)
    added += 1

# ensure docs/ exists
os.makedirs(os.path.dirname(OUTPATH), exist_ok=True)
with open(OUTPATH, "wb") as f:
    f.write(cal.to_ical())

print(f"Done — added {added} new events to {OUTPATH}")