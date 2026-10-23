"use strict";

// 기찻길 만들기: lay track pieces on a grid, then put trains on them and watch them follow the track.
// Exposes window.TrackGame.mount(container) → returns an unmount function.
(function () {
  const COLS = 10;
  const ROWS = 7;
  const STORAGE_KEY = "jaytrain.track.v1";

  // Edges of a cell: 0 = top, 1 = right, 2 = bottom, 3 = left.
  const DR = [-1, 0, 1, 0];
  const DC = [0, 1, 0, -1];
  const opposite = (d) => (d + 2) % 4;

  // Each piece is a list of connections between two edges.
  const PIECES = {
    h: [[1, 3]],
    v: [[0, 2]],
    ne: [[0, 1]],
    es: [[1, 2]],
    sw: [[2, 3]],
    wn: [[3, 0]],
    x: [[0, 2], [1, 3]],
  };
  // Switches (갈림길): a stem edge and two branches. Only the stem and the selected branch are
  // connected, so flipping a switch changes things for trains coming from any direction: a train
  // arriving on the closed branch stops and turns back.
  const SWITCHES = {};
  for (let s = 0; s < 4; s++) {
    SWITCHES["t" + s] = { stem: s, branches: [(s + 1) % 4, (s + 3) % 4] }; // T: curve left or right
    SWITCHES["yl" + s] = { stem: s, branches: [opposite(s), (s + 1) % 4] }; // straight or curve left
    SWITCHES["yr" + s] = { stem: s, branches: [opposite(s), (s + 3) % 4] }; // straight or curve right
  }
  for (const [id, sw] of Object.entries(SWITCHES)) PIECES[id] = sw.branches.map((b) => [sw.stem, b]);

  // The palette shows one button per kind; tapping the selected button again turns it.
  const KINDS = [
    { id: "straight", label: "직선", pieces: ["h", "v"] },
    { id: "curve", label: "커브", pieces: ["es", "sw", "wn", "ne"] },
    { id: "cross", label: "교차로", pieces: ["x"] },
    { id: "t", label: "T자 갈림길", pieces: ["t2", "t3", "t0", "t1"] },
    { id: "yl", label: "왼쪽 갈림길", pieces: ["yl2", "yl3", "yl0", "yl1"] },
    { id: "yr", label: "오른쪽 갈림길", pieces: ["yr2", "yr3", "yr0", "yr1"] },
  ];
  const ROTATE = {};
  for (const k of KINDS) k.pieces.forEach((p, i) => (ROTATE[p] = k.pieces[(i + 1) % k.pieces.length]));

  // A tile is a piece id, plus ":1" when a switch points to its second branch.
  const baseOf = (tile) => (tile ? tile.split(":")[0] : null);
  const stateOf = (tile) => (tile && tile.endsWith(":1") ? 1 : 0);
  const isSwitch = (tile) => !!SWITCHES[baseOf(tile)];
  const edgesOf = (tile) => new Set((PIECES[baseOf(tile)] || []).flat());
  function hasRoute(tile, a, b) {
    return (PIECES[baseOf(tile)] || []).some(([x, y]) => (x === a && y === b) || (x === b && y === a));
  }

  function pieceFor(a, b) {
    const key = [a, b].sort().join("");
    return { "13": "h", "02": "v", "01": "ne", "12": "es", "23": "sw", "03": "wn" }[key];
  }

  const TRAIN_COLORS = [
    { id: "red", body: "#E8453C", dark: "#A8271F", label: "빨간 기차" },
    { id: "blue", body: "#2F7DE1", dark: "#1B4F94", label: "파란 기차" },
    { id: "green", body: "#2FA65A", dark: "#1C6B39", label: "초록 기차" },
  ];
  const MAX_TRAINS = 3;
  const CARS = 4; // a locomotive at each end (like a KTX) + 2 carriages, so turning around looks natural
  const CAR_GAP = 0.62; // in cells
  const SPEEDS = { slow: 0.9, fast: 2.0 }; // cells per second

  // A figure-eight with a crossing in the middle, so kids see what's possible.
  function exampleGrid() {
    const g = emptyGrid();
    const put = (r, c, t) => (g[r][c] = t);
    // outer loop
    put(1, 1, "es"); for (let c = 2; c <= 7; c++) put(1, c, "h"); put(1, 8, "sw");
    for (let r = 2; r <= 4; r++) { put(r, 1, "v"); put(r, 8, "v"); }
    put(5, 1, "ne"); for (let c = 2; c <= 7; c++) put(5, c, "h"); put(5, 8, "wn");
    // a line through the middle crossing the loop's sides
    put(3, 0, "es"); put(4, 0, "v"); put(5, 0, "v");
    put(3, 1, "x"); for (let c = 2; c <= 7; c++) put(3, c, "h"); put(3, 8, "x"); put(3, 9, "sw");
    put(4, 9, "v"); put(5, 9, "v"); put(6, 9, "wn");
    for (let c = 1; c <= 8; c++) put(6, c, "h"); put(6, 0, "ne");
    // a siding off the top: tap the switch to send trains up there
    put(1, 6, "yl3"); put(0, 6, "es"); put(0, 7, "h"); put(0, 8, "h");
    return g;
  }

  function emptyGrid() {
    return Array.from({ length: ROWS }, () => Array(COLS).fill(null));
  }

  function loadGrid() {
    try {
      const saved = JSON.parse(localStorage.getItem(STORAGE_KEY));
      if (Array.isArray(saved) && saved.length === ROWS) {
        return saved.map((row) => Array.from({ length: COLS }, (_, c) => (PIECES[baseOf(row[c])] ? row[c] : null)));
      }
    } catch (_) {}
    return emptyGrid();
  }

  function saveGrid(grid) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(grid));
    } catch (_) {}
  }

  // ---------- sounds ----------
  let audio;
  let muted = false;
  try {
    muted = localStorage.getItem("jaytrain.muted") === "1";
  } catch (_) {}

  function audioCtx() {
    audio = audio || new (window.AudioContext || window.webkitAudioContext)();
    if (audio.state === "suspended") audio.resume();
    return audio;
  }

  function tone(freqs, { type = "sine", dur = 0.12, vol = 0.12, glide } = {}) {
    if (muted) return;
    try {
      const audio = audioCtx();
      const now = audio.currentTime;
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
  // Recorded sounds (Wikimedia Commons, see README): a seamless steam-engine loop, wheels on rail
  // joints, and a steam whistle. The synthesized tones below are only for taps and bumps.
  const RECORDINGS = {
    chuff: "assets/sounds/chuff-loop.wav",
    rail: "assets/sounds/rail-loop.wav",
    whistle: "assets/sounds/whistle.wav",
  };
  const buffers = {};
  let loading;
  function loadRecordings() {
    if (loading) return loading;
    const a = audioCtx();
    loading = Promise.all(
      Object.entries(RECORDINGS).map(([name, url]) =>
        fetch(url)
          .then((r) => (r.ok ? r.arrayBuffer() : Promise.reject(r.status)))
          // old Safari only has the callback form of decodeAudioData
          .then((data) => new Promise((ok, fail) => a.decodeAudioData(data, ok, fail)))
          .then((buf) => (buffers[name] = buf))
          .catch(() => {}) // a missing file just means that layer stays silent
      )
    );
    return loading;
  }

  function playRecording(name, vol = 0.6) {
    if (muted || !buffers[name]) return false;
    const a = audioCtx();
    const src = a.createBufferSource();
    const g = a.createGain();
    src.buffer = buffers[name];
    g.gain.value = vol;
    src.connect(g).connect(a.destination);
    src.start();
    return true;
  }

  // A looping layer whose volume and speed follow the trains on the board.
  function makeLoop(name) {
    let src = null;
    let gain = null;
    return {
      set(volume, rate) {
        if (!buffers[name] || !audio) return;
        const now = audio.currentTime;
        if (!src && volume > 0) {
          src = audio.createBufferSource();
          src.buffer = buffers[name];
          src.loop = true;
          gain = audio.createGain();
          gain.gain.setValueAtTime(0, now);
          src.connect(gain).connect(audio.destination);
          // start somewhere random so two loops never line up the same way twice
          src.start(now, Math.random() * buffers[name].duration);
        }
        if (!src) return;
        gain.gain.setTargetAtTime(muted ? 0 : volume, now, 0.25);
        src.playbackRate.setTargetAtTime(rate, now, 0.3);
      },
      stop() {
        if (src) {
          try {
            src.stop();
          } catch (_) {}
        }
        src = null;
      },
    };
  }

  const sounds = {
    place: () => tone([520], { type: "triangle", dur: 0.08, vol: 0.15, glide: 1.4 }),
    rotate: () => tone([700], { type: "triangle", dur: 0.06, vol: 0.12, glide: 0.8 }),
    erase: () => tone([300], { type: "sine", dur: 0.1, vol: 0.15, glide: 0.5 }),
    whistle: () => playRecording("whistle", 0.5) || tone([587, 740], { type: "square", dur: 0.5, vol: 0.05 }),
    bump: () => tone([180], { type: "sine", dur: 0.15, vol: 0.12, glide: 0.7 }),
  };

  // ---------- geometry (in cell units; one cell = 1×1) ----------
  const EDGE_POINT = [
    [0.5, 0],
    [1, 0.5],
    [0.5, 1],
    [0, 0.5],
  ];
  // Corner shared by two adjacent edges, the centre of a curve's arc.
  function corner(a, b) {
    const s = new Set([a, b]);
    return [s.has(1) ? 1 : 0, s.has(2) ? 1 : 0];
  }
  const isCurve = (a, b) => a % 2 !== b % 2;
  const segLength = (a, b) => (isCurve(a, b) ? Math.PI / 4 : 1);

  // Point at fraction t along the path from edge a to edge b inside cell (r, c).
  function pointOn(r, c, a, b, t) {
    if (!isCurve(a, b)) {
      const [x0, y0] = EDGE_POINT[a];
      const [x1, y1] = EDGE_POINT[b];
      return [c + x0 + (x1 - x0) * t, r + y0 + (y1 - y0) * t];
    }
    const [cx, cy] = corner(a, b);
    const ang = (e) => Math.atan2(EDGE_POINT[e][1] - cy, EDGE_POINT[e][0] - cx);
    const a0 = ang(a);
    let a1 = ang(b);
    let d = a1 - a0;
    if (d > Math.PI) d -= 2 * Math.PI;
    if (d < -Math.PI) d += 2 * Math.PI;
    const th = a0 + d * t;
    return [c + cx + 0.5 * Math.cos(th), r + cy + 0.5 * Math.sin(th)];
  }

  // ---------- train movement ----------
  // A car is { r, c, a (entry edge), b (exit edge), t (0..1 along the piece), flip }.
  function exitFor(tile, entry) {
    const sw = SWITCHES[baseOf(tile)];
    if (sw) {
      const open = sw.branches[stateOf(tile)];
      if (entry === sw.stem) return open;
      return entry === open ? sw.stem : -1;
    }
    for (const [x, y] of PIECES[baseOf(tile)] || []) {
      if (x === entry) return y;
      if (y === entry) return x;
    }
    return -1;
  }

  function stillOnTrack(grid, car) {
    const tile = grid[car.r] && grid[car.r][car.c];
    return !!tile && hasRoute(tile, car.a, car.b);
  }

  // Moves a car forward by dist cells. Returns false if it ran into the end of the track.
  // routes remembers which way the front car went at each switch, so the cars behind it follow
  // the same way even if the switch is flipped while the train is passing.
  // openSwitch(r, c) is asked (auto mode, front car only) when the car runs into a closed switch;
  // returning true means the switch was flipped open.
  function advance(grid, car, dist, routes, openSwitch) {
    car.t += dist / segLength(car.a, car.b);
    while (car.t >= 1) {
      const leftover = (car.t - 1) * segLength(car.a, car.b);
      const nr = car.r + DR[car.b];
      const nc = car.c + DC[car.b];
      const piece = nr >= 0 && nr < ROWS && nc >= 0 && nc < COLS ? grid[nr][nc] : null;
      const entry = opposite(car.b);
      let exit = piece ? exitFor(piece, entry) : -1;
      if (exit < 0 && isSwitch(piece) && openSwitch && openSwitch(nr, nc)) exit = exitFor(grid[nr][nc], entry);
      if (routes && exit >= 0 && isSwitch(piece)) {
        const key = `${nr},${nc},${entry}`;
        if (routes.has(key)) exit = routes.get(key);
        else routes.set(key, exit);
      }
      if (exit < 0) {
        car.t = 1;
        return false;
      }
      Object.assign(car, { r: nr, c: nc, a: entry, b: exit });
      car.t = leftover / segLength(entry, exit);
    }
    return true;
  }

  function reverseCar(car) {
    [car.a, car.b] = [car.b, car.a];
    car.t = 1 - car.t;
    car.flip = !car.flip;
  }

  function makeTrain(grid, r, c, color) {
    const [a, b] = PIECES[baseOf(grid[r][c])][0];
    const head = { r, c, a, b, t: 0.5, flip: false, loco: true };
    const cars = [head];
    for (let i = 1; i < CARS; i++) {
      const car = { ...cars[i - 1], loco: false };
      reverseCar(car);
      advance(grid, car, CAR_GAP);
      reverseCar(car);
      car.flip = false;
      cars.push(car);
    }
    // the rear locomotive faces backwards; after a turn-around it leads
    Object.assign(cars[cars.length - 1], { loco: true, flip: true });
    return { color, cars, smokeTimer: 0, waiting: 0, blocked: 0, patience: 0, routes: new Map() };
  }

  // ---------- mount ----------
  function mount(container) {
    let grid = loadGrid();
    let trains = [];
    let puffs = [];
    let tool = "draw"; // draw | erase | train | piece
    let piece = "h";
    const kindPiece = Object.fromEntries(KINDS.map((k) => [k.id, k.pieces[0]]));
    let trainColor = 0;
    let speed = "slow";
    let autoSwitch = false;
    const chuffLoop = makeLoop("chuff");
    const railLoop = makeLoop("rail");
    loadRecordings();
    let playing = false; // ▶️ trains run and only switches/trains can be touched; ⏸ build the track
    let cell = 80;
    let ox = 0;
    let oy = 0;
    let raf = 0;
    let last = performance.now();
    let clearArmed = false;

    container.innerHTML = `
      <section class="trk">
        <header class="topbar trk-top">
          <button class="round-btn" data-go="#/" aria-label="처음으로">🏠</button>
          <h1>기찻길 만들기</h1>
          <div class="trk-actions">
            <button class="trk-btn trk-go" data-act="play"></button>
            <button class="trk-btn" data-act="speed" aria-label="속도"></button>
            <button class="trk-btn" data-act="auto"></button>
            <button class="trk-btn" data-act="mute"></button>
            <button class="trk-btn" data-act="example">🎁<span class="lbl"> 예시</span></button>
            <button class="trk-btn trk-edit" data-act="clear"></button>
          </div>
        </header>
        <div class="trk-hint"></div>
        <div class="trk-stage"><canvas class="trk-canvas"></canvas>
          <details class="trk-credits"><summary aria-label="소리 출처">ⓘ</summary>
            소리 출처 (Wikimedia Commons)<br>
            칙칙폭폭: "Steam engine" — aradlaw, 퍼블릭 도메인<br>
            덜컹덜컹: "Train passing by in the Wirikuta Desert" — felix.blume, CC0<br>
            기적: "WWS SteamWhistle" — Work With Sounds / Konrad Gutkowski, CC BY 4.0
          </details>
        </div>
        <nav class="trk-tools">
          <div class="trk-group trk-edit">
            <button class="trk-tool" data-tool="draw"><span>✏️</span>그리기</button>
            <button class="trk-tool" data-tool="erase"><span>🧽</span>지우개</button>
          </div>
          <div class="trk-group trk-edit trk-pieces">
            ${KINDS.map(
              (k) => `<button class="trk-tool trk-piece" data-kind="${k.id}" aria-label="${k.label}"><canvas width="120" height="120"></canvas></button>`
            ).join("")}
          </div>
          <div class="trk-group">
            ${TRAIN_COLORS.map(
              (t, i) => `<button class="trk-tool trk-train" data-train="${i}" aria-label="${t.label}"><canvas width="120" height="120"></canvas></button>`
            ).join("")}
          </div>
        </nav>
      </section>`;

    const root = container.querySelector(".trk");
    const stage = root.querySelector(".trk-stage");
    const canvas = root.querySelector(".trk-canvas");
    const hint = root.querySelector(".trk-hint");
    const ctx = canvas.getContext("2d");

    // Palette icons are drawn with the same code as the board.
    function drawPaletteIcons() {
      root.querySelectorAll(".trk-piece canvas").forEach((cv) => {
        const g = cv.getContext("2d");
        g.setTransform(1, 0, 0, 1, 0, 0);
        g.clearRect(0, 0, 120, 120);
        g.scale(120, 120);
        drawTile(g, 0, 0, kindPiece[cv.parentElement.dataset.kind], 1 / 120);
      });
    }
    drawPaletteIcons();
    root.querySelectorAll(".trk-train canvas").forEach((cv) => {
      const g = cv.getContext("2d");
      g.translate(60, 60);
      g.scale(170, 170);
      drawCar(g, TRAIN_COLORS[cv.parentElement.dataset.train], true, 1 / 170);
    });

    function updateUi() {
      root.querySelectorAll("[data-tool]").forEach((b) => b.classList.toggle("active", tool === b.dataset.tool));
      root.querySelectorAll("[data-kind]").forEach((b) => b.classList.toggle("active", tool === "piece" && kindPiece[b.dataset.kind] === piece));
      root.querySelectorAll("[data-train]").forEach((b) => b.classList.toggle("active", tool === "train" && trainColor === Number(b.dataset.train)));
      root.classList.toggle("playing", playing);
      // emoji + word; on phones only the emoji is shown (the word is in .lbl)
      const label = (act, icon, text) => (root.querySelector(`[data-act="${act}"]`).innerHTML = `${icon}<span class="lbl"> ${text}</span>`);
      label("play", playing ? "⏸" : "▶️", playing ? "멈추고 만들기" : "출발!");
      label("speed", speed === "slow" ? "🐢" : "🐇", speed === "slow" ? "천천히" : "빨리");
      label("auto", "🤖", autoSwitch ? "자동 갈림길 켬" : "자동 갈림길");
      label("clear", "🗑", clearArmed ? "한 번 더!" : "다 지우기");
      root.querySelector('[data-act="clear"]').classList.toggle("armed", clearArmed);
      const autoBtn = root.querySelector('[data-act="auto"]');
      autoBtn.classList.toggle("on", autoSwitch);
      root.querySelector('[data-act="mute"]').textContent = muted ? "🔇" : "🔊";
      const hasTrack = grid.some((row) => row.some(Boolean));
      const hasSwitch = grid.some((row) => row.some(isSwitch));
      hint.textContent = !hasTrack
        ? "✏️ 손가락으로 길을 그려 보세요!"
        : playing && !trains.length
        ? "🚂 아래에서 기차를 고르고 길 위에 놓아요!"
        : playing && hasSwitch
        ? "🔀 갈림길을 톡 누르면 길이 바뀌어요!"
        : playing
        ? ""
        : tool === "train"
        ? "🚂 기차를 놓을 길을 눌러요"
        : "다 만들었으면 ▶️ 출발!을 눌러요";
      // keep the line's height so the board doesn't jump when the hint disappears
      hint.style.visibility = hint.textContent ? "visible" : "hidden";
    }

    // ---------- layout ----------
    // On a tall screen (phone held upright) the wide board is turned a quarter turn so it fills
    // the space; drawing happens in board coordinates and only touches are mapped back.
    let rotated = false;
    let viewW = 0;
    let viewH = 0;
    function resize() {
      const w = stage.clientWidth;
      const h = stage.clientHeight;
      rotated = h > w * 1.1;
      viewW = rotated ? h : w;
      viewH = rotated ? w : h;
      cell = Math.floor(Math.min(viewW / COLS, viewH / ROWS));
      const dpr = window.devicePixelRatio || 1;
      canvas.width = viewW * dpr;
      canvas.height = viewH * dpr;
      canvas.style.width = viewW + "px";
      canvas.style.height = viewH + "px";
      canvas.style.left = (w - viewW) / 2 + "px";
      canvas.style.top = (h - viewH) / 2 + "px";
      canvas.style.transform = rotated ? "rotate(90deg)" : "";
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ox = Math.floor((viewW - cell * COLS) / 2);
      oy = Math.floor((viewH - cell * ROWS) / 2);
    }
    const ro = new ResizeObserver(resize);
    ro.observe(stage);
    resize();

    // ---------- drawing ----------
    function drawTile(g, r, c, tile, px) {
      const sw = SWITCHES[baseOf(tile)];
      if (sw) {
        const on = sw.branches[stateOf(tile)];
        const off = sw.branches[1 - stateOf(tile)];
        g.save();
        g.globalAlpha = 0.35;
        drawRoutes(g, r, c, [[sw.stem, off]], px);
        g.restore();
        // a yellow glow under the open way
        g.save();
        g.beginPath();
        for (let i = 0; i <= 12; i++) {
          const [x, y] = pointOn(r, c, sw.stem, on, i / 12);
          if (i === 0) g.moveTo(x, y);
          else g.lineTo(x, y);
        }
        g.strokeStyle = "rgba(255, 214, 59, 0.75)";
        g.lineWidth = 0.5;
        g.lineCap = "butt";
        g.stroke();
        g.restore();
        drawRoutes(g, r, c, [[sw.stem, on]], px);
        return;
      }
      drawRoutes(g, r, c, PIECES[baseOf(tile)], px);
    }

    function drawRoutes(g, r, c, conns, px) {
      const ties = "#8B5E34";
      const rail = "#7A7F87";
      g.lineCap = "butt";
      // sleepers first, then rails on top
      for (const [a, b] of conns) {
        const n = isCurve(a, b) ? 4 : 5;
        for (let i = 0; i < n; i++) {
          const t = (i + 0.5) / n;
          const [x, y] = pointOn(r, c, a, b, t);
          const [x2, y2] = pointOn(r, c, a, b, Math.min(1, t + 0.01));
          const ang = Math.atan2(y2 - y, x2 - x);
          g.save();
          g.translate(x, y);
          g.rotate(ang);
          g.fillStyle = ties;
          g.fillRect(-0.045, -0.2, 0.09, 0.4);
          g.restore();
        }
      }
      for (const [a, b] of conns) {
        for (const off of [-0.12, 0.12]) {
          g.beginPath();
          const steps = isCurve(a, b) ? 12 : 1;
          for (let i = 0; i <= steps; i++) {
            const t = i / steps;
            const [x, y] = pointOn(r, c, a, b, t);
            const [x2, y2] = pointOn(r, c, a, b, Math.min(1, t + 0.01));
            const [xb, yb] = pointOn(r, c, a, b, Math.max(0, t - 0.01));
            const ang = Math.atan2(y2 - yb, x2 - xb);
            const px2 = x - Math.sin(ang) * off;
            const py2 = y + Math.cos(ang) * off;
            if (i === 0) g.moveTo(px2, py2);
            else g.lineTo(px2, py2);
          }
          g.strokeStyle = rail;
          g.lineWidth = Math.max(0.035, 3 * px);
          g.stroke();
        }
      }
    }

    function drawCar(g, color, loco, px) {
      const L = 0.5;
      const W = 0.3;
      g.fillStyle = "rgba(0,0,0,.18)";
      roundRect(g, -L / 2 + 0.02, -W / 2 + 0.03, L, W, 0.07);
      g.fill();
      g.fillStyle = color.body;
      g.strokeStyle = color.dark;
      g.lineWidth = Math.max(0.02, 2 * px);
      if (loco) {
        // body with a rounded nose pointing forward (+x)
        g.beginPath();
        g.moveTo(-L / 2, -W / 2);
        g.lineTo(L / 2 - 0.1, -W / 2);
        g.quadraticCurveTo(L / 2 + 0.06, 0, L / 2 - 0.1, W / 2);
        g.lineTo(-L / 2, W / 2);
        g.closePath();
        g.fill();
        g.stroke();
        g.fillStyle = "#CDEBFF";
        roundRect(g, -L / 2 + 0.05, -W / 2 + 0.06, 0.14, W - 0.12, 0.03);
        g.fill();
        g.fillStyle = "#333";
        g.beginPath();
        g.arc(0.1, 0, 0.055, 0, Math.PI * 2);
        g.fill();
        g.fillStyle = "#FFE066";
        g.beginPath();
        g.arc(L / 2 - 0.02, 0, 0.03, 0, Math.PI * 2);
        g.fill();
      } else {
        roundRect(g, -L / 2, -W / 2, L, W, 0.06);
        g.fill();
        g.stroke();
        g.fillStyle = "#CDEBFF";
        for (const x of [-0.14, 0.02]) {
          roundRect(g, x, -W / 2 + 0.07, 0.11, W - 0.14, 0.025);
          g.fill();
        }
      }
    }

    function roundRect(g, x, y, w, h, r) {
      g.beginPath();
      g.moveTo(x + r, y);
      g.arcTo(x + w, y, x + w, y + h, r);
      g.arcTo(x + w, y + h, x, y + h, r);
      g.arcTo(x, y + h, x, y, r);
      g.arcTo(x, y, x + w, y, r);
      g.closePath();
    }

    function carPose(car) {
      const [x, y] = pointOn(car.r, car.c, car.a, car.b, car.t);
      const t2 = Math.min(1, car.t + 0.02);
      const t1 = Math.max(0, car.t - 0.02);
      const [xa, ya] = pointOn(car.r, car.c, car.a, car.b, t1);
      const [xb, yb] = pointOn(car.r, car.c, car.a, car.b, t2);
      return { x, y, ang: Math.atan2(yb - ya, xb - xa) + (car.flip ? Math.PI : 0) };
    }

    function render() {
      ctx.clearRect(0, 0, viewW, viewH);
      ctx.save();
      ctx.translate(ox, oy);
      ctx.scale(cell, cell);
      const px = 1 / cell;

      // grass board
      ctx.fillStyle = "#9BD770";
      roundRect(ctx, 0, 0, COLS, ROWS, 0.25);
      ctx.fill();
      ctx.strokeStyle = "rgba(255,255,255,.35)";
      ctx.lineWidth = 1.5 * px;
      ctx.setLineDash([4 * px, 6 * px]);
      ctx.beginPath();
      for (let c = 1; c < COLS; c++) { ctx.moveTo(c, 0.1); ctx.lineTo(c, ROWS - 0.1); }
      for (let r = 1; r < ROWS; r++) { ctx.moveTo(0.1, r); ctx.lineTo(COLS - 0.1, r); }
      ctx.stroke();
      ctx.setLineDash([]);

      for (let r = 0; r < ROWS; r++) for (let c = 0; c < COLS; c++) if (grid[r][c]) drawTile(ctx, r, c, grid[r][c], px);

      for (const train of trains) {
        // draw back to front so the front car is on top
        for (let i = train.cars.length - 1; i >= 0; i--) {
          const car = train.cars[i];
          const { x, y, ang } = carPose(car);
          ctx.save();
          ctx.translate(x, y);
          ctx.rotate(ang);
          drawCar(ctx, TRAIN_COLORS[train.color], car.loco, px);
          ctx.restore();
        }
      }

      for (const p of puffs) {
        ctx.fillStyle = `rgba(255,255,255,${0.75 * (1 - p.age / p.life)})`;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size * (0.6 + p.age / p.life), 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.restore();
    }

    // ---------- simulation ----------
    function step(dt) {
      trains = trains.filter((train) => {
        if (train.cars.every((car) => stillOnTrack(grid, car))) return true;
        const { x, y } = carPose(train.cars[0]);
        for (let i = 0; i < 8; i++) puffs.push({ x: x + (Math.random() - 0.5) * 0.6, y: y + (Math.random() - 0.5) * 0.6, size: 0.12, age: 0, life: 0.6 });
        sounds.erase();
        return false;
      });

      if (playing) {
        const dist = SPEEDS[speed] * dt;
        for (const train of trains) {
          if (train.waiting > 0) {
            train.waiting -= dt;
            if (train.waiting <= 0) turnAround(train);
            continue;
          }

          // 🚦 another train just ahead (or crossing in front): wait; if it stays stuck, go back
          if (trainAhead(train)) {
            if (!train.blocked) train.patience = 1.5 + Math.random() * 1.5; // so two stuck trains don't both turn
            train.blocked += dt;
            if (train.blocked > train.patience) {
              train.blocked = 0;
              turnAround(train);
              sounds.bump();
            }
            continue;
          }
          train.blocked = 0;

          const [head, ...rest] = train.cars;
          const ok = advance(grid, head, dist, train.routes, autoSwitch ? (r, c) => autoOpen(r, c, train) : null);
          for (const car of rest) advance(grid, car, dist, train.routes);

          for (const key of train.routes.keys()) {
            const [kr, kc, entry] = key.split(",").map(Number);
            if (train.cars.some((car) => car.r === kr && car.c === kc)) continue;
            train.routes.delete(key);
            // 🤖 the whole train came through from the stem: send the next one the other way
            const tile = grid[kr][kc];
            if (autoSwitch && isSwitch(tile) && SWITCHES[baseOf(tile)].stem === entry && !occupied(kr, kc, null)) {
              flipTile(kr, kc);
            }
          }
          if (!ok) {
            train.waiting = 0.6;
            sounds.bump();
          }

          // smoke from the leading engine's chimney
          const loco = train.cars[0].loco ? train.cars[0] : null;
          train.smokeTimer -= dt;
          if (loco && train.smokeTimer <= 0) {
            train.smokeTimer = speed === "fast" ? 0.15 : 0.28;
            const { x, y, ang } = carPose(loco);
            puffs.push({ x: x + Math.cos(ang) * 0.1, y: y + Math.sin(ang) * 0.1, size: 0.07, age: 0, life: 1.1 });
          }
        }
      }

      // 칙칙폭폭 and 덜컹덜컹: louder with more trains rolling, faster in 🐇 mode
      const rolling = playing ? trains.filter((t) => t.waiting <= 0 && !t.blocked).length : 0;
      const level = rolling ? 0.35 + 0.15 * Math.min(rolling, 3) : 0;
      const rate = speed === "fast" ? 1.45 : 1;
      chuffLoop.set(level, rate);
      railLoop.set(level * 0.6, rate);

      for (const p of puffs) {
        p.age += dt;
        p.y -= dt * 0.15;
      }
      puffs = puffs.filter((p) => p.age < p.life);
    }

    function turnAround(train) {
      // every car reverses and the last car leads
      train.cars.forEach(reverseCar);
      train.cars.reverse();
    }

    function occupied(r, c, exceptTrain) {
      return trains.some((t) => t !== exceptTrain && t.cars.some((car) => car.r === r && car.c === c));
    }

    function flipTile(r, c) {
      const tile = grid[r][c];
      grid[r][c] = stateOf(tile) ? baseOf(tile) : baseOf(tile) + ":1";
    }

    // Auto mode: open a closed switch for a train arriving at it, unless another train is on it.
    function autoOpen(r, c, train) {
      if (occupied(r, c, train)) return false;
      flipTile(r, c);
      tone([900, 1200], { type: "triangle", dur: 0.06, vol: 0.06 });
      saveGrid(grid);
      return true;
    }

    const SAFE_GAP = 0.6; // centre-to-centre distance (cells) that counts as too close
    const LOOK_AHEAD = 0.7;

    // Is another train on the track just ahead of this train's front car?
    function trainAhead(train) {
      const others = [];
      for (const t of trains) if (t !== train) for (const car of t.cars) others.push(pointOn(car.r, car.c, car.a, car.b, car.t));
      if (!others.length) return false;
      const probe = { ...train.cars[0] };
      const routes = new Map(train.routes);
      for (let d = 0.1; d <= LOOK_AHEAD + 1e-9; d += 0.1) {
        if (!advance(grid, probe, 0.1, routes)) return false;
        const [x, y] = pointOn(probe.r, probe.c, probe.a, probe.b, probe.t);
        if (others.some(([ox2, oy2]) => Math.hypot(ox2 - x, oy2 - y) < SAFE_GAP)) return true;
      }
      return false;
    }


    function frame(now) {
      const dt = Math.min(0.05, (now - last) / 1000);
      last = now;
      step(dt);
      render();
      raf = requestAnimationFrame(frame);
    }
    raf = requestAnimationFrame(frame);

    // ---------- editing ----------
    function cellAt(e) {
      const rect = stage.getBoundingClientRect();
      const dx = e.clientX - (rect.left + rect.width / 2);
      const dy = e.clientY - (rect.top + rect.height / 2);
      // undo the quarter turn: a clockwise rotation maps board (u, v) to screen (-v, u)
      const x = (rotated ? dy : dx) + viewW / 2;
      const y = (rotated ? -dx : dy) + viewH / 2;
      const c = Math.floor((x - ox) / cell);
      const r = Math.floor((y - oy) / cell);
      return r >= 0 && r < ROWS && c >= 0 && c < COLS ? { r, c } : null;
    }

    function commit() {
      saveGrid(grid);
      updateUi();
    }

    // An open end of a neighbouring track that points into (r, c), preferring straight ahead.
    function openEndInto(g, r, c, preferEdges) {
      for (const e of preferEdges) {
        const nr = r + DR[e];
        const nc = c + DC[e];
        if (nr < 0 || nr >= ROWS || nc < 0 || nc >= COLS) continue;
        const p = g[nr][nc];
        if (p && edgesOf(p).has(opposite(e))) return e;
      }
      return -1;
    }

    // An edge the track already in (r, c) uses, in order of preference.
    function existingEdge(g, r, c, preferEdges) {
      const edges = edgesOf(g[r][c]);
      return preferEdges.find((e) => edges.has(e)) ?? -1;
    }

    // What to put in a cell that already has track when a new route a–b is drawn through it.
    function combine(existing, a, b) {
      const want = pieceFor(a, b);
      if (!existing) return want;
      const id = baseOf(existing);
      // straight across a perpendicular straight makes a crossing
      if ((id === "h" && want === "v") || (id === "v" && want === "h") || (id === "x" && (want === "h" || want === "v"))) return "x";
      if (hasRoute(existing, a, b)) return existing;
      const edges = edgesOf(existing);
      edges.add(a);
      edges.add(b);
      if (edges.size === 3) {
        // branching off existing track: a switch that keeps the old route(s) and adds the new one
        const fits = Object.keys(SWITCHES).filter((sid) => hasRoute(sid, a, b) && [...edges].every((e) => edgesOf(sid).has(e)));
        const keeps = fits.find((sid) => PIECES[id].every(([x, y]) => hasRoute(sid, x, y)));
        if (keeps || fits[0]) return keeps || fits[0];
      }
      return want;
    }

    // Lay track along a finger path of orthogonally adjacent cells.
    function layPath(base, path) {
      const g = base.map((row) => row.slice());
      // Finger came back to where it started: join the two ends into a loop.
      const closed = path.length >= 5 && same(path[0], path[path.length - 1]);
      const cells = closed ? path.slice(0, -1) : path;
      cells.forEach(({ r, c }, i) => {
        const prev = closed && i === 0 ? cells[cells.length - 1] : cells[i - 1];
        const next = closed && i === cells.length - 1 ? cells[0] : cells[i + 1];
        const toPrev = prev ? dirTo({ r, c }, prev) : -1;
        const toNext = next ? dirTo({ r, c }, next) : -1;
        let a = toPrev;
        let b = toNext;
        if (a < 0 && b >= 0) {
          // first cell: branch off the track already here, or join a neighbouring track end,
          // else run straight
          const prefer = [opposite(b), (b + 1) % 4, (b + 3) % 4];
          a = g[r][c] ? existingEdge(g, r, c, prefer) : openEndInto(g, r, c, prefer);
          if (a < 0) a = opposite(b);
        } else if (b < 0 && a >= 0) {
          // last cell: likewise, which lets kids close a loop or join a line by drawing into it
          const prefer = [opposite(a), (a + 1) % 4, (a + 3) % 4];
          b = g[r][c] ? existingEdge(g, r, c, prefer) : openEndInto(g, r, c, prefer);
          if (b < 0) b = opposite(a);
        } else if (a < 0 && b < 0) {
          return;
        }
        g[r][c] = combine(g[r][c], a, b);
      });
      return g;
    }

    const same = (a, b) => a.r === b.r && a.c === b.c;

    function dirTo(from, to) {
      if (to.r < from.r) return 0;
      if (to.c > from.c) return 1;
      if (to.r > from.r) return 2;
      return 3;
    }

    // Cells between two cells, stepping only up/down/left/right (fast swipes skip cells).
    function cellsBetween(a, b) {
      const out = [];
      let { r, c } = a;
      while (r !== b.r || c !== b.c) {
        if (Math.abs(b.c - c) >= Math.abs(b.r - r)) c += Math.sign(b.c - c);
        else r += Math.sign(b.r - r);
        out.push({ r, c });
      }
      return out;
    }

    let drag = null; // { base, path, lastCell }

    function onDown(e) {
      const at = cellAt(e);
      if (!at) return;
      canvas.setPointerCapture(e.pointerId);
      clearArmed = false;

      if (playing || tool === "train") {
        if (!grid[at.r][at.c]) return;
        if (isSwitch(grid[at.r][at.c])) {
          flipSwitch(at);
          return;
        }
        const hit = trains.findIndex((t) => t.cars.some((car) => car.r === at.r && car.c === at.c));
        if (hit >= 0) {
          trains.splice(hit, 1);
          sounds.erase();
        } else {
          if (trains.length >= MAX_TRAINS) trains.shift();
          trains.push(makeTrain(grid, at.r, at.c, trainColor));
          sounds.whistle();
        }
        updateUi();
        return;
      }

      if (tool === "erase") {
        drag = { lastCell: at };
        if (grid[at.r][at.c]) {
          grid[at.r][at.c] = null;
          sounds.erase();
        }
        return;
      }

      if (tool === "piece") {
        drag = { lastCell: at, moved: false };
        if (grid[at.r][at.c]) {
          drag.rotateOnUp = at; // a tap (not a drag) on a placed piece turns it
        } else {
          grid[at.r][at.c] = piece;
          sounds.place();
        }
        return;
      }

      // draw (a tap without moving flips a switch)
      drag = { base: grid.map((row) => row.slice()), path: [at], lastCell: at, moved: false };
      grid = layPath(drag.base, drag.path);
    }

    function onMove(e) {
      if (!drag) return;
      const at = cellAt(e);
      if (!at || (at.r === drag.lastCell.r && at.c === drag.lastCell.c)) return;
      const steps = cellsBetween(drag.lastCell, at);
      drag.lastCell = at;
      drag.moved = true;

      for (const s of steps) {
        if (tool === "erase") {
          if (grid[s.r][s.c]) {
            grid[s.r][s.c] = null;
            sounds.erase();
          }
        } else if (tool === "piece") {
          if (!grid[s.r][s.c]) {
            grid[s.r][s.c] = piece;
            sounds.place();
          }
        } else {
          const path = drag.path;
          const back = path[path.length - 2];
          if (back && back.r === s.r && back.c === s.c) path.pop(); // finger went back: undo
          else if (same(path[path.length - 1], path[0]) && path.length > 1) {
            // loop already closed; ignore further movement in this stroke
          } else if (!path.some((p) => same(p, s)) || isLoopClose(path, s) || (same(s, path[0]) && path.length >= 4)) {
            path.push(s);
            sounds.place();
          }
          grid = layPath(drag.base, path);
        }
      }
    }

    // Allow passing through a cell already in the path only to make a crossing, never to fold back.
    function isLoopClose(path, s) {
      const prev = path[path.length - 1];
      const i = path.findIndex((p) => p.r === s.r && p.c === s.c);
      if (i <= 0 || i >= path.length - 1) return false;
      const before = path[i - 1];
      const after = path[i + 1];
      const throughOld = dirTo(before, path[i]) % 2; // 0 = vertical, 1 = horizontal
      const throughNew = dirTo(prev, s) % 2;
      return dirTo(before, path[i]) === dirTo(path[i], after) && throughOld !== throughNew;
    }

    function flipSwitch({ r, c }) {
      const tile = grid[r][c];
      grid[r][c] = stateOf(tile) ? baseOf(tile) : baseOf(tile) + ":1";
      tone([900, 1200], { type: "triangle", dur: 0.08, vol: 0.1 });
      commit();
    }

    function onUp() {
      if (!drag) return;
      if (tool === "piece" && drag.rotateOnUp && !drag.moved) {
        const { r, c } = drag.rotateOnUp;
        const tile = grid[r][c];
        grid[r][c] = ROTATE[baseOf(tile)] + (stateOf(tile) ? ":1" : "");
        sounds.rotate();
      }
      if (tool === "draw" && !drag.moved && isSwitch(grid[drag.lastCell.r][drag.lastCell.c])) {
        flipSwitch(drag.lastCell);
      }
      drag = null;
      commit();
    }

    canvas.addEventListener("pointerdown", onDown);
    canvas.addEventListener("pointermove", onMove);
    canvas.addEventListener("pointerup", onUp);
    canvas.addEventListener("pointercancel", onUp);

    root.addEventListener("click", (e) => {
      const b = e.target.closest("button");
      if (!b) return;
      if (b.dataset.act !== "clear") clearArmed = false;
      if (b.dataset.tool) tool = b.dataset.tool;
      if (b.dataset.kind) {
        const k = b.dataset.kind;
        // tapping the selected piece again turns it
        if (tool === "piece" && piece === kindPiece[k]) kindPiece[k] = ROTATE[kindPiece[k]];
        tool = "piece";
        piece = kindPiece[k];
        drawPaletteIcons();
      }
      if (b.dataset.train !== undefined) {
        tool = "train";
        trainColor = Number(b.dataset.train);
      }
      if (b.dataset.act === "play") {
        playing = !playing;
        if (playing) {
          // only trains can be picked while running
          if (tool !== "train") tool = "train";
          sounds.whistle();
        } else {
          tool = "draw";
        }
      }
      if (b.dataset.act === "speed") speed = speed === "slow" ? "fast" : "slow";
      if (b.dataset.act === "auto") autoSwitch = !autoSwitch;
      if (b.dataset.act === "mute") {
        muted = !muted;
        try {
          localStorage.setItem("jaytrain.muted", muted ? "1" : "0");
        } catch (_) {}
      }
      if (b.dataset.act === "example") {
        grid = exampleGrid();
        trains = [makeTrain(grid, 1, 4, 0), makeTrain(grid, 3, 5, 1)];
        turnAround(trains[0]); // heads towards the switch from its stem side, so the siding gets used
        playing = true;
        tool = "train";
        sounds.whistle();
        commit();
      }
      if (b.dataset.act === "clear") {
        if (clearArmed) {
          grid = emptyGrid();
          trains = [];
          clearArmed = false;
          sounds.erase();
          commit();
        } else {
          clearArmed = true; // kids tap things; ask for a second tap instead of a dialog
        }
      }
      if (b.dataset.tool || b.dataset.kind || b.dataset.train !== undefined) sounds.rotate();
      updateUi();
    });

    updateUi();

    // For console checks: run the simulation without waiting for animation frames.
    window.TrackGame._debug = {
      step,
      get: () => ({ grid, trains, playing, autoSwitch, sounds: Object.keys(buffers) }),
      set: (o) => {
        if (o.trains) trains = o.trains.map(([r, c, color]) => makeTrain(grid, r, c, color));
        if ("autoSwitch" in o) autoSwitch = o.autoSwitch;
        if ("playing" in o) playing = o.playing;
        if ("muted" in o) muted = o.muted;
      },
    };

    return function unmount() {
      cancelAnimationFrame(raf);
      chuffLoop.stop();
      railLoop.stop();
      ro.disconnect();
    };
  }

  // Exposed for quick checks from the console; the game itself only uses mount().
  window.TrackGame = { mount, _sim: { PIECES, SWITCHES, pointOn, exampleGrid, emptyGrid, makeTrain, advance, stillOnTrack, reverseCar } };
})();
