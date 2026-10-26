"use strict";

// ---------- data ----------
const state = { regions: [], types: [], trains: [], media: {}, lastBook: "" };

async function loadData() {
  const [trainsRes, mediaRes, quizRes, musicRes] = await Promise.all([
    fetch("data/trains.json"),
    fetch("data/media.json").catch(() => null),
    fetch("data/quiz.json").catch(() => null),
    fetch("data/music.json").catch(() => null),
  ]);
  const data = await trainsRes.json();
  state.regions = data.regions;
  state.types = data.types || [];
  state.trains = data.trains;
  state.media = mediaRes && mediaRes.ok ? await mediaRes.json() : {};
  state.quiz = quizRes && quizRes.ok ? await quizRes.json() : [];
  state.music = musicRes && musicRes.ok ? await musicRes.json() : [];
}

const trainById = (id) => state.trains.find((t) => t.id === id);
const regionById = (id) => state.regions.find((r) => r.id === id);
const typeById = (id) => state.types.find((t) => t.id === id);

// "🇨🇳 중국 · 🌏 아시아" for a tab that groups several places, "🇰🇷 한국" otherwise.
function regionLabel(r) {
  return (r.parts || [r]).map((p) => `<span class="flag">${p.flag}</span>${esc(p.name)}`).join('<span class="dot">·</span>');
}
const imagesOf = (t) => (state.media[t.id] && state.media[t.id].images) || [];
const videoOf = (t) => state.media[t.id] && state.media[t.id].video;

// ---------- helpers ----------
const app = document.getElementById("app");

function h(html) {
  const tpl = document.createElement("template");
  tpl.innerHTML = html.trim();
  return tpl.content;
}

const esc = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

function go(hash) {
  location.hash = hash;
}

// A short "pop" so taps feel alive. Silently does nothing if audio is unavailable.
let audioCtx;
function pop() {
  try {
    audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
    const o = audioCtx.createOscillator();
    const g = audioCtx.createGain();
    o.type = "sine";
    o.frequency.setValueAtTime(660, audioCtx.currentTime);
    o.frequency.exponentialRampToValueAtTime(990, audioCtx.currentTime + 0.08);
    g.gain.setValueAtTime(0.12, audioCtx.currentTime);
    g.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.15);
    o.connect(g).connect(audioCtx.destination);
    o.start();
    o.stop(audioCtx.currentTime + 0.16);
  } catch (_) {}
}

function thumbFor(t) {
  return imagesOf(t).length ? `assets/trains/${t.id}/thumb.jpg` : "";
}

// ---------- screens ----------
function renderHome() {
  app.replaceChildren(
    h(`
    <section class="home">
      <a class="round-btn pictorial-back" href="../" aria-label="도감 고르기">📚</a>
      <div class="home-hero">
        <div class="home-train" aria-hidden="true">🚄</div>
        <h1>기차 도감</h1>
        <p>세계의 멋진 기차들을 만나보자!</p>
      </div>
      <div class="home-buttons">
        <button class="big-btn book" data-go="#/book/${state.regions[0].id}">
          <span class="big-emoji">📚</span>
          <span class="big-label">기차 알아보기</span>
        </button>
        <button class="big-btn home-quiz" data-go="#/quiz">
          <span class="big-emoji">❓</span>
          <span class="big-label">기차 퀴즈</span>
        </button>
        <button class="big-btn build" data-go="#/track">
          <span class="big-emoji">🛤️</span>
          <span class="big-label">기찻길 만들기</span>
        </button>
        <button class="big-btn memory" data-go="#/memory">
          <span class="big-emoji">🃏</span>
          <span class="big-label">카드 뒤집기</span>
        </button>
        <button class="big-btn home-coupling" data-go="#/coupling">
          <span class="big-emoji">🧮</span>
          <span class="big-label">객차 연결하기</span>
        </button>
        <button class="big-btn home-music" data-go="#/music">
          <span class="big-emoji">🎵</span>
          <span class="big-label">기차 음악</span>
        </button>
      </div>
      <div class="track" aria-hidden="true"></div>
    </section>
  `)
  );
}

