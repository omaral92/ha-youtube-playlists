# Home Assistant YouTube Playlists

A custom Home Assistant integration + Lovelace card that:

- authenticates to YouTube using Google OAuth2
- finds every playlist whose name starts with `HA`
- loads all videos in those playlists
- displays thumbnails/titles in a dashboard card
- calls `script.function_play_youtube_video` with `video_id` when clicked
- refreshes data every 15 minutes

## Installation

See `INSTALL.md`.

## Card configuration

All HA playlists:

```yaml
type: custom:youtube-playlist-card
columns: 3
```

One playlist by ID:

```yaml
type: custom:youtube-playlist-card
playlist: PLxxxxxxxxxxxxxxxx
columns: 3
```

Multiple playlists by ID or exact title:

```yaml
type: custom:youtube-playlist-card
playlist:
  - PLxxxxxxxxxxxxxxxx
  - HA Music
columns: 3
```

Hide playlist headings:

```yaml
type: custom:youtube-playlist-card
show_playlist_title: false
columns: 4
```
