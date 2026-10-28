"use strict";

// ---------- data ----------
const state = { books: [], sections: [], items: [], media: {}, lastBook: "" };

async function loadData() {
  const [spaceRes, mediaRes] = await Promise.all([
    fetch("data/space.json"),
    fetch("data/media.json").catch(() => null),
  ]);
  const data = await spaceRes.json();
  state.books = data.books;
  state.sections = data.sections;
  state.items = data.items;
  state.media = mediaRes && mediaRes.ok ? await mediaRes.json() : {};
}

const itemById = (id) => state.items.find((t) => t.id === id);
const sectionById = (id) => state.sections.find((s) => s.id === id);
const bookById = (id) => state.books.find((b) => b.id === id);
const sectionsOf = (book) => state.sections.filter((s) => s.book === book.id);
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
  return imagesOf(t).length ? `assets/items/${t.id}/thumb.jpg` : "";
}

// ---------- screens ----------
function renderHome() {
  const buttons = state.books
    .map(
      (b) => `
        <button class="big-btn" style="--c:${b.color}" data-go="#/book/${sectionsOf(b)[0].id}">
          <span class="big-emoji">${b.emoji}</span>
          <span class="big-label">${esc(b.name)}</span>
        </button>`
    )
    .join("");
  app.replaceChildren(
    h(`
    <section class="home">
      <a class="round-btn pictorial-back" href="../" aria-label="도감 고르기">📚</a>
      <div class="home-hero">
        <div class="home-rocket" aria-hidden="true">🚀</div>
        <h1>우주 도감</h1>
        <p>반짝반짝 우주를 탐험해 보자!</p>
      </div>
      <div class="home-buttons">${buttons}</div>
      <div class="planets-deco" aria-hidden="true">🪐 🌍 🌙 ☄️</div>
    </section>
  `)
  );
}

function renderBook(sectionId) {
  const section = sectionById(sectionId) || state.sections[0];
  const book = bookById(section.book);
  const items = state.items.filter((t) => t.section === section.id);
  state.lastBook = location.hash;

  const tabs = sectionsOf(book)
    .map(
      (s) => `
      <button class="tab ${s.id === section.id ? "active" : ""}" style="--c:${s.color}" data-go="#/book/${s.id}">
        <span class="flag">${s.emoji}</span>${esc(s.name)}
      </button>`
    )
    .join("");

  const cards = items
    .map((t) => {
      const thumb = thumbFor(t);
      return `
      <button class="card" style="--c:${t.color}" data-go="#/item/${t.id}">
        <div class="card-img">
          ${thumb ? `<img src="${thumb}" alt="" loading="lazy">` : `<span class="placeholder">${section.emoji}</span>`}
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
    <section class="book">
      <header class="topbar">
        <button class="round-btn" data-go="#/" aria-label="처음으로">🏠</button>
        <h1>${esc(book.name)}</h1>
        <span class="count">${items.length}개</span>
      </header>
      <nav class="tabs">${tabs}</nav>
      <div class="grid">${cards}</div>
    </section>
  `)
  );
}

function renderItem(id) {
  const t = itemById(id);
  if (!t) return go("#/");
  const section = sectionById(t.section);
  const images = imagesOf(t);
  const video = videoOf(t);

  const slides = images.length
    ? images.map((img, i) => `<img class="slide" src="${img.src}" alt="${esc(t.name)} 사진 ${i + 1}" ${i ? 'loading="lazy"' : ""}>`).join("")
    : `<div class="slide placeholder">${section.emoji}</div>`;

  const dots = images
    .map((img, i) => `<button class="thumb ${i === 0 ? "active" : ""}" data-slide="${i}" aria-label="사진 ${i + 1}"><img src="${img.src}" alt="" loading="lazy"></button>`)
    .join("");

  const credits = images
    .map(
      (img, i) =>
        `<li>사진 ${i + 1}: ${esc(img.credit || "작자 미상")} · ${esc(img.license)} · <a href="${esc(img.source)}" target="_blank" rel="noopener">출처</a></li>`
    )
    .join("");

  const chips = t.facts
    .map(
      ([ico, k, v, unit]) => `
      <div class="chip"><span class="chip-ico">${ico}</span><span class="chip-k">${esc(k)}</span>
        <b class="${v.length > 5 ? "sm" : ""}">${esc(v)}${unit ? `<small>${esc(unit)}</small>` : ""}</b></div>`
    )
    .join("");

  const videoBlock = video
    ? `<section class="video">
        <h2>🎬 영상으로 보기</h2>
        <div class="video-frame">
          <button class="video-poster" data-video="${esc(video.youtube)}" aria-label="동영상 보기">
            <img src="https://i.ytimg.com/vi/${esc(video.youtube)}/hqdefault.jpg" alt="">
            <span class="play">▶</span>
          </button>
        </div>
      </section>`
    : "";

  const back = state.lastBook.startsWith(`#/book/${section.id}`) ? state.lastBook : `#/book/${section.id}`;
  app.replaceChildren(
    h(`
    <section class="detail" style="--c:${t.color}">
      <header class="topbar">
        <button class="round-btn" data-go="${back}" aria-label="뒤로">←</button>
        <span class="crumb"><span class="flag">${section.emoji}</span>${esc(section.name)}</span>
        <button class="round-btn" data-go="#/" aria-label="처음으로">🏠</button>
      </header>

      <div class="detail-main">
        <div class="gallery">
          <div class="slides">${slides}</div>
          ${images.length > 1 ? `<div class="thumbs">${dots}</div>` : ""}
        </div>

        <div class="info">
          <h1 class="item-name">${esc(t.name)}</h1>
          <p class="item-sub">${esc(t.subtitle)}</p>
          <div class="chips">${chips}</div>
          <p class="story">${esc(t.story)}</p>
          <div class="fun">
            <div class="fun-title">💡 알고 있니?</div>
            <p>${esc(t.funFact)}</p>
          </div>
        </div>
      </div>

      ${videoBlock}

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
    else if (player && player.getCurrentTime && player.getCurrentTime() > 0 && shield.classList.contains("starter")) {
      shield.classList.remove("starter");
      show("");
    }
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
            show("▶"); // only a hint: taps go through to YouTube's own player
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
              show("▶"); // only a hint: taps go through to YouTube's own player
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


// ---------- events ----------
app.addEventListener("click", (e) => {
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

function route() {
  stopVideo();
  const [, page, arg] = location.hash.split("/");
  if (page === "book") renderBook(arg);
  else if (page === "item") renderItem(arg);
  else renderHome();
}

window.addEventListener("hashchange", route);

loadData()
  .then(route)
  .catch(() => {
    app.innerHTML = `<p style="padding:40px;font-size:24px">도감을 불러오지 못했어요 😢</p>`;
  });

// Offline support (skipped on localhost so edits show up right away while working).
if ("serviceWorker" in navigator && !["localhost", "127.0.0.1"].includes(location.hostname)) {
  navigator.serviceWorker.register("sw.js").catch(() => {});
}