function renderBook(regionId) {
  const region = regionById(regionId) || state.regions[0];
  const trains = state.trains.filter((t) => t.region === region.id);
  state.lastBook = location.hash;


  const tabs = state.regions
    .map(
      (r) => `
      <button class="tab ${r.id === region.id ? "active" : ""}" style="--c:${r.color}" data-go="#/book/${r.id}">
        ${regionLabel(r)}
      </button>`
    )
    .join("");

  const cards = trains
    .map((t) => {
      const thumb = thumbFor(t);
      return `
      <button class="card" style="--c:${t.color}" data-go="#/train/${t.id}">
        <div class="card-img">
          ${thumb ? `<img src="${thumb}" alt="" loading="lazy">` : `<span class="placeholder">🚆</span>`}
          ${typeById(t.type) ? `<span class="card-type" title="${esc(typeById(t.type).name)}">${typeById(t.type).emoji}</span>` : ""}
        </div>
        <div class="card-body">
          <div class="card-name">${esc(t.name)}</div>
          <div class="card-sub">${esc(t.subtitle)}</div>
        </div>
      </button>`;
    })
    .join("");

  app.replaceChildren(
    h(`
    <section class="book" style="--region:${region.color}">
      <header class="topbar">
        <button class="round-btn" data-go="#/" aria-label="처음으로">🏠</button>
        <h1>기차 도감</h1>
        <span class="count">${trains.length}대</span>
      </header>
      <nav class="tabs">${tabs}</nav>
      <div class="grid">${cards}</div>
    </section>
  `)
  );
}

function speedLine(t) {
  const car = 100;
  if (t.speedKmh >= car * 2) return `자동차보다 약 ${Math.round(t.speedKmh / car)}배 빨라요!`;
  if (t.speedKmh > car) return `고속도로 자동차보다 빨라요!`;
  if (t.speedKmh >= 60) return `자동차랑 비슷하게 달려요.`;
  return `천천히 경치를 구경하며 달려요.`;
}

