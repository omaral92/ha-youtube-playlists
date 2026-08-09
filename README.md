# YouTube Playlists for Home Assistant

A custom Home Assistant integration + Lovelace card that pulls in your YouTube
playlists and lets you browse and play videos from a dashboard.

- Authenticates to YouTube via Google OAuth2 (read-only access)
- Imports **all playlists**, or only ones matching a **pattern/prefix** you choose
- Refreshes every 15 minutes
- Optionally runs a Home Assistant **script** whenever new videos appear in a
  tracked playlist
- Ships a **Lovelace card** that shows thumbnails in a grid and calls a script
  with the video ID when clicked
- Card supports **custom titles**, **hiding titles**, and long-title clamping

The card's JS is registered automatically by the integration — there's no
manual "Add Resource" step required.

## Installation

### Via HACS (recommended)

1. HACS → Integrations → ⋮ → Custom repositories → add this repo URL,
   category **Integration**
2. Install **YouTube Playlists**
3. Restart Home Assistant

### Manual

1. Copy `custom_components/youtube_playlists` to
   `/config/custom_components/youtube_playlists`
2. Restart Home Assistant

## Setup

### 1. Create Google OAuth credentials

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create or select a project
3. Enable the **YouTube Data API v3**
4. Go to **APIs & Services → Credentials → Create Credentials → OAuth client ID**
5. Create a **Web application** OAuth client
6. For the authorized redirect URI, use the one Home Assistant shows you
   during the Application Credentials step below — don't guess it. On
   installations using My Home Assistant this is normally
   `https://my.home-assistant.io/redirect/oauth`
7. Copy the **Client ID** and **Client Secret**

### 2. Add the credentials to Home Assistant

**Settings → Devices & Services → Application Credentials** → add a
credential for **YouTube Playlists**, pasting the Client ID/Secret from
above. If the integration doesn't show up yet, restart Home Assistant once
more.

### 3. Add the integration

**Settings → Devices & Services → Add Integration** → search **YouTube
Playlists** → complete the Google login and grant read-only access.

By default this imports playlists whose title starts with `HA`. You can
change this any time — see [Options](#options) below.

## Options

Open **Settings → Devices & Services → YouTube Playlists → Configure**:

| Option | Description |
|---|---|
| **Playlists to import** | `All playlists`, or `Match a pattern / prefix` |
| **Pattern** | Only used in pattern mode. Glob syntax, case-insensitive: `HA*` matches titles starting with "HA"; `*Podcast*` matches titles containing "Podcast" anywhere |
| **Script to run on new videos** | Optional. Pick a `script.*` entity to trigger whenever the coordinator detects new videos in a tracked playlist |

Changing any option reloads the integration automatically — no restart
needed.

### The "new videos" script

If you set a script, it's called with a `new_videos` variable — a list of
dicts, one per new video:

```yaml
- playlist_id: PLxxxxxxxxxxxxxxxx
  playlist_title: HA Music
  id: dQw4w9WgXcQ
  title: Some Video Title
  description: "..."
  thumbnail: https://...
  published_at: "2026-08-01T12:00:00Z"
```

Example script using it:

```yaml
sequence:
  - repeat:
      for_each: "{{ new_videos }}"
      sequence:
        - service: notify.mobile_app
          data:
            message: "New video: {{ repeat.item.title }}"
```

Note: nothing fires on the very first refresh after setup (that just
establishes the baseline) — only videos that appear on later refreshes count
as "new".

## The Lovelace card

Add a Manual card:

```yaml
type: custom:youtube-playlist-card
columns: 3
```

### Options

| Option | Default | Description |
|---|---|---|
| `columns` | `3` | Grid columns |
| `show_playlist_title` | `true` | Show/hide each playlist's heading |
| `show_titles` | `true` | Show/hide video titles under thumbnails |
| `video_titles` | `{}` | Override specific video titles — see below |
| `playlist` | *(all)* | Restrict the card to specific playlists, by ID or exact title |

### Selecting playlists

```yaml
type: custom:youtube-playlist-card
playlist:
  - PLxxxxxxxxxxxxxxxx
  - HA Music
columns: 3
```

### Custom titles / hiding long titles

Long YouTube titles are clamped to 2 lines with a "…" by default, and the
full original title always shows as a tooltip on hover. You can also hide
titles entirely, or override specific ones:

```yaml
type: custom:youtube-playlist-card
show_titles: false        # hide all titles
```

```yaml
type: custom:youtube-playlist-card
video_titles:
  dQw4w9WgXcQ: "Short custom title"          # keyed by video ID (recommended)
  "Some Really Long Original Title": "Nickname"  # or by exact original title
```

### Playing videos

The card calls:

```
script.function_play_youtube_video
```

with `video_id: <YouTube video ID>` when a thumbnail is clicked. Create a
script with that entity ID/name to handle playback however you like (media
player, cast, browser_mod, etc).

## Notes & limitations

- The YouTube Data API has quota limits — this integration refreshes every
  15 minutes to stay well within them.
- The YouTube API does not expose the "Watch later" playlist through
  `playlistItems.list`; only ordinary playlists are supported.
- Requires read-only YouTube access (`youtube.readonly` scope) — this
  integration cannot modify your playlists or account.

## Troubleshooting

- **Card changes don't seem to apply**: the browser caches the card's JS by
  URL. The integration auto-versions the resource using the installed
  version, so bumping the integration version (or a full HA restart after
  editing files manually) plus a hard refresh (Ctrl+Shift+R) should pick up
  changes.
- **"Options have no effect"**: make sure you're editing via **Configure**
  on the integration (Settings → Devices & Services), not the card's own
  YAML — the playlist filter and script are integration-level options; the
  card's `show_titles`/`video_titles`/`columns` are separate, per-card YAML
  options.
- **Setup fails with an OAuth error**: double check the redirect URI in the
  Google Cloud Console matches exactly what Home Assistant showed you during
  setup.