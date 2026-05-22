(() => {
  const data = document.querySelector("#playlist-data");
  if (!data) return;

  const playlist = JSON.parse(data.textContent);
  const tracks = playlist.tracks || [];
  const root = document.querySelector("#music-root");
  const playlistHead = document.querySelector("[data-playlist-head]");
  const grid = document.querySelector("[data-track-grid]");
  const shell = document.querySelector("[data-player-shell]");
  const miniStatus = document.querySelector("[data-mini-status]");
  const audio = document.querySelector("[data-audio]");
  const cover = document.querySelector("[data-now-cover]");
  const miniCover = document.querySelector("[data-mini-cover]");
  const statusCover = document.querySelector("[data-status-cover]");
  const record = document.querySelector("[data-record]");
  const title = document.querySelector("[data-now-title]");
  const miniTitle = document.querySelector("[data-mini-title]");
  const statusTitle = document.querySelector("[data-status-title]");
  const artist = document.querySelector("[data-now-artist]");
  const miniArtist = document.querySelector("[data-mini-artist]");
  const statusArtist = document.querySelector("[data-status-artist]");
  const currentTime = document.querySelector("[data-current-time]");
  const duration = document.querySelector("[data-duration]");
  const seek = document.querySelector("[data-seek]");
  const playToggle = document.querySelector("[data-play-toggle]");
  const lyricList = document.querySelector("[data-lyric-list]");
  const sourceLink = document.querySelector("[data-source-link]");
  const rows = [...document.querySelectorAll(".song-row")];
  let currentIndex = -1;
  let activeLyricIndex = -1;
  let isSeeking = false;
  let minimized = false;

  const formatTime = (seconds) => {
    if (!Number.isFinite(seconds)) return "--:--";
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
  };

  const indexFromHash = () => {
    const match = window.location.hash.match(/^#track-(\d+)$/);
    if (!match) return -1;
    const rank = Number(match[1]);
    return tracks.findIndex((track) => Number(track.rank) === rank);
  };

  const syncRows = (index) => {
    rows.forEach((row) => {
      const active = Number(row.dataset.trackIndex) === index;
      row.classList.toggle("is-active", active);
      row.setAttribute("aria-current", active ? "true" : "false");
    });
  };

  const renderLyrics = (track) => {
    activeLyricIndex = -1;
    const lyricTrack = document.createElement("div");
    lyricTrack.className = "lyric-track";
    const lines = track.lyrics?.length ? track.lyrics : [{ time: 0, text: track.description || track.title }];
    lines.forEach((line) => {
      const item = document.createElement("p");
      item.className = "lyric-line";
      item.dataset.time = String(line.time || 0);
      item.textContent = line.text;
      lyricTrack.appendChild(item);
    });
    lyricList.replaceChildren(lyricTrack);
  };

  const updateLyricPosition = () => {
    const lines = [...lyricList.querySelectorAll(".lyric-line")];
    if (!lines.length) return;
    const nextIndex = lines.reduce((current, line, index) => {
      const time = Number(line.dataset.time || 0);
      return audio.currentTime >= time ? index : current;
    }, 0);
    if (nextIndex === activeLyricIndex) return;
    activeLyricIndex = nextIndex;
    lines.forEach((line, index) => line.classList.toggle("is-active", index === nextIndex));
    const track = lyricList.querySelector(".lyric-track");
    const active = lines[nextIndex];
    if (track && active) {
      track.style.setProperty("--lyric-offset", `${96 - active.offsetTop}px`);
    }
  };

  const setPlayingState = () => {
    const playing = !audio.paused && !audio.ended;
    record.classList.toggle("is-playing", playing);
    playToggle.textContent = playing ? "⏸" : "▶";
  };

  const renderTrack = (track, autoplay) => {
    cover.src = track.cover;
    cover.alt = `${track.title} 封面`;
    miniCover.src = track.cover;
    miniCover.alt = `${track.title} 封面`;
    statusCover.src = track.cover;
    statusCover.alt = `${track.title} 封面`;
    title.textContent = track.title;
    miniTitle.textContent = track.title;
    statusTitle.textContent = track.title;
    artist.textContent = `${track.artist}  ·  ${track.album || "公开音频"}  ·  来源：${track.source_name || "公开来源"}`;
    miniArtist.textContent = track.artist;
    statusArtist.textContent = track.artist;
    duration.textContent = track.duration || "--:--";
    sourceLink.href = track.source_url || track.src;
    sourceLink.textContent = `查看 ${track.source_name || "公开来源"}`;
    renderLyrics(track);
    if (audio.src !== new URL(track.src, window.location.href).href) {
      audio.src = track.src;
      seek.value = "0";
      currentTime.textContent = "00:00";
    }
    if (autoplay) audio.play().catch(() => setPlayingState());
    setPlayingState();
  };

  const openTrack = (index, pushHistory = true, autoplay = true) => {
    const track = tracks[index];
    if (!track) {
      returnToPlaylist(pushHistory);
      return;
    }
    currentIndex = index;
    minimized = false;
    miniStatus.hidden = true;
    playlistHead.hidden = true;
    grid.hidden = true;
    shell.hidden = false;
    renderTrack(track, autoplay);
    syncRows(index);
    if (pushHistory) history.pushState({ trackIndex: index }, "", `#track-${track.rank}`);
    shell.scrollIntoView({ block: "start", behavior: "smooth" });
  };

  function stopAndReturn(pushHistory = true) {
    currentIndex = -1;
    audio.pause();
    audio.removeAttribute("src");
    audio.load();
    minimized = false;
    miniStatus.hidden = true;
    playlistHead.hidden = false;
    grid.hidden = false;
    shell.hidden = true;
    syncRows(-1);
    seek.value = "0";
    currentTime.textContent = "00:00";
    duration.textContent = "--:--";
    setPlayingState();
    if (pushHistory) history.pushState({}, "", window.location.pathname);
    root.scrollIntoView({ block: "start", behavior: "smooth" });
  }

  function minimizePlayer(pushHistory = true) {
    if (currentIndex < 0) {
      stopAndReturn(pushHistory);
      return;
    }
    minimized = true;
    playlistHead.hidden = false;
    grid.hidden = false;
    shell.hidden = true;
    miniStatus.hidden = false;
    syncRows(currentIndex);
    if (pushHistory) history.pushState({ minimized: true, trackIndex: currentIndex }, "", `#track-${tracks[currentIndex].rank}`);
    root.scrollIntoView({ block: "start", behavior: "smooth" });
  }

  document.querySelectorAll(".js-track-link").forEach((entry) => {
    entry.addEventListener("click", (event) => {
      event.preventDefault();
      openTrack(Number(entry.dataset.trackIndex));
    });
  });

  document.querySelectorAll("[data-prev-track]").forEach((button) => {
    button.addEventListener("click", () => {
      if (currentIndex <= 0) stopAndReturn();
      else openTrack(currentIndex - 1);
    });
  });

  document.querySelectorAll("[data-next-track]").forEach((button) => {
    button.addEventListener("click", () => {
      if (currentIndex < 0 || currentIndex >= tracks.length - 1) stopAndReturn();
      else openTrack(currentIndex + 1);
    });
  });

  document.querySelectorAll("[data-back-playlist]").forEach((button) => {
    button.addEventListener("click", () => stopAndReturn());
  });

  document.querySelectorAll("[data-close-player], [data-stop-current]").forEach((button) => {
    button.addEventListener("click", () => stopAndReturn());
  });

  document.querySelectorAll("[data-minimize-player]").forEach((button) => {
    button.addEventListener("click", () => minimizePlayer());
  });

  document.querySelectorAll("[data-open-current]").forEach((button) => {
    button.addEventListener("click", () => {
      if (currentIndex >= 0) openTrack(currentIndex, true, false);
    });
  });

  playToggle.addEventListener("click", () => {
    if (!audio.src && tracks[0]) openTrack(0);
    else if (audio.paused) audio.play().catch(() => setPlayingState());
    else audio.pause();
  });

  audio.addEventListener("play", setPlayingState);
  audio.addEventListener("pause", setPlayingState);
  audio.addEventListener("timeupdate", () => {
    currentTime.textContent = formatTime(audio.currentTime);
    if (!isSeeking && Number.isFinite(audio.duration) && audio.duration > 0) {
      seek.value = String(Math.round((audio.currentTime / audio.duration) * 1000));
    }
    updateLyricPosition();
  });
  audio.addEventListener("loadedmetadata", () => {
    duration.textContent = formatTime(audio.duration);
  });
  audio.addEventListener("ended", () => {
    if (currentIndex >= 0 && currentIndex < tracks.length - 1) openTrack(currentIndex + 1, true, true);
    else setPlayingState();
  });

  seek.addEventListener("input", () => {
    isSeeking = true;
  });
  seek.addEventListener("change", () => {
    if (Number.isFinite(audio.duration) && audio.duration > 0) {
      audio.currentTime = (Number(seek.value) / 1000) * audio.duration;
    }
    isSeeking = false;
  });

  window.addEventListener("popstate", () => {
    const index = indexFromHash();
    if (index >= 0 && minimized) minimizePlayer(false);
    else if (index >= 0) openTrack(index, false, false);
    else stopAndReturn(false);
  });

  const initialIndex = indexFromHash();
  if (initialIndex >= 0) openTrack(initialIndex, false, false);
})();
