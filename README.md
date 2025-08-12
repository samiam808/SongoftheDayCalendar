# Song of the Day Calendar

This project generates a daily calendar (`.ics` file) featuring songs from a specified Spotify playlist.  
Each day includes the song title, artist, a Spotify link in the description, and a YouTube video link as the main event URL.

## Usage

The calendar file is automatically generated and updated by a scheduled GitHub Actions workflow.

### Calendar Link

You can subscribe to or download the live calendar here:  
[https://samiam808.github.io/SongoftheDayCalendar/song_of_the_day.ics](https://samiam808.github.io/SongoftheDayCalendar/song_of_the_day.ics)

---

## Setup

- Add your Spotify credentials as GitHub secrets: `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET`.
- Add your YouTube API key as GitHub secret: `YOUTUBE_API_KEY`.
- The script runs daily and updates the calendar file in the `docs/` directory.

## Requirements

- Python 3.10+
- Packages: `spotipy`, `icalendar`, `python-dateutil`, `requests`

Install dependencies via:

```bash
pip install -r requirements.txt
