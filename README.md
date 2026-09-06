<p align="center">
  <img src="icon/icon.png" width="360" alt="Youtube-Playlist">
</p>

<h1 align="center">YouTube Playlists for Home Assistant</h1>

<p align="center">
  A custom Home Assistant integration + Lovelace card that pulls in your YouTube
  playlists and lets you browse and play videos from a dashboard.
</p>

---

## Features

- Authenticates to YouTube via Google OAuth2 (read-only access)
- Imports **all playlists**, or only ones matching a **pattern/prefix** you choose
- Refreshes every 15 minutes
- Play videos either by **running a script** you choose, or **directly on an
  Android TV** entity (turns it on, sets volume, launches the video via ADB)
- Ships a **Lovelace card** that shows thumbnails in a grid, with custom
  playlist ordering, MDI icons, collapsible sections, and custom/hidden
  titles

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
change this any time — see [Options](#options) below. You'll also need to
set up playback (script or Android TV) — see
[How videos play](#how-videos-play).

## Options

Open **Settings → Devices & Services → YouTube Playlists → Configure**.
This is a short, two-step flow:

**Step 1 — playlists & playback method**

| Option | Description |
|---|---|
| **Playlists to import** | `All playlists`, or `Match a pattern / prefix` |
| **Pattern** | Only used in pattern mode. Glob syntax, case-insensitive: `HA*` matches titles starting with "HA"; `*Podcast*` matches titles containing "Podcast" anywhere |
| **How to play videos** | `Run a script when a video is clicked`, or `Play directly on a media player entity` |

**Step 2 — depends on what you picked above**

If you chose **Run a script**:

| Option | Description |
|---|---|
| **Script to run** | Required. A `script.*` entity, called with `video_id` when a video is clicked |

If you chose **Play directly on a media player entity**:

| Option | Description |
|---|---|
| **Media player (Android TV only)** | Required. Only Android TV entities set up via the Android TV (ADB) integration are supported |
| **Volume to set before playing** | 0–100%, default 30% |

Changing any option reloads the integration automatically — no restart
needed. Switching between script/media player modes only asks for the
fields relevant to that mode.

### How videos play

**Script mode**: your script is called with a `video_id` variable
(the YouTube video ID) whenever a video is clicked. Handle playback however
you like inside the script — cast, browser_mod, media_player, etc.

```yaml
sequence:
  - service: media_player.play_media
    target:
      entity_id: media_player.living_room
    data:
      media_content_id: "https://www.youtube.com/watch?v={{ video_id }}"
      media_content_type: video
```

**Android TV mode**: no script needed. Clicking a video calls the
integration's own `youtube_playlists.play_video` service, which:

1. Turns the TV on if it's off, and waits for it to wake up
2. Sets the volume to your configured level
3. Waits for the configured profile-picker delay, then confirms the default YouTube profile
4. Launches the video via an ADB intent
   (`am start -a android.intent.action.VIEW -d "https://www.youtube.com/watch?v=<id>"`)

This requires the device to already be set up in Home Assistant via the
**Android TV** integration (the ADB-based one), with ADB debugging enabled
on the device. It does not work with Fire TV, Chromecast, Roku, or any
other `media_player` platform — only Android TV/ADB.

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
| `show_playlist_title` | `true` | Show/hide each playlist's heading (non-collapsible mode) |
| `collapsible_playlists` | `false` | Make each playlist collapsible using an expand/collapse panel |
| `playlist_background` | `true` | Set `false` to make the collapsible panel/header transparent instead of using the card background |
| `show_titles` | `true` | Show/hide video titles under thumbnails |
| `video_titles` | `{}` | Override specific video titles — see below |
| `playlist_titles` | `{}` | Override playlist names, can include emoji |
| `icon` | *(none)* | MDI icon shown next to every playlist heading, e.g. `mdi:book-open-page-variant` (collapsible mode only) |
| `playlist_icons` | `{}` | Per-playlist MDI icon override — see below |
| `sort` | `default` | Playlist order — see below |
| `playlist_order` | `[]` | Explicit order, used when `sort: custom` |
| `playlist` | *(all)* | Restrict the card to specific playlists, by ID or exact title |

### Selecting playlists

```yaml
type: custom:youtube-playlist-card
playlist:
  - PLxxxxxxxxxxxxxxxx
  - HA Music
columns: 3
```

### Sorting playlists

```yaml
type: custom:youtube-playlist-card
sort: title_asc
```

| Value | Behavior |
|---|---|
| `default` | Whatever order the integration returns |
| `title_asc` / `title_desc` | Alphabetical by (display) title |
| `video_count_asc` / `video_count_desc` | By number of videos in the playlist |
| `custom` | Explicit order via `playlist_order` |

```yaml
type: custom:youtube-playlist-card
sort: custom
playlist_order:
  - "Quran"
  - PLxxxxxxxxxxxxxxxx
  - "HA Music"
```

Mix playlist IDs and exact titles freely. Anything not listed is appended at
the end, keeping its original relative order.

### Custom playlist names

Override the playlist heading text with `playlist_titles:`. Works by
playlist ID or by exact original playlist title, and can include emoji.

```yaml
type: custom:youtube-playlist-card
playlist_titles:
  PLxxxxxxxxxxxxxxxx: "📿 Quran"
  "HA Music": "🎶 My Favorites"
columns: 3
```

### Collapsible playlists

```yaml
type: custom:youtube-playlist-card
collapsible_playlists: true
columns: 3
```

Each playlist renders as a native expand/collapse panel, styled like a
[Bubble Card](https://github.com/Clooos/Bubble-Card) separator: an icon,
the title, an extending line, and a chevron toggle.

#### Icons

Set an MDI icon shown next to the title (no background circle — just the
plain icon):

```yaml
type: custom:youtube-playlist-card
collapsible_playlists: true
icon: mdi:book-open-page-variant
```

Per-playlist override, falls back to `icon`, then to no icon at all if
neither is set:

```yaml
playlist_icons:
  PLxxxxxxxxxxxxxxxx: mdi:book-open-page-variant
  "Quran": mdi:mosque
```

#### Transparent background

By default each collapsible playlist panel has a card-style background. Set
`playlist_background: false` to make it blend into the dashboard instead:

```yaml
type: custom:youtube-playlist-card
collapsible_playlists: true
playlist_background: false
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

The card calls the `youtube_playlists.play_video` service with the clicked
video's ID. What happens next depends on the integration's **How to play
videos** option (script or Android TV) — see
[How videos play](#how-videos-play) above.

## Notes & limitations

- The YouTube Data API has quota limits — this integration refreshes every
  15 minutes to stay well within them.
- The YouTube API does not expose the "Watch later" playlist through
  `playlistItems.list`; only ordinary playlists are supported.
- Requires read-only YouTube access (`youtube.readonly` scope) — this
  integration cannot modify your playlists or account.
- Android TV playback mode only works with the ADB-based Android TV
  integration, not Fire TV, Chromecast, or other media_player platforms.

## Troubleshooting

- **Card changes don't seem to apply**: the browser caches the card's JS by
  URL. The integration auto-versions the resource using the installed
  version (`manifest.json`), so bumping the version string after editing
  the card, then hard-refreshing (Ctrl+Shift+R), is required to see
  changes — a Home Assistant restart alone does not clear browser cache.
- **Leftover duplicate resource**: if you previously registered the card
  manually under Settings → Dashboards → Resources (e.g. pointing at
  `/local/youtube-playlist-card.js`), remove that entry now that the
  integration registers it automatically — having both loaded can cause the
  older one to silently win.
- **"Options have no effect"**: make sure you're editing via **Configure**
  on the integration (Settings → Devices & Services), not the card's own
  YAML — the playlist filter and playback method are integration-level
  options; the card's `show_titles`/`video_titles`/`columns`/etc. are
  separate, per-card YAML options.
- **Options form seems to do nothing on Submit**: this usually means an
  unhandled error occurred while advancing the flow. Check
  **Settings → System → Logs** (filter for `youtube_playlists`) for a
  traceback.
- **Setup fails with an OAuth error**: double check the redirect URI in the
  Google Cloud Console matches exactly what Home Assistant showed you during
  setup.