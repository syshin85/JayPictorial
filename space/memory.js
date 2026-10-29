"use strict";

// 카드 뒤집기: a memory game with the encyclopedia's photos (copy of train/memory.js).
// Exposes window.MemoryGame.mount(container, { items, media }) → returns an unmount function.
(function () {
  const LEVELS = [
    { id: "easy", label: "쉬움", cols: 4, rows: 3, emoji: "🐣" },
    { id: "normal", label: "보통", cols: 4, rows: 4, emoji: "🌙" },
    { id: "hard", label: "어려움", cols: 6, rows: 4, emoji: "🚀", recommended: true },
  ];
  const MISMATCH_MS = 900;
  const GAP = 10;

  // ---------- sounds (same as the train pictorial; there is no mute switch here) ----------
  let audio;
  function tone(freqs, { type = "sine", dur = 0.12, vol = 0.12, glide, delay = 0 } = {}) {
    try {
      audio = audio || new (window.AudioContext || window.webkitAudioContext)();
      if (audio.state === "suspended") audio.resume();
      const now = audio.currentTime + delay;
      for (const f of freqs) {
        const o = audio.createOscillator();
        const g = audio.createGain();
        o.type = type;
        o.frequency.setValueAtTime(f, now);
        if (glide) o.frequency.exponentialRampToValueAtTime(f * glide, now + dur);
        g.gain.setValueAtTime(0.0001, now);
        g.gain.exponentialRampToValueAtTime(vol, now + 0.02);
        g.gain.exponentialRampToValueAtTime(0.0001, now + dur);
        o.connect(g).connect(audio.destination);
        o.start(now);
        o.stop(now + dur + 0.02);
      }
    } catch (_) {}
  }
  const sounds = {
    flip: () => tone([700], { type: "triangle", dur: 0.06, vol: 0.12, glide: 1.3 }),
    match: () => {
      tone([660], { type: "triangle", dur: 0.12, vol: 0.14 });
      tone([990], { type: "triangle", dur: 0.18, vol: 0.14, delay: 0.1 });
    },
    miss: () => tone([260], { type: "sine", dur: 0.15, vol: 0.1, glide: 0.8 }),
    clear: () => [523, 659, 784, 1047].forEach((f, i) => tone([f], { type: "square", dur: 0.22, vol: 0.06, delay: i * 0.13 })),
  };

  // ---------- helpers ----------
  const esc = (s) =>
    String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  function shuffle(list) {
    const a = list.slice();
    for (let i = a.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
  }

  function fmt(ms) {
    const s = Math.floor(ms / 1000);
    return `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
  }

  const bestKey = (level) => `jaypictorial.space.memory.best.${level}`;
  function loadBest(level) {
    try {
      const v = Number(localStorage.getItem(bestKey(level)));
      return v > 0 ? v : null;
    } catch (_) {
      return null;
    }
  }
  function saveBest(level, ms) {
    try {
      localStorage.setItem(bestKey(level), String(ms));
    } catch (_) {}
  }

  // ---------- mount ----------
  function mount(container, { items = [], media = {} } = {}) {
    // only items that have a card photo
    const pool = items.filter((t) => ((media[t.id] || {}).images || []).length);

    let level = null;
    let deck = []; // [{ id, name, thumb }]
    let open = []; // indices currently face-up and not yet matched
    let matched = new Set();
    let busy = false;
    let moves = 0;
    let startedAt = 0;
    let ticker = 0;
    let flipBackTimer = 0;

    container.innerHTML = `
      <section class="mem">
        <header class="topbar mem-top">
          <button class="round-btn" data-go="#/" aria-label="처음으로">🏠</button>
          <h1>카드 뒤집기</h1>
          <div class="mem-stats" hidden>
            <span class="mem-stat">⏱ <b class="mem-time">00:00</b></span>
            <span class="mem-stat">👆 <b class="mem-moves">0</b>번</span>
          </div>
        </header>
        <div class="mem-stage"></div>
      </section>`;

    const root = container.querySelector(".mem");
    const stage = root.querySelector(".mem-stage");
    const stats = root.querySelector(".mem-stats");
    const timeEl = root.querySelector(".mem-time");
    const movesEl = root.querySelector(".mem-moves");

    function stopTimer() {
      clearInterval(ticker);
      ticker = 0;
    }

    function showPicker() {
      stopTimer();
      clearTimeout(flipBackTimer);
      stats.hidden = true;
      level = null;
      stage.innerHTML = `
        <div class="mem-picker">
          <p class="mem-ask">같은 우주 카드 두 장을 찾아요! 어떤 걸로 할까?</p>
          <div class="mem-levels">
            ${LEVELS.map((l) => {
              const best = loadBest(l.id);
              return `<button class="mem-level ${l.recommended ? "rec" : ""}" data-level="${l.id}">
                ${l.recommended ? '<span class="mem-rec">추천!</span>' : ""}
                <span class="mem-level-emoji">${l.emoji}</span>
                <span class="mem-level-name">${l.label}</span>
                <span class="mem-level-size">${l.cols}×${l.rows} · ${(l.cols * l.rows) / 2}쌍</span>
                <span class="mem-level-best">${best ? `🏆 ${fmt(best)}` : "&nbsp;"}</span>
              </button>`;
            }).join("")}
          </div>
        </div>`;
    }

    function startGame(levelId) {
      level = LEVELS.find((l) => l.id === levelId);
      const pairs = level.cols * level.rows / 2;
      const picked = shuffle(pool).slice(0, pairs);
      deck = shuffle(
        picked.flatMap((t) => {
          const card = { id: t.id, name: t.name, thumb: `assets/items/${t.id}/thumb.jpg` };
          return [card, { ...card }];
        })
      );
      open = [];
      matched = new Set();
      busy = false;
      moves = 0;
      startedAt = 0;
      stopTimer();
      timeEl.textContent = "00:00";
      movesEl.textContent = "0";
      stats.hidden = false;

      stage.innerHTML = `
        <div class="mem-grid">
          ${deck
            .map(
              (c, i) => `
            <button class="mcard" data-card="${i}" aria-label="카드 ${i + 1}">
              <span class="mcard-inner">
                <span class="mcard-face mcard-back"><span>🪐</span></span>
                <span class="mcard-face mcard-front">
                  <img src="${esc(c.thumb)}" alt="" draggable="false">
                  <span class="mcard-name">${esc(c.name)}</span>
                </span>
              </span>
            </button>`
            )
            .join("")}
        </div>`;
      layout();
    }

    // Size cards so the whole board fits without scrolling; 6×4 turns into 4×6 when the iPad is upright.
    function layout() {
      const grid = stage.querySelector(".mem-grid");
      if (!grid || !level) return;
      const w = stage.clientWidth;
      const h = stage.clientHeight;
      const portrait = h > w;
      const cols = portrait ? Math.min(level.cols, level.rows) : Math.max(level.cols, level.rows);
      const rows = (level.cols * level.rows) / cols;
      const ratio = 0.8; // card width / height
      const cardH = Math.floor(Math.min((h - GAP * (rows - 1)) / rows, (w - GAP * (cols - 1)) / cols / ratio));
      const cardW = Math.floor(cardH * ratio);
      grid.style.gridTemplateColumns = `repeat(${cols}, ${cardW}px)`;
      grid.style.gridAutoRows = `${cardH}px`;
      grid.style.setProperty("--card-h", `${cardH}px`);
    }
    const ro = new ResizeObserver(layout);
    ro.observe(stage);

    function flip(i) {
      if (busy || matched.has(i) || open.includes(i)) return;
      const el = stage.querySelector(`[data-card="${i}"]`);
      if (!el) return;
      if (!startedAt) {
        startedAt = Date.now();
        ticker = setInterval(() => (timeEl.textContent = fmt(Date.now() - startedAt)), 250);
      }
      el.classList.add("flipped");
      sounds.flip();
      open.push(i);
      if (open.length < 2) return;

      moves += 1;
      movesEl.textContent = String(moves);
      const [a, b] = open;
      if (deck[a].id === deck[b].id) {
        open = [];
        for (const k of [a, b]) {
          matched.add(k);
          stage.querySelector(`[data-card="${k}"]`).classList.add("matched");
        }
        sounds.match();
        if (matched.size === deck.length) finish();
      } else {
        busy = true; // no third card while these two are shown
        flipBackTimer = setTimeout(() => {
          for (const k of [a, b]) stage.querySelector(`[data-card="${k}"]`)?.classList.remove("flipped");
          open = [];
          busy = false;
          sounds.miss();
        }, MISMATCH_MS);
      }
    }

    function finish() {
      stopTimer();
      const ms = Date.now() - startedAt;
      timeEl.textContent = fmt(ms);
      const best = loadBest(level.id);
      const record = !best || ms < best;
      if (record) saveBest(level.id, ms);
      setTimeout(() => {
        sounds.clear();
        const overlay = document.createElement("div");
        overlay.className = "mem-clear";
        overlay.innerHTML = `
          <div class="mem-clear-card">
            <div class="mem-clear-emoji">🎉</div>
            <h2>다 찾았어요! 정말 대단해!</h2>
            ${record ? '<div class="mem-record">🏆 새 기록!</div>' : ""}
            <div class="mem-result">
              <div><span>걸린 시간</span><b>${fmt(ms)}</b></div>
              <div><span>뒤집은 횟수</span><b>${moves}번</b></div>
            </div>
            ${!record && best ? `<p class="mem-best">최고 기록 🏆 ${fmt(best)}</p>` : ""}
            <div class="mem-clear-btns">
              <button class="mem-btn primary" data-act="again">🔄 다시 하기</button>
              <button class="mem-btn" data-act="levels">🎚 난이도 바꾸기</button>
              <button class="mem-btn" data-go="#/">🏠</button>
            </div>
          </div>`;
        root.appendChild(overlay);
      }, 500);
    }

    root.addEventListener("click", (e) => {
      const card = e.target.closest("[data-card]");
      if (card) return flip(Number(card.dataset.card));
      const lv = e.target.closest("[data-level]");
      if (lv) {
        tone([520], { type: "triangle", dur: 0.08, vol: 0.12, glide: 1.4 });
        return startGame(lv.dataset.level);
      }
      const act = e.target.closest("[data-act]");
      if (!act) return;
      root.querySelector(".mem-clear")?.remove();
      if (act.dataset.act === "again") startGame(level.id);
      if (act.dataset.act === "levels") showPicker();

    });

    showPicker();

    return function unmount() {
      stopTimer();
      clearTimeout(flipBackTimer);
      ro.disconnect();
    };
  }

  window.MemoryGame = { mount };
})();
