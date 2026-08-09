# Home Assistant YouTube Playlists

A custom Home Assistant integration + Lovelace card that:

- authenticates to YouTube using Google OAuth2
- finds every playlist whose name starts with `HA`
- loads all videos in those playlists
- displays thumbnails and titles in a dashboard card
- calls a custom script you configure and passes `video_id` as a variable when a video is clicked
- optionally runs a custom script when new videos are discovered
- refreshes data every 15 minutes

## Summary

This integration watches YouTube playlists for new videos, exposes those videos in a Lovelace card, and can notify Home Assistant by calling a custom script when new playlist videos appear.

## Notification script

You can set a custom script in the integration options. The chosen script entity will be called whenever new videos are detected, and it receives a `new_videos` variable containing the new video data.

Example:

1. Open the integration entry in Home Assistant.
2. Choose `Options`.
3. Select a script entity, such as `script.notify_new_youtube_videos`.

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

Hide all video titles or override long titles with custom text:

```yaml
type: custom:youtube-playlist-card
show_titles: false          # hide all titles entirely
video_titles:                # override specific long titles
  dQw4w9WgXcQ: "Short custom title"     # keyed by video id, or
  "Some Really Long Original YouTube Title Here": "My Nickname"  # or by exact original title
```
