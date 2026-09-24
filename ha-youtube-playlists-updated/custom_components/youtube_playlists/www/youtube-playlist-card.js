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
  }

  setConfig(config) {
    if (!config) throw new Error("Invalid configuration");
    this.config = {
      columns: 3,
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
    if (!this.config.player_entity || !this.data) return;

    // While an optimistic click-flash is active, don't let a stale/lagging
    // entity update flicker the indicator off before Cast actually starts.
    if (Date.now() < this._optimisticUntil) return;

    const { id, state } = this._computeNowPlaying();
    if (id !== this._nowPlayingId || state !== this._nowPlayingState) {
      this._nowPlayingId = id;
      this._nowPlayingState = state;
      this._render();
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
    try {
      this.data = await this._hass.callWS({
        type: "youtube_playlists/get_data",
      });
      this._render();
    } catch (err) {
      this.data = { error: err.message || "Unable to load YouTube data" };
      this._render();
    }
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

  _render() {
    const style = `
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
          grid-template-columns: repeat(${Number(this.config.columns) || 3}, minmax(0, 1fr));
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

    const playlists = this._sortPlaylists(
      (this.data.playlists || []).filter(p => this._playlistMatches(p))
    );
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
        const displayTitle = this._displayTitle(video);
        const showTitle = this.config.show_titles;
        html += `
          <button class="video${showTitle ? "" : " no-title"}${video.id === this._nowPlayingId ? (this._nowPlayingState === "paused" ? " is-paused" : " is-playing") : ""}" data-video-id="${this._escape(video.id)}" title="${this._escape(video.title)}">
            ${video.thumbnail ? `<img class="thumb" loading="lazy" src="${this._escape(video.thumbnail)}">` : `<div class="thumb"></div>`}
            <span class="video-overlay">
              <svg class="play-icon" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>
            </span>
            ${showTitle ? `<span class="title">${this._escape(displayTitle)}</span>` : ""}
          </button>`;
      }

      html += `</div>`;
      html += collapsible ? `</details>` : `</section>`;
    }
    html += `</div>`;

    this.shadowRoot.innerHTML = html;

    this.shadowRoot.querySelectorAll(".video").forEach(button => {
      button.addEventListener("click", () => {
        // Ignore rapid repeat taps (own or on another thumbnail) within the cooldown window.
        const now = Date.now();
        if (now < this._clickLockedUntil) return;
        this._clickLockedUntil = now + 600;

        // Restart the tap animation even on rapid repeat clicks of the same video.
        this.shadowRoot.querySelectorAll(".video.is-active").forEach(b => {
          if (b !== button) b.classList.remove("is-active");
        });
        button.classList.remove("is-active");
        void button.offsetWidth; // force reflow so the animation can re-trigger
        button.classList.add("is-active");
        button.addEventListener(
          "animationend",
          () => button.classList.remove("is-active"),
          { once: true }
        );

        // Move the "now playing" indicator to this thumbnail (optimistic —
        // the real media_player state will confirm/correct it shortly).
        const previouslyPlaying = this.shadowRoot.querySelector(".video.is-playing, .video.is-paused");
        if (previouslyPlaying && previouslyPlaying !== button) {
          previouslyPlaying.classList.remove("is-playing", "is-paused");
        }
        button.classList.remove("is-paused");
        button.classList.add("is-playing");

        const videoId = button.dataset.videoId;
        this._nowPlayingId = videoId;
        this._nowPlayingState = "playing";
        this._optimisticUntil = Date.now() + 4000;
        this._hass.callService("youtube_playlists", "play_video", {
          video_id: videoId,
        });
      });
    });
  }

  getCardSize() {
    return 4;
  }
}

customElements.define("youtube-playlist-card", YouTubePlaylistCard);