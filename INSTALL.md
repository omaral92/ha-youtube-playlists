# Installation

## 1. Copy the files

Copy the `custom_components/youtube_playlists` folder to:

`/config/custom_components/youtube_playlists`

Copy `www/youtube-playlist-card.js` to:

`/config/www/youtube-playlist-card.js`

Restart Home Assistant after copying.

## 2. Create Google OAuth credentials

Go to:

https://console.cloud.google.com/

Create/select a Google Cloud project.

Enable:

**YouTube Data API v3**

Then open:

**APIs & Services → Credentials → Create Credentials → OAuth client ID**

Create a **Web application** OAuth client.

For the authorized redirect URI, use the OAuth redirect URI shown by Home Assistant's Application Credentials flow. On Home Assistant installations using My Home Assistant, this is normally:

`https://my.home-assistant.io/redirect/oauth`

Do not guess a local callback URL if Home Assistant shows a different one.

Copy the Google Client ID and Client Secret.

## 3. Add Google credentials in Home Assistant

Go to:

**Settings → Devices & services → Application credentials**

Add an application credential for **YouTube Playlists**.

Paste the Google Client ID and Client Secret.

If the integration is not listed yet, restart Home Assistant once more.

## 4. Add the YouTube integration

Go to:

**Settings → Devices & services → Add Integration**

Search for:

**YouTube Playlists**

Start the setup and complete the Google login/consent.

Grant read-only access to YouTube.

The integration automatically discovers playlists whose names start with `HA`.

## 5. Install the dashboard card

The JavaScript file must be available at:

`/config/www/youtube-playlist-card.js`

Then go to:

**Settings → Dashboards → Resources**

Add:

`/local/youtube-playlist-card.js`

Type:

`JavaScript Module`

If your Home Assistant version lets you add resources from the dashboard UI, use that. Alternatively, put the following in the dashboard resources configuration if your setup uses YAML resources:

```yaml
url: /local/youtube-playlist-card.js
type: module
```

## 6. Add the card

Add a Manual card:

```yaml
type: custom:youtube-playlist-card
columns: 3
```

Or select specific playlists:

```yaml
type: custom:youtube-playlist-card
playlist:
  - HA Music
  - HA Videos
columns: 3
```

The card calls:

```yaml
script.function_play_youtube_video
```

with:

```yaml
video_id: <YouTube video ID>
```

## Notes

The YouTube Data API has quota limits. This integration refreshes every 15 minutes to avoid unnecessarily frequent API calls.

The YouTube API does not expose the contents of the user's "Watch later" playlist through `playlistItems.list`; ordinary playlists are supported.
