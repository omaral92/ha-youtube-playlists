class YouTubePlaylistCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this.config = {};
    this.data = null;
    this._loaded = false;
  }

  setConfig(config) {
    if (!config) throw new Error("Invalid configuration");
    this.config = {
      columns: 3,
      show_playlist_title: true,
      ...config,
    };
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._loaded) {
      this._loaded = true;
      this._load();
    }
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
        :host { display:block; }
        .wrap {
          padding: 12px;
        }
        .playlist {
          margin-bottom: 18px;
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
        }
        .video {
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
        }
        .thumb {
          width: 100%;
          aspect-ratio: 16 / 9;
          object-fit: cover;
          display:block;
          background: var(--secondary-background-color);
        }
        .title {
          display:block;
          padding: 9px;
          line-height: 1.25;
          font-size: .95rem;
        }
        @media (max-width: 600px) {
          .grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        }
      </style>
    `;

    if (!this.data) {
      this.shadowRoot.innerHTML = style + `<div class="wrap">Loading YouTube…</div>`;
      return;
    }

    if (this.data.error) {
      this.shadowRoot.innerHTML = style + `<div class="wrap">${this._escape(this.data.error)}</div>`;
      return;
    }

    const playlists = (this.data.playlists || []).filter(p => this._playlistMatches(p));
    if (!playlists.length) {
      this.shadowRoot.innerHTML = style + `<div class="wrap">No matching HA playlists found.</div>`;
      return;
    }

    let html = style + `<div class="wrap">`;
    for (const playlist of playlists) {
      html += `<section class="playlist">`;
      if (this.config.show_playlist_title) {
        html += `<div class="playlist-title">${this._escape(playlist.title)}</div>`;
      }
      html += `<div class="grid">`;

      for (const video of playlist.videos || []) {
        html += `
          <button class="video" data-video-id="${this._escape(video.id)}">
            ${video.thumbnail ? `<img class="thumb" loading="lazy" src="${this._escape(video.thumbnail)}">` : `<div class="thumb"></div>`}
            <span class="title">${this._escape(video.title)}</span>
          </button>`;
      }
      html += `</div></section>`;
    }
    html += `</div>`;

    this.shadowRoot.innerHTML = html;

    this.shadowRoot.querySelectorAll(".video").forEach(button => {
      button.addEventListener("click", () => {
        const videoId = button.dataset.videoId;
        this._hass.callService("script", "function_play_youtube_video", {
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