function renderTrain(id) {
  const t = trainById(id);
  if (!t) return go("#/");
  const region = regionById(t.region);
  const images = imagesOf(t);
  const video = videoOf(t);
  const maxSpeed = Math.max(350, t.speedKmh * 1.05); // maglevs go past the usual scale
  const pct = Math.min(100, (t.speedKmh / maxSpeed) * 100);

  const slides = images.length
    ? images.map((img, i) => `<img class="slide" src="${img.src}" alt="${esc(t.name)} 사진 ${i + 1}" ${i ? 'loading="lazy"' : ""}>`).join("")
    : `<div class="slide placeholder">🚆</div>`;

  const dots = images
    .map((img, i) => `<button class="thumb ${i === 0 ? "active" : ""}" data-slide="${i}" aria-label="사진 ${i + 1}"><img src="${img.src}" alt="" loading="lazy"></button>`)
    .join("");

  const credits = images
    .map(
      (img, i) =>
        `<li>사진 ${i + 1}: ${esc(img.credit || "작자 미상")} · ${esc(img.license)} · <a href="${esc(img.source)}" target="_blank" rel="noopener">출처</a></li>`
    )
    .join("");

  const videoBlock = video && video.file
    ? `<video src="${esc(video.file)}" controls playsinline preload="metadata"
         poster="${images.length ? esc(images[0].src) : ""}"></video>`
    : video
    ? `<button class="video-poster" data-video="${esc(video.youtube)}" aria-label="동영상 보기">
         <img src="https://i.ytimg.com/vi/${esc(video.youtube)}/hqdefault.jpg" alt="">
         <span class="play">▶</span>
       </button>`
    : `<div class="video-empty">동영상을 준비하고 있어요 🎬</div>`;

  app.replaceChildren(
    h(`
    <section class="detail" style="--c:${t.color}; --region:${region.color}">
      <header class="topbar">
        <button class="round-btn" data-go="${state.lastBook.startsWith(`#/book/${region.id}`) ? state.lastBook : `#/book/${region.id}`}" aria-label="뒤로">←</button>
        <span class="crumb">${regionLabel(region)}</span>
        <button class="round-btn" data-go="#/" aria-label="처음으로">🏠</button>
      </header>

      <div class="detail-main">
        <div class="gallery">
          <div class="slides">${slides}</div>
          ${images.length > 1 ? `<div class="thumbs">${dots}</div>` : ""}
        </div>

        <div class="info">
          <h1 class="train-name">${esc(t.name)}</h1>
          <p class="train-sub">${typeById(t.type) ? `<span class="type-pill">${typeById(t.type).emoji} ${esc(typeById(t.type).name)}</span>` : ""}${esc(t.subtitle)}</p>

          <div class="chips">
            <div class="chip"><span class="chip-ico">⚡</span><span class="chip-k">최고 속도</span><b>${t.speedKmh}<small>km/h</small></b></div>
            <div class="chip"><span class="chip-ico">🎂</span><span class="chip-k">처음 달린 해</span><b>${t.since}<small>년</small></b></div>
            <div class="chip"><span class="chip-ico">🌏</span><span class="chip-k">나라</span><b class="sm">${esc(t.country)}</b></div>
          </div>

          <div class="speed">
            <div class="speed-track">
              <div class="speed-fill" style="width:${pct}%"></div>
              <span class="speed-mark" style="left:${(20 / maxSpeed) * 100}%" title="자전거">🚲</span>
              <span class="speed-mark" style="left:${(100 / maxSpeed) * 100}%" title="자동차">🚗</span>
              <span class="speed-train" style="left:${pct}%">🚄</span>
            </div>
            <p class="speed-text">${speedLine(t)}</p>
          </div>

          <p class="story">${esc(t.story)}</p>

          <div class="fun">
            <div class="fun-title">💡 알고 있니?</div>
            <p>${esc(t.funFact)}</p>
          </div>

        </div>
      </div>

      <section class="video">
        <h2>🎬 달리는 모습 보기</h2>
        <div class="video-frame">${videoBlock}</div>
      </section>

      ${images.length ? `<details class="credits"><summary>사진 정보</summary><ul>${credits}</ul></details>` : ""}
    </section>
  `)
  );

  setupGallery();
  window.scrollTo(0, 0);
}

function setupGallery() {
  const slides = app.querySelector(".slides");
  const thumbs = [...app.querySelectorAll(".thumb")];
  if (!slides || !thumbs.length) return;

  slides.addEventListener(
    "scroll",
    () => {
      const i = Math.round(slides.scrollLeft / slides.clientWidth);
      thumbs.forEach((b, j) => b.classList.toggle("active", i === j));
    },
    { passive: true }
  );
}

// ---------- events ----------
app.addEventListener("click", (e) => {
  const song = e.target.closest("[data-song]");
  if (song) {
    pop();
    return openSong(song.dataset.song);
  }
  const el = e.target.closest("[data-go], [data-slide], [data-video]");
  if (!el || el.disabled) return;

  if (el.dataset.go !== undefined) {
    pop();
    go(el.dataset.go);
  } else if (el.dataset.slide !== undefined) {
    const slides = app.querySelector(".slides");
    const i = Number(el.dataset.slide);
    app.querySelectorAll(".thumb").forEach((b, j) => b.classList.toggle("active", i === j));
    slides.scrollTo({ left: slides.clientWidth * i, behavior: "smooth" });
  } else if (el.dataset.video !== undefined) {
    playVideo(el, el.dataset.video);
  }
});

// ---------- kid-safe YouTube player ----------
// The video sits under a transparent shield, so a tap can never reach YouTube's own links (logo,
// title, suggested videos) and take a child out of the app. Tapping the shield plays / pauses.
// iOS may refuse to start a video until a tap lands inside the player itself, so until the first
// play the middle of the video (YouTube's big play button) is left open; the top and bottom
// strips, where YouTube puts its links, stay covered the whole time.
let ytApi = null;
let player = null;

function loadYouTubeApi() {
  if (window.YT && window.YT.Player) return Promise.resolve(window.YT);
  if (!ytApi) {
    ytApi = new Promise((resolve, reject) => {
      const previous = window.onYouTubeIframeAPIReady;
      window.onYouTubeIframeAPIReady = () => {
        if (previous) previous();
        resolve(window.YT);
      };
      const script = document.createElement("script");
      script.src = "https://www.youtube.com/iframe_api";
      script.onerror = () => {
        ytApi = null;
        reject(new Error("YouTube API unavailable"));
      };
      document.head.appendChild(script);
    });
  }
  return ytApi;
}

function playVideo(poster, videoId) {
  const box = document.createElement("div");
  box.className = "yt-box";
  box.innerHTML = `<div class="yt-player"></div>
    <button class="yt-shield" aria-label="재생 / 일시정지"><span class="yt-state">⏳</span></button>
    <div class="yt-band top"></div><div class="yt-band bottom"></div>`;
  poster.replaceWith(box);
  const shield = box.querySelector(".yt-shield");
  const state = box.querySelector(".yt-state");
  let hasPlayed = false;
  const show = (symbol) => {
    state.textContent = symbol;
    state.hidden = !symbol;
    shield.classList.toggle("ended", symbol === "🔄");
  };

  // an ad before the video shows as "unstarted" (-1) while its clock runs. Until the video itself plays,
  // the corner with YouTube's "Skip ad" button stays open, and the rest stays covered.
  box.classList.add("ad");
  const adWatch = setInterval(() => {
    if (!box.isConnected || hasPlayed) clearInterval(adWatch);
    else if (player && player.getCurrentTime && player.getCurrentTime() > 0) shield.classList.remove("starter");
  }, 300);

  loadYouTubeApi()
    .then((YT) => {
      const S = YT.PlayerState;
      // if the video still hasn't started shortly after we asked, open the middle for a direct tap
      const openIfStuck = () =>
        setTimeout(() => {
          if (hasPlayed || !player || !player.getPlayerState) return;
          const now = player.getPlayerState();
          if (now !== S.PLAYING && now !== S.BUFFERING && !(player.getCurrentTime() > 0)) {
            shield.classList.add("starter");
            show("");
          }
        }, 1500);
      player = new YT.Player(box.querySelector(".yt-player"), {
        videoId,
        host: "https://www.youtube-nocookie.com",
        width: "100%",
        height: "100%",
        playerVars: { autoplay: 1, controls: 0, rel: 0, playsinline: 1, modestbranding: 1, disablekb: 1, fs: 0, iv_load_policy: 3 },
        events: {
          onReady: (e) => {
            e.target.playVideo();
            openIfStuck();
          },
          onStateChange: (e) => {
            if (e.data === S.PLAYING) {
              hasPlayed = true;
              box.classList.remove("ad");
              shield.classList.remove("starter");
              show("");
            } else if (!hasPlayed && e.data === S.CUED) {
              // autoplay was blocked: let the child press YouTube's own play button in the middle
              shield.classList.add("starter");
              show("");
            } else if (e.data === S.ENDED) show("🔄");
            else if (e.data === S.PAUSED) show("▶");
          },
          onError: () => show("😢"),
        },
      });
      shield.addEventListener("click", () => {
        if (!player || !player.getPlayerState) return;
        const now = player.getPlayerState();
        if (now === S.PLAYING || now === S.BUFFERING) player.pauseVideo();
        else {
          if (now === S.ENDED) player.seekTo(0, true);
          player.playVideo();
          openIfStuck();
        }
      });
    })
    .catch(() => show("😢"));
}

function stopVideo() {
  if (player && player.destroy) player.destroy();
  player = null;
}

let unmountGame = null;

function renderTrack() {
  unmountGame = window.TrackGame.mount(app);
}

function renderMemory() {
  unmountGame = window.MemoryGame.mount(app, { trains: state.trains, media: state.media });
}

// ---------- 기차 음악: real trains with songs, played in the kid-safe player ----------
const MUSIC_LANGS = [
  { id: "all", label: "전체", flag: "🎵" },
  { id: "ko", label: "한국어", flag: "🇰🇷" },
  { id: "en", label: "English", flag: "🇺🇸" },
  { id: "ja", label: "日本語", flag: "🇯🇵" },
];

function renderMusic(langId) {
  const lang = MUSIC_LANGS.find((l) => l.id === langId) || MUSIC_LANGS[0];
  const songs = state.music.filter((m) => lang.id === "all" || m.lang === lang.id);
  const flagOf = (id) => (MUSIC_LANGS.find((l) => l.id === id) || {}).flag || "";
  app.replaceChildren(
    h(`
    <section class="book music">
      <header class="topbar">
        <button class="round-btn" data-go="#/" aria-label="처음으로">🏠</button>
        <h1>기차 음악</h1>
        <span class="count">${songs.length}곡</span>
      </header>
      <nav class="tabs">
        ${MUSIC_LANGS.map(
          (l) => `<button class="tab ${l.id === lang.id ? "active" : ""}" style="--c:#E8453C" data-go="#/music/${l.id}">
            <span class="flag">${l.flag}</span>${esc(l.label)}</button>`
        ).join("")}
      </nav>
      <div class="grid music-grid">
        ${songs
          .map(
            (m) => `<button class="card song" style="--c:#E8453C" data-song="${esc(m.youtube)}">
              <div class="card-img song-img">
                <img src="https://i.ytimg.com/vi/${esc(m.youtube)}/hqdefault.jpg" alt="" loading="lazy">
                <span class="song-play">▶</span>
                <span class="card-type">${flagOf(m.lang)}</span>
              </div>
              <div class="card-body">
                <div class="card-name">${esc(m.title)}</div>
                <div class="card-sub">${esc(m.channel)}</div>
              </div>
            </button>`
          )
          .join("")}
      </div>
    </section>`)
  );
}

// Big player on top of the music list; ✕ (or tapping outside) closes it.
function openSong(id) {
  const song = state.music.find((m) => m.youtube === id);
  const overlay = document.createElement("div");
  overlay.className = "song-overlay";
  overlay.innerHTML = `
    <div class="song-sheet">
      <div class="song-head"><b>${esc(song ? song.title : "")}</b>
        <button class="round-btn song-close" aria-label="닫기">✕</button></div>
      <div class="video-frame"><div class="song-poster"></div></div>
    </div>`;
  app.appendChild(overlay);
  playVideo(overlay.querySelector(".song-poster"), id);
  const close = () => {
    stopVideo();
    overlay.remove();
  };
  overlay.addEventListener("click", (e) => {
    if (e.target === overlay || e.target.closest(".song-close")) close();
  });
}

function renderCoupling() {
  unmountGame = window.CouplingGame.mount(app);
}

function renderQuiz() {
  unmountGame = window.QuizGame.mount(app, { quiz: state.quiz });
}

function route() {
  stopVideo();
  if (unmountGame) {
    unmountGame();
    unmountGame = null;
  }
  const [, page, arg] = location.hash.split("/");
  if (page === "track") renderTrack();
  else if (page === "memory") renderMemory();
  else if (page === "quiz") renderQuiz();
  else if (page === "music") renderMusic(arg);
  else if (page === "coupling") renderCoupling();
  else if (page === "book") renderBook(arg);
  else if (page === "train") renderTrain(arg);
  else renderHome();
}

window.addEventListener("hashchange", route);

loadData()
  .then(route)
  .catch((err) => {
    app.textContent = "기차 정보를 불러오지 못했어요. 서버로 열었는지 확인해 주세요.";
    console.error(err);
  });

// Offline support on the deployed site. Skipped on localhost so local edits are never served stale.
if ("serviceWorker" in navigator && !["localhost", "127.0.0.1"].includes(location.hostname)) {
  navigator.serviceWorker.register("sw.js").catch((err) => console.warn("offline mode unavailable", err));
}
