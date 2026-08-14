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
      show_titles: true,
      collapsible_playlists: false,
      playlist_background: true,
      video_titles: {},
      playlist_titles: {},
      icon: null,
      playlist_icons: {},
      sort: "default",
      playlist_order: [],
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
          <button class="video${showTitle ? "" : " no-title"}" data-video-id="${this._escape(video.id)}" title="${this._escape(video.title)}">
            ${video.thumbnail ? `<img class="thumb" loading="lazy" src="${this._escape(video.thumbnail)}">` : `<div class="thumb"></div>`}
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
        const videoId = button.dataset.videoId;
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