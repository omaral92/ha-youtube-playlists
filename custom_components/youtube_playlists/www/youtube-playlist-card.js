const REFRESH_MS = 15 * 60 * 1000; // matches the integration's own refresh interval
const RETRY_MS = 30 * 1000;
const TAB_KEY = "youtube-playlist-card:tab";

const PLAY_SVG = `<svg viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>`;
const YT_SVG = `<svg viewBox="0 0 24 24"><path fill="currentColor" d="M21.6 7.2a2.5 2.5 0 0 0-1.8-1.8C18.2 5 12 5 12 5s-6.2 0-7.8.4A2.5 2.5 0 0 0 2.4 7.2 26 26 0 0 0 2 12a26 26 0 0 0 .4 4.8 2.5 2.5 0 0 0 1.8 1.8C5.8 19 12 19 12 19s6.2 0 7.8-.4a2.5 2.5 0 0 0 1.8-1.8A26 26 0 0 0 22 12a26 26 0 0 0-.4-4.8z"/><path fill="#26262c" d="M10 15.2 15.2 12 10 8.8z"/></svg>`;

// The original look: follows the active Home Assistant theme.
const classicStyle = (cols) => `
  <style>
    * { box-sizing: border-box; }
    :host { display:block; }
    .wrap {
      padding: 12px;
    }
    .playlist {
      margin-bottom: 18px;
    }
    details.playlist {
      border-radius: 12px;
      overflow: hidden;
      margin-bottom: 18px;
      background: var(--ha-card-background, var(--card-background-color));
    }
    details.playlist.no-bg {
      background: transparent;
    }
    summary {
      cursor: pointer;
      padding: 0;
      list-style: none;
      outline: none;
      display: block;
      background: var(--ha-card-background, var(--card-background-color));
    }
    details.playlist.no-bg summary {
      background: transparent;
    }
    summary::-webkit-details-marker {
      display: none;
    }
    summary .bubble-container {
      display: flex;
      align-items: center;
      width: 100%;
      min-width: 0;
      min-height: 56px;
      padding: 8px 10px;
      gap: 10px;
    }
    summary .bubble-icon {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      flex: 0 0 auto;
      width: 24px;
      height: 24px;
      color: var(--primary-text-color);
      --mdc-icon-size: 24px;
    }
    summary .bubble-name {
      flex: 0 1 auto;
      min-width: 0;
      margin: 0;
      font-size: 16px;
      font-weight: 600;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    summary .bubble-line {
      flex: 1 1 auto;
      min-width: 12px;
      height: 3px;
      border-radius: 3px;
      margin: 0 4px;
      background-color: rgba(var(--rgb-primary-text-color, 0, 0, 0), 0.15);
    }
    summary .bubble-toggle {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      flex: 0 0 auto;
      width: 36px;
      height: 36px;
      border-radius: 999px;
      background: rgba(var(--rgb-primary-text-color, 0, 0, 0), 0.05);
      color: var(--secondary-text-color);
      transition: transform .2s ease;
    }
    details[open] summary .bubble-toggle {
      transform: rotate(180deg);
    }
    .playlist-title {
      font-size: 1.15rem;
      font-weight: 600;
      margin: 0 0 10px 4px;
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(${cols}, minmax(0, 1fr));
      gap: 10px;
      padding: 0;
    }
    .video {
      position: relative;
      cursor: pointer;
      overflow: hidden;
      border-radius: 12px;
      background: var(--ha-card-background, var(--card-background-color));
      box-shadow: var(--ha-card-box-shadow, 0 1px 3px rgba(0,0,0,.25));
      border: 0;
      color: var(--primary-text-color);
      text-align: left;
      padding: 0;
      font: inherit;
      transform: scale(1);
      transition: transform .18s cubic-bezier(.4,0,.2,1);
      -webkit-tap-highlight-color: transparent;
    }
    .video:active {
      transform: scale(.95);
    }
    .video.is-active {
      animation: video-ring .7s cubic-bezier(.2,.7,.3,1);
    }
    @keyframes video-ring {
      0% {
        box-shadow: 0 0 0 0 rgba(var(--rgb-primary-color, 3, 169, 244), .55);
      }
      100% {
        box-shadow: 0 0 0 14px rgba(var(--rgb-primary-color, 3, 169, 244), 0);
      }
    }
    .video-overlay {
      position: absolute;
      inset: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      background: rgba(0, 0, 0, .32);
      backdrop-filter: blur(3px);
      -webkit-backdrop-filter: blur(3px);
      opacity: 0;
      pointer-events: none;
    }
    .video.is-active .video-overlay {
      animation: video-overlay-fade .85s ease forwards;
    }
    @keyframes video-overlay-fade {
      0%   { opacity: 0; }
      18%  { opacity: 1; }
      70%  { opacity: 1; }
      100% { opacity: 0; }
    }
    .video-overlay .play-icon {
      width: 38px;
      height: 38px;
      color: #fff;
      filter: drop-shadow(0 1px 4px rgba(0,0,0,.4));
      transform: scale(.4);
      opacity: 0;
    }
    .video.is-active .video-overlay .play-icon {
      animation: video-icon-pop .85s cubic-bezier(.34, 1.56, .64, 1) forwards;
    }
    @keyframes video-icon-pop {
      0%   { transform: scale(.4);  opacity: 0; }
      25%  { transform: scale(1.15); opacity: 1; }
      40%  { transform: scale(1);    opacity: 1; }
      78%  { transform: scale(1);    opacity: 1; }
      100% { transform: scale(1);    opacity: 0; }
    }
    .thumb {
      width: 100%;
      aspect-ratio: 16 / 9;
      object-fit: cover;
      display:block;
      background: var(--secondary-background-color);
    }
    .title {
      display: -webkit-box;
      -webkit-box-orient: vertical;
      -webkit-line-clamp: 2;
      overflow: hidden;
      padding: 9px;
      line-height: 1.25;
      font-size: .95rem;
    }
    .video.no-title .thumb {
      border-radius: 12px;
    }
    .video.is-playing {
      box-shadow: 0 0 0 2px var(--primary-color, #03a9f4);
    }
    .video.is-playing::after {
      content: "";
      position: absolute;
      top: 7px;
      right: 7px;
      width: 9px;
      height: 9px;
      border-radius: 50%;
      background: var(--primary-color, #03a9f4);
      z-index: 2;
      animation: video-playing-pulse 1.6s ease-out infinite;
    }
    .video.is-paused {
      box-shadow: 0 0 0 2px var(--secondary-text-color, #9e9e9e);
    }
    .video.is-paused::after {
      content: "";
      position: absolute;
      top: 7px;
      right: 7px;
      width: 9px;
      height: 9px;
      border-radius: 50%;
      background: var(--secondary-text-color, #9e9e9e);
      z-index: 2;
    }
    @keyframes video-playing-pulse {
      0%   { box-shadow: 0 0 0 0 rgba(var(--rgb-primary-color, 3, 169, 244), .6); }
      70%  { box-shadow: 0 0 0 7px rgba(var(--rgb-primary-color, 3, 169, 244), 0); }
      100% { box-shadow: 0 0 0 0 rgba(var(--rgb-primary-color, 3, 169, 244), 0); }
    }
    .skeleton-thumb, .skeleton-title {
      background: linear-gradient(
        100deg,
        rgba(var(--rgb-primary-text-color, 0, 0, 0), .06) 30%,
        rgba(var(--rgb-primary-text-color, 0, 0, 0), .14) 50%,
        rgba(var(--rgb-primary-text-color, 0, 0, 0), .06) 70%
      );
      background-size: 200% 100%;
      animation: skeleton-shimmer 1.4s ease-in-out infinite;
    }
    .skeleton {
      border-radius: 12px;
      overflow: hidden;
      background: var(--ha-card-background, var(--card-background-color));
      box-shadow: var(--ha-card-box-shadow, 0 1px 3px rgba(0,0,0,.25));
    }
    .skeleton-thumb {
      width: 100%;
      aspect-ratio: 16 / 9;
    }
    .skeleton-title {
      height: 12px;
      margin: 10px 9px 12px;
      border-radius: 4px;
    }
    @keyframes skeleton-shimmer {
      0%   { background-position: 200% 0; }
      100% { background-position: -200% 0; }
    }
    @media (max-width: 600px) {
      .grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    }
  </style>
`;

