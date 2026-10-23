"use strict";

// 객차 연결하기: build a train with exactly the asked number of cars.
// Coupling a bundle of cars adds, uncoupling cars subtracts — the equation is written as the child plays.
// Exposes window.CouplingGame.mount(container) → returns an unmount function.
(function () {
  const ROUND = 10;
  const LEVELS = [
    { id: "easy", label: "쉬움", emoji: "🐣", max: 5, bundles: [1, 2, 3], kinds: ["build"] },
    { id: "normal", label: "보통", emoji: "🚃", max: 10, bundles: [1, 2, 3, 4], kinds: ["build", "build", "change"], recommended: true },
    { id: "hard", label: "어려움", emoji: "🚄", max: 15, bundles: [1, 2, 3, 4, 5], kinds: ["build", "change", "change"] },
  ];
  // car colours by kind: 객차 / 화물칸 / 식당칸 / 침대칸
  const CAR_KINDS = [
    { name: "객차", body: "#2F7DE1", dark: "#1B4F94" },
    { name: "화물칸", body: "#C47F2C", dark: "#8A5414" },
    { name: "식당칸", body: "#2FA65A", dark: "#1C6B39" },
    { name: "침대칸", body: "#8B5CF6", dark: "#5B32B8" },
    { name: "객차", body: "#E8453C", dark: "#A8271F" },
  ];
  const MIN_CAR = 34; // px; below this the train wraps onto a second row

  // ---------- sounds (same style and mute setting as the other games) ----------
  let audio;
  const buffers = {};
  let loading = null;
  const isMuted = () => {
    try {
      return localStorage.getItem("jaytrain.muted") === "1";
    } catch (_) {
      return false;
    }
  };
  function ctx() {
    audio = audio || new (window.AudioContext || window.webkitAudioContext)();
    if (audio.state === "suspended") audio.resume();
    return audio;
  }
  function tone(freqs, { type = "sine", dur = 0.12, vol = 0.12, glide, delay = 0 } = {}) {
    if (isMuted()) return;
    try {
      const a = ctx();
      const now = a.currentTime + delay;
      for (const f of freqs) {
        const o = a.createOscillator();
        const g = a.createGain();
        o.type = type;
        o.frequency.setValueAtTime(f, now);
        if (glide) o.frequency.exponentialRampToValueAtTime(f * glide, now + dur);
        g.gain.setValueAtTime(0.0001, now);
        g.gain.exponentialRampToValueAtTime(vol, now + 0.015);
        g.gain.exponentialRampToValueAtTime(0.0001, now + dur);
        o.connect(g).connect(a.destination);
        o.start(now);
        o.stop(now + dur + 0.02);
      }
    } catch (_) {}
  }
  // the recorded whistle and steam chuffs used by 기찻길 만들기
  function loadRecordings() {
    if (loading) return loading;
    let a;
    try {
      a = ctx();
    } catch (_) {
      return Promise.resolve();
    }
    loading = Promise.all(
      [
        ["whistle", "assets/sounds/whistle.wav"],
        ["chuff", "assets/sounds/chuff-loop.wav"],
      ].map(([name, url]) =>
        fetch(url)
          .then((r) => (r.ok ? r.arrayBuffer() : Promise.reject(r.status)))
          .then((data) => new Promise((ok, fail) => a.decodeAudioData(data, ok, fail))) // old Safari: callback form
          .then((buf) => (buffers[name] = buf))
          .catch(() => {})
      )
    );
    return loading;
  }
  function playRecording(name, { vol = 0.6, seconds } = {}) {
    if (isMuted() || !buffers[name]) return false;
    const a = ctx();
    const src = a.createBufferSource();
    const g = a.createGain();
    src.buffer = buffers[name];
    src.loop = !!seconds;
    g.gain.value = vol;
    src.connect(g).connect(a.destination);
    src.start();
    if (seconds) {
      g.gain.setValueAtTime(vol, a.currentTime + seconds - 0.5);
      g.gain.linearRampToValueAtTime(0.0001, a.currentTime + seconds);
      src.stop(a.currentTime + seconds + 0.05);
    }
    return true;
  }
  const sounds = {
    tap: () => tone([620], { type: "triangle", dur: 0.06, vol: 0.12, glide: 1.3 }),
    couple: () => {
      // 철컥: two quick metallic knocks
      tone([1400], { type: "square", dur: 0.04, vol: 0.06 });
      tone([900], { type: "square", dur: 0.06, vol: 0.07, delay: 0.06 });
    },
    uncouple: () => tone([500], { type: "triangle", dur: 0.18, vol: 0.12, glide: 0.5 }),
    right: () => {
      tone([660], { type: "triangle", dur: 0.12, vol: 0.14 });
      tone([990], { type: "triangle", dur: 0.18, vol: 0.14, delay: 0.1 });
    },
    depart: () => {
      if (!playRecording("whistle", { vol: 0.5 })) tone([587, 740], { type: "square", dur: 0.5, vol: 0.05 });
      playRecording("chuff", { vol: 0.5, seconds: 2.6 });
    },
    fanfare: () => [523, 659, 784, 1047].forEach((f, i) => tone([f], { type: "square", dur: 0.22, vol: 0.06, delay: i * 0.13 })),
  };

  // ---------- missions ----------
  const rand = (lo, hi) => lo + Math.floor(Math.random() * (hi - lo + 1));
  const pick = (list) => list[Math.floor(Math.random() * list.length)];

  // Every mission reads the same: "make an N-car train". build starts with no cars (adding);
  // change starts with some cars already coupled, half the time more than needed (taking away).
  const missionText = (target) => `🎯 <b>${target}칸</b> 기차를 만들어서 출발시켜요!`;

  function makeMission(level, prev) {
    for (let tries = 0; tries < 20; tries++) {
      const kind = pick(level.kinds);
      let m;
      if (kind === "build") {
        const target = rand(2, level.max);
        m = { kind, start: 0, target, text: missionText(target) };
      } else {
        const shrink = Math.random() < 0.5;
        const start = shrink ? rand(4, level.max) : rand(2, level.max - 2);
        const target = shrink ? rand(1, start - 1) : rand(start + 1, level.max);
        m = { kind, start, target, text: missionText(target) };
      }
      // don't repeat the previous mission exactly
      if (!prev || prev.start !== m.start || prev.target !== m.target) return m;
    }
    return { kind: "build", start: 0, target: 3, text: missionText(3) };
  }

  // ---------- mount ----------
  function mount(container) {
    let level = null;
    let missionNo = 0;
    let mission = null;
    let cars = []; // { kind, bundle } — bundle groups cars coupled together
    let ops = []; // one step per tap: { sign: "+" | "−", n, from, to } — each shown as its own short equation
    let bundleSeq = 0;
    let departing = false;
    let departed = 0;
    let timers = [];
    loadRecordings();

    container.innerHTML = `
      <section class="cpl">
        <header class="topbar cpl-top">
          <button class="round-btn" data-go="#/" aria-label="처음으로">🏠</button>
          <h1>객차 연결하기</h1>
          <span class="cpl-progress" hidden></span>
        </header>
        <div class="cpl-stage"></div>
      </section>`;
    const root = container.querySelector(".cpl");
    const stage = root.querySelector(".cpl-stage");
    const progress = root.querySelector(".cpl-progress");
    const later = (fn, ms) => timers.push(setTimeout(fn, ms));

    // ----- level picker -----
    function showPicker() {
      level = null;
      progress.hidden = true;
      stage.innerHTML = `
        <div class="cpl-picker">
          <div class="cpl-hero" aria-hidden="true">🚂🚃🚃🚃</div>
          <p class="cpl-ask">객차를 <b>더하고</b> <b>빼서</b> 기차를 만들어요! 몇 칸 기차를 만들까?</p>
          <div class="cpl-levels">
            ${LEVELS.map(
              (l) => `<button class="cpl-level ${l.recommended ? "rec" : ""}" data-level="${l.id}">
                ${l.recommended ? '<span class="cpl-rec">추천!</span>' : ""}
                <span class="cpl-level-emoji">${l.emoji}</span>
                <span class="cpl-level-name">${l.label}</span>
                <span class="cpl-level-size">${l.max}칸까지 · ${l.id === "easy" ? "더하기" : "더하기 + 빼기"}</span>
              </button>`
            ).join("")}
          </div>
        </div>`;
    }

    function startRound(levelId) {
      level = LEVELS.find((l) => l.id === levelId);
      missionNo = 0;
      departed = 0;
      mission = null;
      nextMission();
    }

    function nextMission() {
      missionNo++;
      if (missionNo > ROUND) return showEnd();
      mission = makeMission(level, mission);
      bundleSeq = 0;
      cars = [];
      ops = [];
      // a starting train is shown as one coupled bundle
      if (mission.start) addCars(mission.start, false);
      departing = false;
      renderMission();
    }

    function addCars(n, record = true) {
      const bundle = bundleSeq++;
      const kind = bundle % CAR_KINDS.length;
      for (let i = 0; i < n; i++) cars.push({ kind, bundle });
      if (record) ops.push({ sign: "+", n, from: cars.length - n, to: cars.length });
    }

    // ----- mission screen -----
    function renderMission() {
      progress.hidden = false;
      progress.textContent = `${missionNo} / ${ROUND}`;
      stage.innerHTML = `
        <div class="cpl-mission">${mission.text}</div>
        <div class="cpl-yard-rail">
          <div class="cpl-train"></div>
          <div class="cpl-rail" aria-hidden="true"></div>
        </div>
        <div class="cpl-math">
          <div class="cpl-hist" aria-hidden="true"></div>
          <div class="cpl-eq" aria-live="polite"></div>
          <div class="cpl-hint"></div>
        </div>
        <div class="cpl-bottom">
          <button class="cpl-go" data-act="go" hidden>출발! 🚂</button>
          <div class="cpl-yard">
            <span class="cpl-yard-label">➕ 더하기</span>
            ${level.bundles
              .map(
                (n) => `<button class="cpl-bundle" data-add="${n}" aria-label="${n}칸 더하기">
                  <span class="cpl-mini">${'<i></i>'.repeat(n)}</span><b>+${n}칸</b></button>`
              )
              .join("")}
          </div>
          ${level.kinds.includes("change")
            ? `<div class="cpl-yard take">
            <span class="cpl-yard-label">➖ 빼기</span>
            ${level.bundles
              .map(
                (n) => `<button class="cpl-bundle take" data-take="${n}" aria-label="${n}칸 빼기">
                  <span class="cpl-mini">${'<i></i>'.repeat(n)}</span><b>−${n}칸</b></button>`
              )
              .join("")}
          </div>`
            : ""}
        </div>`;
      renderTrain();
    }

    function renderTrain() {
      const train = stage.querySelector(".cpl-train");
      if (!train) return;
      train.innerHTML =
        `<div class="cpl-loco" aria-hidden="true">🚂</div>` +
        cars
          .map((c, i) => {
            const k = CAR_KINDS[c.kind];
            const joinsNext = cars[i + 1] && cars[i + 1].bundle === c.bundle;
            return `<div class="cpl-car ${joinsNext ? "joined" : ""}" data-car="${i}"
              style="--body:${k.body};--dark:${k.dark}">
              <span class="cpl-num">${i + 1}</span><span class="cpl-win"></span>
            </div>`;
          })
          .join("");
      fitTrain();
      updateMath();
    }

    // one row when it fits, otherwise two rows; cars shrink to fit the width
    const GAP = 4; // must match .cpl-train gap
    const LOCO = 1.5; // locomotive width in car widths (.cpl-loco)
    function fitTrain() {
      const train = stage.querySelector(".cpl-train");
      if (!train || !train.parentElement.clientWidth) return;
      const w = train.parentElement.clientWidth - 16; // .cpl-train side padding
      const n = cars.length;
      const across = (units, count) => Math.floor((w - GAP * count) / units);
      let size = across(n + LOCO, n + 1);
      let rows = 1;
      if (size < MIN_CAR) {
        rows = 2;
        const perRow = Math.ceil((n + LOCO) / 2);
        size = across(perRow, perRow);
      }
      train.style.setProperty("--car", Math.max(20, Math.min(72, size)) + "px");
      train.classList.toggle("two-rows", rows === 2);
    }

    // The latest tap as a two-number equation: "5 + 3 = 8", "8 − 2 = 6". Before any tap: the count.
    const stepText = (op) => `${op.from} ${op.sign} ${op.n} = ${op.to}`;
    function equationText() {
      return ops.length ? stepText(ops[ops.length - 1]) : String(cars.length);
    }

    function updateMath() {
      const eq = stage.querySelector(".cpl-eq");
      const hint = stage.querySelector(".cpl-hint");
      const go = stage.querySelector(".cpl-go");
      if (!eq) return;
      eq.textContent = equationText();
      // the two taps before, small and faded, so the child can follow what happened
      stage.querySelector(".cpl-hist").innerHTML = ops
        .slice(-3, -1)
        .map((op) => `<span>${stepText(op)}</span>`)
        .join("");
      const n = cars.length;
      const done = n === mission.target && (ops.length > 0 || mission.start === 0);
      hint.className = "cpl-hint";
      if (done) {
        hint.textContent = "딱 맞아요! 출발해요! 🎉";
        hint.classList.add("ok");
      } else if (n > mission.target) {
        hint.textContent = "너무 길어요! 몇 칸 빼 볼까? ➖";
        hint.classList.add("long");
      } else if (n === 0) {
        hint.textContent = "👇 몇 칸을 더할까요?";
      } else {
        hint.textContent = "조금 모자라요! 몇 칸 더해 볼까? ➕";
      }
      go.hidden = !done;
      if (done && !go.dataset.shown) {
        go.dataset.shown = "1";
        sounds.right();
      } else if (!done) {
        delete go.dataset.shown;
      }
    }

    function uncouple(index) {
      const removed = cars.length - index;
      if (removed <= 0) return;
      sounds.uncouple();
      // the count and the equation change right away; copies of the cars roll off for show
      const rail = stage.querySelector(".cpl-yard-rail");
      const base = rail.getBoundingClientRect();
      [...stage.querySelectorAll(".cpl-car")].slice(index).forEach((el) => {
        const r = el.getBoundingClientRect();
        const ghost = el.cloneNode(true);
        ghost.removeAttribute("data-car");
        ghost.classList.add("cpl-ghost");
        Object.assign(ghost.style, { left: r.left - base.left + "px", top: r.top - base.top + "px", width: r.width + "px", height: r.height + "px" });
        ghost.addEventListener("animationend", () => ghost.remove());
        rail.appendChild(ghost);
      });
      cars = cars.slice(0, index);
      ops.push({ sign: "−", n: removed, from: cars.length + removed, to: cars.length });
      renderTrain();
    }

    function depart() {
      departing = true;
      departed++;
      sounds.depart();
      const train = stage.querySelector(".cpl-train");
      stage.querySelector(".cpl-go").hidden = true;
      stage.querySelector(".cpl-hint").textContent = `🎉 딱 ${cars.length}칸! 출발~`;
      train.classList.add("leaving");
      later(nextMission, 2300);
    }

    function showEnd() {
      progress.hidden = true;
      stage.innerHTML = `
        <div class="cpl-end">
          <div class="cpl-hero">🎉</div>
          <h2>기차 ${departed}대가 출발했어요!</h2>
          <div class="cpl-badges">${"🚂".repeat(departed)}</div>
          <div class="cpl-end-btns">
            <button class="cpl-btn" data-act="again">다시 하기 🔄</button>
            <button class="cpl-btn alt" data-act="levels">난이도 바꾸기</button>
            <button class="cpl-btn alt" data-go="#/">🏠 처음으로</button>
          </div>
        </div>`;
      sounds.fanfare();
    }

    // ----- input -----
    root.addEventListener("click", (e) => {
      const lv = e.target.closest("[data-level]");
      if (lv) {
        sounds.tap();
        return startRound(lv.dataset.level);
      }
      const act = e.target.closest("[data-act]");
      if (act) {
        if (act.dataset.act === "go" && !departing) return depart();
        if (act.dataset.act === "again") {
          sounds.tap();
          return startRound(level.id);
        }
        if (act.dataset.act === "levels") {
          sounds.tap();
          return showPicker();
        }
        return;
      }
      if (departing) return;
      const add = e.target.closest("[data-add]");
      if (add) {
        addCars(Number(add.dataset.add));
        sounds.couple();
        renderTrain();
        const last = stage.querySelectorAll(".cpl-car");
        [...last].slice(-Number(add.dataset.add)).forEach((el) => el.classList.add("arriving"));
        return;
      }
      const take = e.target.closest("[data-take]");
      if (take) {
        const n = Number(take.dataset.take);
        if (n > cars.length) {
          tone([220], { type: "sine", dur: 0.15, vol: 0.1, glide: 0.8 });
          stage.querySelector(".cpl-hint").textContent = `기차에 ${cars.length}칸밖에 없어요!`;
          return;
        }
        uncouple(cars.length - n);
      }
    });

    const ro = new ResizeObserver(() => fitTrain());
    ro.observe(stage);

    showPicker();

    return function unmount() {
      timers.forEach(clearTimeout);
      timers = [];
      ro.disconnect();
    };
  }

  window.CouplingGame = { mount };
})();