// The Lumina dashboard look: a dark, self-contained card with playlist tabs and a
// scrolling thumbnail grid. It fills its container's height (the Lumina media page
// gives it a fixed-height column), or set `height:` to cap it on a normal dashboard.
const LUMINA_STYLE = `
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  :host { display: block; height: 100%; }
  button { font: inherit; color: inherit; background: none; border: 0; cursor: pointer; -webkit-tap-highlight-color: transparent; }
  .lum {
    --card: #18181c; --card-2: #1f1f24; --line: rgba(255,255,255,.06); --text: #f3f3f5; --muted: #8d8d96; --dim: #5c5c66;
    --accent: #ff7a2f; --accent-soft: rgba(255,122,47,.16);
    height: 100%; display: flex; flex-direction: column; gap: 16px; padding: 20px; min-height: 0;
    background: linear-gradient(165deg, var(--card-2), var(--card) 60%);
    border: 1px solid var(--line); border-radius: 22px; overflow: hidden;
    color: var(--text); font-family: "DM Sans", system-ui, sans-serif; font-size: 14px; line-height: 1.25;
    -webkit-font-smoothing: antialiased; user-select: none; -webkit-user-select: none;
  }
  .ell { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .hd { display: flex; align-items: center; gap: 12px; min-width: 0; }
  .logo { width: 44px; height: 44px; border-radius: 14px; background: #26262c; display: grid; place-items: center; flex: none; color: #ff5a52; }
  .logo svg { width: 24px; height: 24px; }
  .hdt { flex: 1; min-width: 0; }
  .ttl { font-family: "Sora", "DM Sans", sans-serif; font-size: 16px; font-weight: 400; letter-spacing: .1px; }
  .sub { font-size: 12px; color: var(--muted); display: flex; align-items: center; gap: 6px; min-width: 0; margin-top: 2px; }
  .sub span { min-width: 0; }
  .sub.np { color: var(--text); }
  .pill { font-size: 11px; padding: 4px 9px; border-radius: 99px; background: #2a2a30; color: var(--muted); white-space: nowrap; flex: none; }
  .tabs { display: flex; gap: 4px; background: rgba(255,255,255,.04); border-radius: 12px; padding: 3px; flex: none; overflow-x: auto; scrollbar-width: none; }
  .tabs::-webkit-scrollbar { display: none; }
  .tab { flex: 1 0 auto; display: flex; align-items: center; justify-content: center; gap: 6px; font-size: 12.5px; padding: 7px 12px; border-radius: 9px; color: var(--muted); transition: background .25s, color .25s; }
  .tab.on { background: #2a2a31; color: var(--text); }
  .tab ha-icon { --mdc-icon-size: 15px; display: inline-flex; }
  .tab .live { width: 6px; height: 6px; border-radius: 50%; background: var(--accent); box-shadow: 0 0 6px var(--accent); display: none; }
  .tab.live .live { display: block; }
  .scroll { flex: 1; min-height: 0; overflow-y: auto; margin: -4px -20px -20px; padding: 4px 20px 24px; scrollbar-width: none;
    -webkit-mask-image: linear-gradient(180deg, transparent, #000 6px, #000 calc(100% - 28px), transparent);
            mask-image: linear-gradient(180deg, transparent, #000 6px, #000 calc(100% - 28px), transparent); }
  .scroll::-webkit-scrollbar { display: none; }
  .grid { display: grid; grid-template-columns: repeat(var(--cols, 2), minmax(0, 1fr)); gap: 14px 12px; }
  .grid[hidden] { display: none; }
  .video { display: flex; flex-direction: column; gap: 8px; min-width: 0; text-align: left; transition: transform .18s cubic-bezier(.4,0,.2,1); }
  .video:active { transform: scale(.96); }
  .th { position: relative; display: block; aspect-ratio: 16 / 9; border-radius: 14px; overflow: hidden; background: #232329;
    box-shadow: 0 10px 24px -14px rgba(0,0,0,.8); transition: box-shadow .3s; }
  .th img { width: 100%; height: 100%; object-fit: cover; display: block; }
  .th:after { content: ""; position: absolute; inset: 0; border-radius: inherit; box-shadow: inset 0 0 0 1px rgba(255,255,255,.07); transition: box-shadow .3s; pointer-events: none; }
  .video.is-playing .th { box-shadow: 0 0 0 4px var(--accent-soft), 0 10px 26px -10px rgba(255,122,47,.55); }
  .video.is-playing .th:after { box-shadow: inset 0 0 0 2px var(--accent); }
  .video.is-paused .th:after { box-shadow: inset 0 0 0 2px rgba(255,255,255,.35); }
  .badge { position: absolute; left: 8px; top: 8px; z-index: 1; display: none; align-items: center; gap: 6px; padding: 4px 9px 4px 8px; border-radius: 99px;
    background: rgba(12,12,15,.72); -webkit-backdrop-filter: blur(6px); backdrop-filter: blur(6px); font-size: 11px; }
  .video.is-playing .badge, .video.is-paused .badge { display: inline-flex; }
  .eq { display: inline-flex; gap: 2px; align-items: flex-end; height: 10px; flex: none; }
  .eq i { width: 2px; height: 3px; border-radius: 1px; background: var(--accent); }
  .is-playing .eq i, .sub.playing .eq i { animation: eq 1s ease-in-out infinite; }
  .eq i:nth-child(2) { animation-delay: -.3s !important; } .eq i:nth-child(3) { animation-delay: -.6s !important; }
  .is-paused .eq i, .sub.paused .eq i { background: var(--muted); height: 6px; }
  .ov { position: absolute; inset: 0; z-index: 2; display: grid; place-items: center; background: rgba(0,0,0,.38); opacity: 0; pointer-events: none; }
  .pp { width: 46px; height: 46px; border-radius: 50%; background: var(--accent); color: #fff; display: grid; place-items: center;
    box-shadow: 0 0 0 6px var(--accent-soft), 0 6px 18px rgba(255,122,47,.45); transform: scale(.4); }
  .pp svg { width: 20px; height: 20px; margin-left: 2px; }
  .video.is-active .ov { animation: ov .85s ease forwards; }
  .video.is-active .pp { animation: pop .85s cubic-bezier(.34,1.56,.64,1) forwards; }
  .title { font-size: 12.5px; line-height: 1.3; color: var(--muted); padding: 0 2px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; transition: color .3s; }
  .video.is-playing .title { color: var(--text); }
  .sk .th, .sk .title { background: linear-gradient(100deg, #232329 30%, #2c2c33 50%, #232329 70%); background-size: 200% 100%; animation: shimmer 1.4s ease-in-out infinite; }
  .sk .title { height: 11px; width: 70%; border-radius: 4px; }
  .msg { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 12px; text-align: center; color: var(--muted); font-size: 13px; padding: 20px; }
  .retry { font-size: 12.5px; padding: 8px 16px; border-radius: 12px; background: rgba(255,255,255,.06); color: var(--text); }
  @keyframes eq { 0%, 100% { height: 3px; } 50% { height: 10px; } }
  @keyframes ov { 0% { opacity: 0; } 18%, 70% { opacity: 1; } 100% { opacity: 0; } }
  @keyframes pop { 0% { transform: scale(.4); } 25% { transform: scale(1.15); } 40%, 100% { transform: scale(1); } }
  @keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }
  @media (prefers-reduced-motion: reduce) { *, *:before, *:after { animation-duration: 0s !important; animation-iteration-count: 1 !important; } }
</style>`;

class YouTubePlaylistCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this.config = {};
    this.data = null;
    this._loaded = false;
    this._nowPlayingId = null;
    this._nowPlayingState = null; // "playing" | "paused" | null
    this._optimisticUntil = 0;
    this._clickLockedUntil = 0;
    // One delegated listener, so re-rendering never stacks handlers.
    this.shadowRoot.addEventListener("click", (e) => this._onClick(e));
  }

  setConfig(config) {
    if (!config) throw new Error("Invalid configuration");
    this.config = {
      theme: "classic", // "classic" follows the HA theme; "lumina" matches the Lumina dashboard
      title: "YouTube", // lumina theme header
      height: null, // lumina theme: e.g. "640px" caps the card and scrolls the grid
      columns: config.theme === "lumina" ? 2 : 3,
      show_playlist_title: true,
      show_titles: true,
      collapsible_playlists: false,
      playlist_background: true,
      video_titles: {},
      playlist_titles: {},
      icon: null,
      playlist_icons: {},
      sort: "default",
      playlist_order: [],
      player_entity: null, // e.g. "media_player.living_room_tv" - reports real now-playing state
      ...config,
    };
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._loaded) {
      this._loaded = true;
      this._load();
      return;
    }
    this._syncNowPlaying();
  }

  connectedCallback() {
    // The integration refreshes playlists every 15 minutes; follow it, so a
    // wall tablet that never reloads still picks up new videos.
    if (!this._refreshTimer) this._refreshTimer = setInterval(() => this._hass && this._load(), REFRESH_MS);
  }

  disconnectedCallback() {
    clearInterval(this._refreshTimer);
    this._refreshTimer = null;
    clearTimeout(this._retryTimer);
    this._retryTimer = null;
  }

  get _lumina() {
    return this.config.theme === "lumina";
  }

  _syncNowPlaying() {
    if (!this.config.player_entity || !this.data?.playlists) return;

    // While an optimistic click-flash is active, don't let a stale/lagging
    // entity update flicker the indicator off before Cast actually starts.
    if (Date.now() < this._optimisticUntil) return;

    const { id, state } = this._computeNowPlaying();
    if (id !== this._nowPlayingId || state !== this._nowPlayingState) {
      this._nowPlayingId = id;
      this._nowPlayingState = state;
      this._applyNowPlaying();
    }
  }

  // Matches the configured media_player's current media against the loaded
  // playlist videos, by content id first (exact) then by title (fallback).
  _computeNowPlaying() {
    const entity = this._hass?.states?.[this.config.player_entity];
    if (!entity) return { id: null, state: null };

    const state = entity.state;
    if (state !== "playing" && state !== "paused") return { id: null, state: null };

    const attrs = entity.attributes || {};
    const mediaContentId = attrs.media_content_id;
    const mediaTitle = (attrs.media_title || "").trim();
    if (!mediaContentId && !mediaTitle) return { id: null, state: null };

    for (const playlist of this.data.playlists || []) {
      for (const video of playlist.videos || []) {
        if (mediaContentId && video.id === mediaContentId) return { id: video.id, state };
      }
    }
    if (mediaTitle) {
      for (const playlist of this.data.playlists || []) {
        for (const video of playlist.videos || []) {
          if (video.title && video.title.trim() === mediaTitle) return { id: video.id, state };
        }
      }
    }
    return { id: null, state: null };
  }

  async _load() {
    clearTimeout(this._retryTimer);
    let data;
    try {
      data = await this._hass.callWS({ type: "youtube_playlists/get_data" });
    } catch (err) {
      // Usually Home Assistant still starting up (no data yet): retry shortly.
      // A refresh failing after a good load keeps showing what we have.
      this._retryTimer = setTimeout(() => this._load(), RETRY_MS);
      if (this.data && !this.data.error) return;
      data = { error: err.message || "Unable to load YouTube data" };
    }
    const json = JSON.stringify(data);
    if (json === this._dataJson) return; // unchanged: keep the DOM (and scroll position)
    this._dataJson = json;
    this.data = data;
    if (this.config.player_entity && data.playlists) {
      ({ id: this._nowPlayingId, state: this._nowPlayingState } = this._computeNowPlaying());
    }
    this._render();
  }

  _playlistMatches(playlist) {
    if (!this.config.playlist) return true;
    if (Array.isArray(this.config.playlist)) {
      return this.config.playlist.includes(playlist.id) ||
             this.config.playlist.includes(playlist.title);
    }
    return playlist.id === this.config.playlist ||
           playlist.title === this.config.playlist;
  }

  _sortPlaylists(playlists) {
    const sort = this.config.sort || "default";
    const list = [...playlists];

    switch (sort) {
      case "title_asc":
        return list.sort((a, b) =>
          this._playlistTitle(a).localeCompare(this._playlistTitle(b))
        );
      case "title_desc":
        return list.sort((a, b) =>
          this._playlistTitle(b).localeCompare(this._playlistTitle(a))
        );
      case "video_count_asc":
        return list.sort((a, b) => (a.item_count || 0) - (b.item_count || 0));
      case "video_count_desc":
        return list.sort((a, b) => (b.item_count || 0) - (a.item_count || 0));
      case "custom": {
        const order = this.config.playlist_order || [];
        const rank = (p) => {
          const idIdx = order.indexOf(p.id);
          if (idIdx !== -1) return idIdx;
          const titleIdx = order.indexOf(p.title);
          if (titleIdx !== -1) return titleIdx;
          return order.length; // anything unlisted keeps its relative place, after listed ones
        };
        return list
          .map((p, i) => ({ p, rank: rank(p), i }))
          .sort((a, b) => a.rank - b.rank || a.i - b.i)
          .map((x) => x.p);
      }
      default:
        return list; // "default": whatever order the API/coordinator returned
    }
  }

  _displayTitle(video) {
    const overrides = this.config.video_titles || this.config.videoTitles || {};
    return overrides[video.id] ?? overrides[video.title] ?? video.title;
  }

  _playlistTitle(playlist) {
    const overrides = this.config.playlist_titles || this.config.playlistTitles || {};
    return overrides[playlist.id] ?? overrides[playlist.title] ?? playlist.title;
  }

  _playlistIcon(playlist) {
    const overrides = this.config.playlist_icons || this.config.playlistIcons || {};
    return overrides[playlist.id] ?? overrides[playlist.title] ?? this.config.icon ?? null;
  }

  _escape(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  _playlists() {
    return this._sortPlaylists((this.data?.playlists || []).filter((p) => this._playlistMatches(p)));
  }

  _render() {
    if (this._lumina) this._renderLumina();
    else this._renderClassic();
    this._applyNowPlaying();
  }

  /* ---------- classic theme ---------- */

  _renderClassic() {
    const style = classicStyle(Number(this.config.columns) || 3);

    if (!this.data) {
      const cols = Number(this.config.columns) || 3;
      const skeletonCount = cols * 2;
      const showTitle = this.config.show_titles;
      let skeletonHtml = `<div class="wrap"><div class="grid">`;
      for (let i = 0; i < skeletonCount; i++) {
        skeletonHtml += `<div class="skeleton"><div class="skeleton-thumb"></div>${showTitle ? `<div class="skeleton-title"></div>` : ""}</div>`;
      }
      skeletonHtml += `</div></div>`;
      this.shadowRoot.innerHTML = style + skeletonHtml;
      return;
    }

    if (this.data.error) {
      this.shadowRoot.innerHTML = style + `<div class="wrap">${this._escape(this.data.error)}</div>`;
      return;
    }

    const playlists = this._playlists();
    if (!playlists.length) {
      this.shadowRoot.innerHTML = style + `<div class="wrap">No matching HA playlists found.</div>`;
      return;
    }

    const collapsible = Boolean(this.config.collapsible_playlists);
    let html = style + `<div class="wrap">`;
    for (const playlist of playlists) {
      if (collapsible) {
        const playlistTitle = this._escape(this._playlistTitle(playlist));
        const icon = this._playlistIcon(playlist);
        const iconHtml = icon
          ? `<span class="bubble-icon"><ha-icon icon="${this._escape(icon)}"></ha-icon></span>`
          : "";
        const noBgClass = this.config.playlist_background ? "" : " no-bg";
        html += `<details class="playlist${noBgClass}" open><summary><span class="bubble-container">${iconHtml}<span class="bubble-name">${playlistTitle}</span><span class="bubble-line"></span><span class="bubble-toggle">▾</span></span></summary><div class="grid">`;
      } else {
        html += `<section class="playlist">`;
        if (this.config.show_playlist_title) {
          html += `<div class="playlist-title">${this._escape(this._playlistTitle(playlist))}</div>`;
        }
        html += `<div class="grid">`;
      }

      for (const video of playlist.videos || []) {
        const showTitle = this.config.show_titles;
        html += `
          <button class="video${showTitle ? "" : " no-title"}" data-video-id="${this._escape(video.id)}" title="${this._escape(video.title)}">
            ${video.thumbnail ? `<img class="thumb" loading="lazy" src="${this._escape(video.thumbnail)}">` : `<div class="thumb"></div>`}
            <span class="video-overlay">
              <svg class="play-icon" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>
            </span>
            ${showTitle ? `<span class="title">${this._escape(this._displayTitle(video))}</span>` : ""}
          </button>`;
      }

      html += `</div>`;
      html += collapsible ? `</details>` : `</section>`;
    }
    html += `</div>`;

    this.shadowRoot.innerHTML = html;
  }

  /* ---------- lumina theme ---------- */

  _renderLumina() {
    const c = this.config;
    const frame = (inner) =>
      `${LUMINA_STYLE}<div class="lum" style="--cols:${Number(c.columns) || 2}${c.height ? `;height:${this._escape(c.height)}` : ""}">` +
      `<div class="hd"><i class="logo">${YT_SVG}</i><div class="hdt"><div class="ttl ell">${this._escape(c.title)}</div><div class="sub" id="sub"></div></div><span class="pill" id="count" hidden></span></div>` +
      inner + `</div>`;

    if (!this.data) {
      const tile = `<div class="video sk"><span class="th"></span>${c.show_titles ? `<span class="title"></span>` : ""}</div>`;
      this.shadowRoot.innerHTML = frame(`<div class="scroll"><div class="grid">${tile.repeat((Number(c.columns) || 2) * 3)}</div></div>`);
      return;
    }
    if (this.data.error) {
      this.shadowRoot.innerHTML = frame(`<div class="msg">${this._escape(this.data.error)}<button class="retry" data-retry>Try again</button></div>`);
      return;
    }
    const playlists = this._playlists();
    if (!playlists.length) {
      this.shadowRoot.innerHTML = frame(`<div class="msg">No matching playlists found.</div>`);
      return;
    }

    let saved = null;
    try { saved = localStorage.getItem(TAB_KEY); } catch (_) { /* storage blocked */ }
    if (!playlists.some((p) => p.id === this._tabId)) this._tabId = playlists.some((p) => p.id === saved) ? saved : playlists[0].id;

    const tabs = playlists.length < 2 ? "" : `<div class="tabs">${playlists.map((p) => {
      const icon = this._playlistIcon(p);
      return `<button class="tab" data-tab="${this._escape(p.id)}">${icon ? `<ha-icon icon="${this._escape(icon)}"></ha-icon>` : ""}${this._escape(this._playlistTitle(p))}<i class="live"></i></button>`;
    }).join("")}</div>`;

    const grids = playlists.map((p) => `<div class="grid" data-pl="${this._escape(p.id)}">${(p.videos || []).map((v) => `
      <button class="video" data-video-id="${this._escape(v.id)}" title="${this._escape(v.title)}">
        <span class="th">${v.thumbnail ? `<img loading="lazy" alt="" src="${this._escape(v.thumbnail)}">` : ""}
          <span class="badge"><span class="eq"><i></i><i></i><i></i></span><b></b></span>
          <span class="ov"><span class="pp">${PLAY_SVG}</span></span></span>
        ${c.show_titles ? `<span class="title">${this._escape(this._displayTitle(v))}</span>` : ""}
      </button>`).join("")}</div>`).join("");

    this.shadowRoot.innerHTML = frame(`${tabs}<div class="scroll" id="scroll">${grids}</div>`);
    this._showTab(this._tabId, false);
  }

  _showTab(id, remember = true) {
    this._tabId = id;
    if (remember) { try { localStorage.setItem(TAB_KEY, id); } catch (_) { /* storage blocked */ } }
    const root = this.shadowRoot;
    root.querySelectorAll(".tab").forEach((b) => b.classList.toggle("on", b.dataset.tab === id));
    root.querySelector(".tab.on")?.scrollIntoView({ block: "nearest", inline: "nearest" });
    root.querySelectorAll(".grid[data-pl]").forEach((g) => (g.hidden = g.dataset.pl !== id));
    const scroll = root.getElementById("scroll");
    if (scroll) scroll.scrollTop = 0;
    this._renderHeader();
  }

  // Header: what's playing (from player_entity), else the open playlist's size.
  _renderHeader() {
    const sub = this.shadowRoot.getElementById("sub");
    if (!sub) return;
    const playlists = this._playlists();
    const video = this._nowPlayingId && playlists.flatMap((p) => p.videos || []).find((v) => v.id === this._nowPlayingId);
    const st = video ? this._nowPlayingState : null;
    sub.className = `sub${st ? ` np ${st}` : ""}`;
    sub.innerHTML = video
      ? `<span class="eq"><i></i><i></i><i></i></span><span class="ell">${this._escape(this._displayTitle(video) || video.title)}</span>`
      : `<span class="ell">${playlists.length} playlist${playlists.length === 1 ? "" : "s"} · ${playlists.reduce((n, p) => n + (p.videos || []).length, 0)} videos</span>`;
    const count = this.shadowRoot.getElementById("count"), cur = playlists.find((p) => p.id === this._tabId);
    if (count && cur && playlists.length > 1) {
      count.hidden = false;
      count.textContent = `${(cur.videos || []).length} videos`;
    }
  }

  /* ---------- shared ---------- */

  // Move the now-playing ring/badge without rebuilding the DOM (keeps scroll).
  _applyNowPlaying() {
    const root = this.shadowRoot, id = this._nowPlayingId, paused = this._nowPlayingState === "paused";
    root.querySelectorAll(".video[data-video-id]").forEach((b) => {
      const on = b.dataset.videoId === id;
      b.classList.toggle("is-playing", on && !paused);
      b.classList.toggle("is-paused", on && paused);
      const label = b.querySelector(".badge b");
      if (label) label.textContent = paused ? "Paused" : "Playing";
    });
    root.querySelectorAll(".tab").forEach((t) => {
      const pl = root.querySelector(`.grid[data-pl="${CSS.escape(t.dataset.tab)}"]`);
      t.classList.toggle("live", !!(id && pl?.querySelector(`[data-video-id="${CSS.escape(id)}"]`)));
    });
    if (this._lumina) this._renderHeader();
  }

  _onClick(e) {
    const tab = e.target.closest(".tab");
    if (tab) return this._showTab(tab.dataset.tab);
    if (e.target.closest("[data-retry]")) {
      this.data = null; this._dataJson = null; this._render(); this._load();
      return;
    }
    const button = e.target.closest(".video[data-video-id]");
    if (button) this._play(button);
  }

  _play(button) {
    // Ignore rapid repeat taps (own or on another thumbnail) within the cooldown window.
    const now = Date.now();
    if (now < this._clickLockedUntil) return;
    this._clickLockedUntil = now + 600;

    // Restart the tap animation even on rapid repeat clicks of the same video.
    this.shadowRoot.querySelectorAll(".video.is-active").forEach((b) => {
      if (b !== button) b.classList.remove("is-active");
    });
    button.classList.remove("is-active");
    void button.offsetWidth; // force reflow so the animation can re-trigger
    button.classList.add("is-active");
    setTimeout(() => button.classList.remove("is-active"), 900);

    // Move the "now playing" indicator to this thumbnail (optimistic —
    // the real media_player state will confirm/correct it shortly).
    const videoId = button.dataset.videoId;
    this._nowPlayingId = videoId;
    this._nowPlayingState = "playing";
    this._optimisticUntil = Date.now() + 4000;
    this._applyNowPlaying();
    this._hass.callService("youtube_playlists", "play_video", {
      video_id: videoId,
    });
  }

  getCardSize() {
    return this._lumina ? 8 : 4;
  }
}

// Guard against a duplicate define(), which throws and would otherwise stop
// the whole script (breaking the last card in the file too). This can
// legitimately happen if a user also added this URL manually as a Lovelace
// resource on top of the integration's own automatic registration.
if (!customElements.get("youtube-playlist-card")) {
  customElements.define("youtube-playlist-card", YouTubePlaylistCard);
}
