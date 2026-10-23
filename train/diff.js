"use strict";

// 틀린그림찾기: a train photo from the encyclopedia and a copy with five changes made on a <canvas>.
// Changes go where the photo has detail (the train, windows, signs), never on flat sky or ground,
// and each one is checked to be clearly visible before it is kept.
// Exposes window.DiffGame.mount(container, { trains, media }) → returns an unmount function.
(function () {
  const W = 800;
  const H = 600;
  const DIFFS_PER_PICTURE = 5;
  const MAX_HINTS = 2;
  const RADIUS = 62; // ≈ 7.8% of the width: big enough for small fingers and eyes
  const TAP_REACH = 1.4; // a tap counts within 140% of the radius
  const MIN_GAP = 2.6; // spot centres at least this many radii apart
  const ROOT = new URL(".", (document.currentScript && document.currentScript.src) || location.href);
  const TYPE_EMOJI = { highspeed: "🚄", intercity: "🚆", metro: "🚇", tram: "🚋", monorail: "🚝", scenic: "🏔️", steam: "🚂", special: "🔧" };
  const STICKERS = ["🐦", "🌸", "⭐", "🎈", "☁️", "🦋", "🍎", "🐱"];

  // ---------- sounds (same style and mute setting as the other games) ----------
  let audio;
  const isMuted = () => {
    try {
      return localStorage.getItem("jaytrain.muted") === "1";
    } catch (_) {
      return false;
    }
  };
  function tone(freqs, { type = "sine", dur = 0.12, vol = 0.12, glide, delay = 0 } = {}) {
    if (isMuted()) return;
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
        g.gain.exponentialRampToValueAtTime(vol, now + 0.015);
        g.gain.exponentialRampToValueAtTime(0.0001, now + dur);
        o.connect(g).connect(audio.destination);
        o.start(now);
        o.stop(now + dur + 0.02);
      }
    } catch (_) {}
  }
  const sounds = {
    found: () => {
      tone([784], { type: "triangle", dur: 0.12, vol: 0.13 });
      tone([1175], { type: "triangle", dur: 0.18, vol: 0.13, delay: 0.1 });
    },
    miss: () => tone([220], { type: "sine", dur: 0.16, vol: 0.09, glide: 0.8 }),
    hint: () => tone([660, 880], { type: "sine", dur: 0.25, vol: 0.06 }),
    tap: () => tone([620], { type: "triangle", dur: 0.06, vol: 0.1, glide: 1.3 }),
    clear: () => [523, 659, 784, 1047].forEach((f, i) => tone([f], { type: "triangle", dur: 0.22, vol: 0.12, delay: i * 0.12 })),
  };

  // ---------- data ----------
  let dataPromise = null;
  function loadData() {
    if (!dataPromise) {
      dataPromise = Promise.all([
        fetch(new URL("data/trains.json", ROOT)).then((r) => r.json()),
        fetch(new URL("data/media.json", ROOT)).then((r) => r.json()),
      ]).then(([t, media]) => ({ trains: t.trains, media }));
    }
    return dataPromise;
  }

  const photoOf = (media, train) => {
    const imgs = (media[train.id] && media[train.id].images) || [];
    return imgs.length ? imgs[0].src : null;
  };

  function shuffle(list) {
    const a = list.slice();
    for (let i = a.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
  }

  // ---------- image helpers ----------
  const canvas = (w = W, h = H) => {
    const c = document.createElement("canvas");
    c.width = w;
    c.height = h;
    return c;
  };

  function loadImage(src) {
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => resolve(img);
      img.onerror = () => reject(new Error("image failed: " + src));
      img.src = new URL(src, ROOT).href;
    });
  }

  // centre-crop to 4:3 into an 800×600 canvas
  function cropToCanvas(img) {
    const c = canvas();
    const ratio = W / H;
    let sw = img.naturalWidth;
    let sh = img.naturalHeight;
    if (sw / sh > ratio) sw = sh * ratio;
    else sh = sw / ratio;
    const sx = (img.naturalWidth - sw) / 2;
    const sy = (img.naturalHeight - sh) / 2;
    c.getContext("2d").drawImage(img, sx, sy, sw, sh, 0, 0, W, H);
    return c;
  }

  // Edge strength on an 80×60 grid (one cell = 10 px), as a summed-area table for fast box means.
  // The coarse grid is deliberate: thin overhead wires and gravel average out, while the big
  // shapes of a train (windows, doors, stripes, the nose) still stand out.
  const CELL = 10;
  const GW = W / CELL;
  const GH = H / CELL;
  function detailMap(src) {
    const small = canvas(GW, GH);
    const g = small.getContext("2d");
    g.drawImage(src, 0, 0, GW, GH);
    const d = g.getImageData(0, 0, GW, GH).data;
    const gray = new Float32Array(GW * GH);
    for (let i = 0; i < GW * GH; i++) gray[i] = 0.299 * d[i * 4] + 0.587 * d[i * 4 + 1] + 0.114 * d[i * 4 + 2];
    const mag = new Float32Array(GW * GH);
    for (let y = 1; y < GH - 1; y++) {
      for (let x = 1; x < GW - 1; x++) {
        const p = (yy, xx) => gray[yy * GW + xx];
        const gx = p(y - 1, x + 1) + 2 * p(y, x + 1) + p(y + 1, x + 1) - p(y - 1, x - 1) - 2 * p(y, x - 1) - p(y + 1, x - 1);
        const gy = p(y + 1, x - 1) + 2 * p(y + 1, x) + p(y + 1, x + 1) - p(y - 1, x - 1) - 2 * p(y - 1, x) - p(y - 1, x + 1);
        mag[y * GW + x] = Math.hypot(gx, gy);
      }
    }
    const sat = new Float64Array((GW + 1) * (GH + 1));
    for (let y = 0; y < GH; y++) {
      let row = 0;
      for (let x = 0; x < GW; x++) {
        row += mag[y * GW + x];
        sat[(y + 1) * (GW + 1) + x + 1] = sat[y * (GW + 1) + x + 1] + row;
      }
    }
    // mean colour in a box, used to find a look-alike patch for 지우기
    const color = (cx, cy, r) => {
      const x0 = Math.max(0, Math.floor((cx - r) / CELL));
      const y0 = Math.max(0, Math.floor((cy - r) / CELL));
      const x1 = Math.min(GW, Math.ceil((cx + r) / CELL));
      const y1 = Math.min(GH, Math.ceil((cy + r) / CELL));
      const c = [0, 0, 0];
      let n = 0;
      for (let y = y0; y < y1; y++) {
        for (let x = x0; x < x1; x++) {
          const i = (y * GW + x) * 4;
          c[0] += d[i];
          c[1] += d[i + 1];
          c[2] += d[i + 2];
          n++;
        }
      }
      return c.map((v) => v / Math.max(1, n));
    };
    // mean edge strength in a box of half-size r (canvas px) around (cx, cy)
    const edges = (cx, cy, r) => {
      const x0 = Math.max(0, Math.floor((cx - r) / CELL));
      const y0 = Math.max(0, Math.floor((cy - r) / CELL));
      const x1 = Math.min(GW, Math.ceil((cx + r) / CELL));
      const y1 = Math.min(GH, Math.ceil((cy + r) / CELL));
      const s = sat[y1 * (GW + 1) + x1] - sat[y0 * (GW + 1) + x1] - sat[y1 * (GW + 1) + x0] + sat[y0 * (GW + 1) + x0];
      return s / Math.max(1, (x1 - x0) * (y1 - y0));
    };
    edges.color = color;
    return edges;
  }

  // Trains sit in the middle band of these photos; sky (top) and track bed (bottom) score lower.
  function bandWeight(cy) {
    const t = cy / H;
    if (t < 0.22) return 0.35 + (t / 0.22) * 0.45;
    if (t > 0.82) return 1 - ((t - 0.82) / 0.18) * 0.5;
    return 1;
  }

  // Draws `patch` (2r × 2r) onto ctx at the spot through a soft round mask.
  function stampSoft(ctx, patch, cx, cy, r) {
    const pc = patch.getContext("2d");
    pc.globalCompositeOperation = "destination-in";
    const grad = pc.createRadialGradient(r, r, r * 0.72, r, r, r);
    grad.addColorStop(0, "rgba(0,0,0,1)");
    grad.addColorStop(1, "rgba(0,0,0,0)");
    pc.fillStyle = grad;
    pc.fillRect(0, 0, 2 * r, 2 * r);
    ctx.drawImage(patch, cx - r, cy - r);
  }

  // mean absolute RGB difference inside 80% of the circle
  function visibleChange(a, b, cx, cy, r) {
    const x0 = Math.round(cx - r);
    const y0 = Math.round(cy - r);
    const size = Math.round(2 * r);
    const da = a.getContext("2d").getImageData(x0, y0, size, size).data;
    const db = b.getContext("2d").getImageData(x0, y0, size, size).data;
    const rr = (r * 0.8) ** 2;
    let sum = 0;
    let n = 0;
    for (let y = 0; y < size; y++) {
      for (let x = 0; x < size; x++) {
        if ((x - r) ** 2 + (y - r) ** 2 > rr) continue;
        const i = (y * size + x) * 4;
        sum += Math.abs(da[i] - db[i]) + Math.abs(da[i + 1] - db[i + 1]) + Math.abs(da[i + 2] - db[i + 2]);
        n += 3;
      }
    }
    return n ? sum / n : 0;
  }

  function rgbToHsl(r, g, b) {
    r /= 255;
    g /= 255;
    b /= 255;
    const max = Math.max(r, g, b);
    const min = Math.min(r, g, b);
    const l = (max + min) / 2;
    if (max === min) return [0, 0, l];
    const d = max - min;
    const s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
    let h;
    if (max === r) h = (g - b) / d + (g < b ? 6 : 0);
    else if (max === g) h = (b - r) / d + 2;
    else h = (r - g) / d + 4;
    return [h / 6, s, l];
  }
  function hslToRgb(h, s, l) {
    if (s === 0) return [l * 255, l * 255, l * 255];
    const hue = (p, q, t) => {
      if (t < 0) t += 1;
      if (t > 1) t -= 1;
      if (t < 1 / 6) return p + (q - p) * 6 * t;
      if (t < 1 / 2) return q;
      if (t < 2 / 3) return p + (q - p) * (2 / 3 - t) * 6;
      return p;
    };
    const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
    const p = 2 * l - q;
    return [hue(p, q, h + 1 / 3) * 255, hue(p, q, h) * 255, hue(p, q, h - 1 / 3) * 255];
  }

  // ---------- the five kinds of change ----------
  // Each takes the working canvas and a spot, returns a 2r×2r patch canvas (or null) to stamp.
  const CHANGES = {
    // 색 바꾸기: colourful areas get their hue turned around; grey ones get a vivid tint
    color(src, s) {
      const r = s.r;
      const p = canvas(2 * r, 2 * r);
      const pc = p.getContext("2d");
      pc.drawImage(src, s.cx - r, s.cy - r, 2 * r, 2 * r, 0, 0, 2 * r, 2 * r);
      const img = pc.getImageData(0, 0, 2 * r, 2 * r);
      const d = img.data;
      let satSum = 0;
      for (let i = 0; i < d.length; i += 4) satSum += rgbToHsl(d[i], d[i + 1], d[i + 2])[1];
      const colorful = satSum / (d.length / 4) > 0.22;
      const tint = [[232, 69, 60], [47, 125, 225], [255, 196, 0], [46, 166, 90], [160, 80, 220]][Math.floor(Math.random() * 5)];
      const turn = 0.4 + Math.random() * 0.2; // 144°–216°
      for (let i = 0; i < d.length; i += 4) {
        if (colorful) {
          const [h, sat, l] = rgbToHsl(d[i], d[i + 1], d[i + 2]);
          const [nr, ng, nb] = hslToRgb((h + turn) % 1, Math.min(1, sat * 1.3 + 0.1), l);
          d[i] = nr;
          d[i + 1] = ng;
          d[i + 2] = nb;
        } else {
          const lum = (0.299 * d[i] + 0.587 * d[i + 1] + 0.114 * d[i + 2]) / 255;
          const k = 0.35 + lum * 0.75;
          d[i] = d[i] * 0.3 + tint[0] * k * 0.7;
          d[i + 1] = d[i + 1] * 0.3 + tint[1] * k * 0.7;
          d[i + 2] = d[i + 2] * 0.3 + tint[2] * k * 0.7;
        }
      }
      pc.putImageData(img, 0, 0);
      return p;
    },

    // 지우기: cover the spot with a plain-looking piece from nearby (something disappears)
    erase(src, s, ctx) {
      const r = s.r;
      let best = null;
      for (let k = 0; k < 16; k++) {
        const a = (k / 16) * Math.PI * 2;
        for (const dist of [2.1, 2.6, 3.2]) {
          const x = s.cx + Math.cos(a) * r * dist;
          const y = s.cy + Math.sin(a) * r * dist;
          if (x - r < 0 || y - r < 0 || x + r > W || y + r > H) continue;
          if (ctx.taken.some((t) => Math.hypot(t.cx - x, t.cy - y) < (t.r + r) * 1.05)) continue;
          const a1 = ctx.detail.color(x, y, r * 0.8);
          const a0 = ctx.detail.color(s.cx, s.cy, r * 0.8);
          const colorGap = Math.abs(a1[0] - a0[0]) + Math.abs(a1[1] - a0[1]) + Math.abs(a1[2] - a0[2]);
          if (colorGap > 90) continue; // a patch of a different colour would look like a smudge
          const score = ctx.detail(x, y, r * 0.8);
          if (!best || score < best.score) best = { x, y, score };
        }
      }
      if (!best || best.score > ctx.detail(s.cx, s.cy, r * 0.8) * 0.6) return null;
      const p = canvas(2 * r, 2 * r);
      p.getContext("2d").drawImage(src, best.x - r, best.y - r, 2 * r, 2 * r, 0, 0, 2 * r, 2 * r);
      return p;
    },

    // 붙이기: a cute sticker that wasn't there
    sticker(src, s, ctx) {
      const r = s.r;
      const p = canvas(2 * r, 2 * r);
      const pc = p.getContext("2d");
      pc.drawImage(src, s.cx - r, s.cy - r, 2 * r, 2 * r, 0, 0, 2 * r, 2 * r);
      const unused = STICKERS.filter((e) => !ctx.taken.some((t) => t.sticker === e));
      const emoji = unused[Math.floor(Math.random() * unused.length)];
      pc.font = `${Math.round(r * 1.25)}px "Apple Color Emoji","Segoe UI Emoji","Noto Color Emoji",sans-serif`;
      pc.textAlign = "center";
      pc.textBaseline = "middle";
      // white halo so the sticker reads on dark and busy backgrounds
      pc.shadowColor = "rgba(255,255,255,0.95)";
      pc.shadowBlur = 8;
      for (let i = 0; i < 3; i++) pc.fillText(emoji, r, r + r * 0.05);
      pc.shadowColor = "transparent";
      pc.fillText(emoji, r, r + r * 0.05);
      s.sticker = emoji;
      return p;
    },

    // 뒤집기: the round piece mirrored left–right
    flip(src, s) {
      const r = s.r;
      const p = canvas(2 * r, 2 * r);
      const pc = p.getContext("2d");
      pc.translate(2 * r, 0);
      pc.scale(-1, 1);
      pc.drawImage(src, s.cx - r, s.cy - r, 2 * r, 2 * r, 0, 0, 2 * r, 2 * r);
      return p;
    },

    // 크게: the middle of the spot blown up 1.6×
    zoom(src, s) {
      const r = s.r;
      const q = r / 1.6;
      const p = canvas(2 * r, 2 * r);
      p.getContext("2d").drawImage(src, s.cx - q, s.cy - q, 2 * q, 2 * q, 0, 0, 2 * r, 2 * r);
      return p;
    },
  };
  // how much a change must alter the pixels (mean |ΔRGB|, 0–255) to count as easy to see
  const MIN_VISIBLE = { color: 38, erase: 30, sticker: 0, flip: 55, zoom: 62 };
  const KIND_LABEL = { color: "색 바꾸기", erase: "지우기", sticker: "붙이기", flip: "뒤집기", zoom: "크게" };

  // ---------- one puzzle from one photo ----------
  async function makePuzzle(train, src) {
    const img = await loadImage(src);
    const left = cropToCanvas(img);
    const right = canvas();
    const rctx = right.getContext("2d");
    rctx.drawImage(left, 0, 0);
    const detail = detailMap(left);

    // candidate centres on a grid, best detail first
    const r = RADIUS;
    const margin = r + 8;
    const cands = [];
    for (let y = margin; y <= H - margin; y += 20) {
      for (let x = margin; x <= W - margin; x += 20) cands.push({ cx: x, cy: y, score: detail(x, y, r * 0.8) * bandWeight(y) });
    }
    cands.sort((a, b) => b.score - a.score);
    const top = cands[0] ? cands[0].score : 0;
    const floor = Math.max(top * 0.28, cands[Math.floor(cands.length / 2)].score * 1.05);

    const spots = [];
    // mirror-flips are the hardest to spot, so they're only a fallback
    const kinds = shuffle(["color", "sticker", "erase", "zoom"]);
    const ctx = { detail, taken: spots };
    for (const c of cands) {
      if (spots.length >= DIFFS_PER_PICTURE) break;
      if (c.score < floor) break;
      if (spots.some((s) => Math.hypot(s.cx - c.cx, s.cy - c.cy) < MIN_GAP * r)) continue;
      // try the kinds not used yet first, then any
      const unused = kinds.filter((k) => !spots.some((s) => s.kind === k));
      const order = [...unused, ...kinds.filter((k) => !unused.includes(k)), "flip"];
      for (const kind of order) {
        if (kind === "erase" && spots.some((s) => s.kind === "erase")) continue;
        const spot = { cx: c.cx, cy: c.cy, r, kind };
        const before = canvas();
        before.getContext("2d").drawImage(right, 0, 0);
        const patch = CHANGES[kind](right, spot, ctx);
        if (!patch) continue;
        stampSoft(rctx, patch, spot.cx, spot.cy, r);
        const change = visibleChange(left, right, spot.cx, spot.cy, r);
        if (change >= MIN_VISIBLE[kind]) {
          spot.change = Math.round(change);
          spot.id = spots.length;
          spots.push(spot);
          break;
        }
        rctx.clearRect(0, 0, W, H);
        rctx.drawImage(before, 0, 0); // not visible enough: undo and try the next kind
      }
    }
    if (spots.length < DIFFS_PER_PICTURE) throw new Error(`only ${spots.length} good spots in ${train.id}`);
    return {
      train,
      spots,
      left: left.toDataURL("image/jpeg", 0.9),
      right: right.toDataURL("image/jpeg", 0.9),
    };
  }

  // ---------- stages ----------
  // Prepared pairs (photo + AI-edited copy) live in data/diffs.json:
  //   [{ "id": "ktx", "left": "assets/diff/ktx/a.jpg", "right": "assets/diff/ktx/b.jpg",
  //      "w": 1536, "h": 1024, "spots": [{ "cx": 300, "cy": 420, "r": 70 }, …] }]
  // Until there are any, these trains are stages with automatically made changes instead.
  const FALLBACK_STAGES = ["ktx", "ktx-sancheon", "srt", "shinkansen-0", "e5-hayabusa", "doctor-yellow", "tgv", "ice", "e6-komachi", "sf-cable-car"];
  const CLEARED_KEY = "jaytrain.diff.cleared";

  function loadCleared() {
    try {
      return new Set(JSON.parse(localStorage.getItem(CLEARED_KEY)) || []);
    } catch (_) {
      return new Set();
    }
  }
  function saveCleared(set) {
    try {
      localStorage.setItem(CLEARED_KEY, JSON.stringify([...set]));
    } catch (_) {}
  }

  async function loadStages(data) {
    let prepared = [];
    try {
      const r = await fetch(new URL("data/diffs.json", ROOT), { cache: "no-cache" });
      if (r.ok) prepared = await r.json();
    } catch (_) {}
    const byId = new Map(data.trains.map((t) => [t.id, t]));
    const ready = new Map(prepared.filter((p) => byId.has(p.id)).map((p) => [p.id, p]));
    // prepared pictures first, then the trains still waiting for theirs
    const ids = [...ready.keys(), ...FALLBACK_STAGES.filter((id) => !ready.has(id))];
    return ids
      .filter((id) => byId.has(id) && (ready.has(id) || photoOf(data.media, byId.get(id))))
      .map((id) => ({
        id,
        train: byId.get(id),
        thumb: ready.has(id) ? ready.get(id).left : `assets/trains/${id}/thumb.jpg`,
        prepared: ready.get(id) || null,
      }));
  }

  // The right picture = the original, with the edited picture used only inside each answer's
  // area. An AI edit also redraws the whole photo slightly and sometimes changes extra things;
  // this keeps exactly the five intended differences. Edges are feathered so no seam shows.
  async function composeRight(p) {
    const [orig, edited] = await Promise.all([loadImage(new URL(p.left, ROOT).href), loadImage(new URL(p.right, ROOT).href)]);
    const out = canvas(p.w, p.h);
    const ctx = out.getContext("2d");
    ctx.drawImage(orig, 0, 0, p.w, p.h);
    const FEATHER = 18;
    for (const s of p.spots) {
      const [x, y, w, h] = s.area || [s.cx - s.r, s.cy - s.r, s.r * 2, s.r * 2];
      const patch = canvas(p.w, p.h);
      const pc = patch.getContext("2d");
      // soft-edged mask: full strength over the whole area, fading out just outside it,
      // so nothing inside the answer (a cart's wheels, a sign's corner) gets mixed with the original
      for (let i = FEATHER; i >= 0; i -= 2) {
        pc.fillStyle = `rgba(0,0,0,${i === 0 ? 1 : 0.18})`;
        pc.beginPath();
        pc.roundRect(x - i, y - i, w + 2 * i, h + 2 * i, 8 + i);
        pc.fill();
      }
      pc.globalCompositeOperation = "source-in";
      pc.drawImage(edited, 0, 0, p.w, p.h);
      ctx.drawImage(patch, 0, 0);
    }
    return out.toDataURL("image/jpeg", 0.92);
  }

  // A stage's puzzle: the prepared pair, or one made now from the train's photo.
  async function puzzleFor(stage, data) {
    const p = stage.prepared;
    if (p) {
      return {
        train: stage.train,
        w: p.w,
        h: p.h,
        left: new URL(p.left, ROOT).href,
        right: await composeRight(p),
        // circles are drawn tightly around each real change, so only a little leeway is added
        spots: p.spots.map((s, i) => ({ ...s, id: i, reach: s.reach || 1.15 })),
      };
    }
    const pz = await makePuzzle(stage.train, photoOf(data.media, stage.train));
    return { ...pz, w: W, h: H };
  }

  // ---------- mount ----------
  function mount(container, opts = {}) {
    let data = opts.trains && opts.media ? { trains: opts.trains, media: opts.media } : null;
    let stages = [];
    let cleared = loadCleared();
    let current = -1; // index into stages while playing
    let puzzle = null;
    let pw = W;
    let ph = H;
    let found = new Set();
    let hintsLeft = MAX_HINTS;
    let lastTap = 0;
    let done = true;
    let alive = true;
    const timers = new Set();
    const later = (fn, ms) => {
      const t = setTimeout(() => {
        timers.delete(t);
        fn();
      }, ms);
      timers.add(t);
    };

    container.innerHTML = `
      <section class="dif">
        <header class="topbar dif-top">
          <button class="round-btn" data-go="#/" aria-label="처음으로">🏠</button>
          <button class="round-btn dif-back" data-act="list" aria-label="그림 고르기" hidden>←</button>
          <h1>틀린그림찾기</h1>
          <span class="dif-progress"></span>
          <span class="dif-dots" aria-hidden="true"></span>
        </header>
        <div class="dif-list" hidden></div>
        <div class="dif-play" hidden>
          <div class="dif-bar">
            <span class="dif-name"></span>
            <span class="dif-count"></span>
            <button class="dif-hint" data-act="hint">💡 힌트</button>
          </div>
          <div class="dif-board">
            <div class="dif-pic"><svg data-side="L"></svg></div>
            <div class="dif-pic"><svg data-side="R"></svg></div>
            <div class="dif-loading" hidden>그림 준비 중… 🚂</div>
          </div>
        </div>
      </section>`;
    const root = container.querySelector(".dif");
    const list = root.querySelector(".dif-list");
    const play = root.querySelector(".dif-play");
    const board = root.querySelector(".dif-board");
    const pics = [...root.querySelectorAll(".dif-pic")];
    const svgs = [...root.querySelectorAll(".dif-pic svg")];
    const loading = root.querySelector(".dif-loading");
    const back = root.querySelector(".dif-back");

    const svgEl = (tag, attrs) => {
      const el = document.createElementNS("http://www.w3.org/2000/svg", tag);
      for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
      return el;
    };

    // ----- stage list: every picture as a thumbnail, cleared ones marked -----
    function showList() {
      root.querySelector(".dif-clear")?.remove();
      done = true;
      current = -1;
      play.hidden = true;
      list.hidden = false;
      back.hidden = true;
      root.querySelector(".dif-dots").innerHTML = "";
      const n = stages.filter((s) => cleared.has(s.id)).length;
      root.querySelector(".dif-progress").textContent = stages.length ? `✅ ${n} / ${stages.length}` : "";
      list.innerHTML = stages.length
        ? `<p class="dif-ask">어떤 그림을 할까요? 다른 곳 5개를 찾아요!</p>
           <div class="dif-grid">${stages
             .map(
               (s, i) => `<button class="dif-stage ${cleared.has(s.id) ? "cleared" : ""}" data-stage="${i}">
                 <span class="dif-stage-img"><img src="${s.thumb}" alt="" loading="lazy">
                   ${cleared.has(s.id) ? '<span class="dif-stage-done">✅ 클리어</span>' : ""}
                   <span class="dif-stage-no">${i + 1}</span></span>
                 <span class="dif-stage-name">${TYPE_EMOJI[s.train.type] || "🚆"} ${s.train.name}</span>
               </button>`
             )
             .join("")}</div>`
        : `<p class="dif-ask">그림을 불러오는 중… 🚂</p>`;
    }

    async function startStage(i) {
      current = i;
      list.hidden = true;
      play.hidden = false;
      back.hidden = false;
      root.querySelector(".dif-clear")?.remove();
      done = true; // no taps until the picture is in
      svgs.forEach((svg) => (svg.innerHTML = ""));
      loading.hidden = false;
      loading.textContent = "그림 준비 중… 🚂";
      const stage = stages[i];
      root.querySelector(".dif-name").textContent = `${TYPE_EMOJI[stage.train.type] || "🚆"} ${stage.train.name}`;
      root.querySelector(".dif-progress").textContent = `${i + 1} / ${stages.length}`;
      let pz = null;
      try {
        pz = await puzzleFor(stage, data);
      } catch (_) {}
      if (!alive || current !== i) return;
      if (!pz) {
        loading.textContent = "그림을 만들지 못했어요 😢";
        return;
      }
      loading.hidden = true;
      puzzle = pz;
      pw = pz.w;
      ph = pz.h;
      found = new Set();
      hintsLeft = MAX_HINTS;
      done = false;
      svgs.forEach((svg) => {
        svg.setAttribute("viewBox", `0 0 ${pw} ${ph}`);
        const href = svg.dataset.side === "L" ? pz.left : pz.right;
        svg.innerHTML = `<image href="${href}" x="0" y="0" width="${pw}" height="${ph}"/><g class="dif-marks"></g>`;
      });
      layout();
      updateStatus();
    }

    function updateStatus() {
      root.querySelector(".dif-dots").innerHTML = Array.from({ length: DIFFS_PER_PICTURE }, (_, i) => `<i class="${i < found.size ? "on" : ""}"></i>`).join("");
      root.querySelector(".dif-count").innerHTML = `찾은 개수 <b>${found.size} / ${DIFFS_PER_PICTURE}</b>`;
      const hint = root.querySelector(".dif-hint");
      hint.disabled = hintsLeft <= 0 || done;
      hint.textContent = hintsLeft > 0 ? `💡 힌트 ${hintsLeft}` : "💡 힌트 끝";
    }

    // picture coordinates of a tap, whatever size the picture is drawn at
    function toPicture(svg, e) {
      const p = svg.createSVGPoint();
      p.x = e.clientX;
      p.y = e.clientY;
      return p.matrixTransform(svg.getScreenCTM().inverse());
    }

    const near = (s, p) => Math.hypot(p.x - s.cx, p.y - s.cy) <= s.r * (s.reach || TAP_REACH);
    // marks are drawn at the same on-screen size whatever the picture's own size
    const unit = () => pw / W;

    function markFound(s) {
      svgs.forEach((svg) => {
        svg.querySelector(".dif-marks").appendChild(svgEl("circle", { cx: s.cx, cy: s.cy, r: s.r + 8 * unit(), class: "dif-found", style: `stroke-width:${8 * unit()}` }));
      });
    }

    function markMiss(svg, p) {
      const x = svgEl("text", { x: p.x, y: p.y + 16 * unit(), class: "dif-miss", "text-anchor": "middle", style: `font-size:${48 * unit()}px` });
      x.textContent = "❌";
      svg.querySelector(".dif-marks").appendChild(x);
      later(() => x.remove(), 700);
    }

    function onTap(e) {
      if (done || !puzzle) return;
      const now = performance.now();
      if (now - lastTap < 300) return; // a double tap counts once
      lastTap = now;
      const svg = e.currentTarget;
      const p = toPicture(svg, e);
      const hit = puzzle.spots.find((s) => !found.has(s.id) && near(s, p));
      if (hit) {
        found.add(hit.id);
        markFound(hit);
        sounds.found();
        if (found.size === puzzle.spots.length) {
          done = true;
          cleared.add(stages[current].id);
          saveCleared(cleared);
          later(showClear, 700);
        }
        updateStatus();
      } else if (!puzzle.spots.some((s) => found.has(s.id) && near(s, p))) {
        // tapping one already found is neither right nor wrong
        markMiss(svg, p);
        sounds.miss();
      }
    }

    function giveHint() {
      if (hintsLeft <= 0 || done || !puzzle) return;
      const left = puzzle.spots.filter((s) => !found.has(s.id));
      if (!left.length) return;
      const s = left[Math.floor(Math.random() * left.length)];
      hintsLeft--;
      sounds.hint();
      const glow = svgEl("circle", { cx: s.cx, cy: s.cy, r: s.r + 18 * unit(), class: "dif-glow", style: `stroke-width:${14 * unit()}` });
      svgs[1].querySelector(".dif-marks").appendChild(glow);
      later(() => glow.remove(), 2400);
      updateStatus();
    }

    // the next picture not cleared yet, after this one (wrapping around)
    function nextUncleared() {
      for (let k = 1; k <= stages.length; k++) {
        const i = (current + k) % stages.length;
        if (!cleared.has(stages[i].id)) return i;
      }
      return -1;
    }

    function showClear() {
      sounds.clear();
      const next = nextUncleared();
      const all = next < 0;
      const overlay = document.createElement("div");
      overlay.className = "dif-clear";
      overlay.innerHTML = `
        <div class="dif-clear-card">
          <div class="dif-clear-emoji">${all ? "🏆" : "🎉"}</div>
          <h2>${all ? "모든 그림을 다 찾았어요!" : "다 찾았어요!"}</h2>
          <div class="dif-stars">⭐⭐⭐⭐⭐</div>
          <div class="dif-clear-btns">
            ${all ? "" : `<button class="dif-btn go" data-act="next" data-next="${next}">다음 그림 ▶</button>`}
            <button class="dif-btn" data-act="list">🖼️ 그림 고르기</button>
          </div>
        </div>`;
      root.appendChild(overlay);
    }

    svgs.forEach((svg) => svg.addEventListener("pointerdown", onTap));
    root.addEventListener("click", (e) => {
      const st = e.target.closest("[data-stage]");
      if (st) {
        sounds.tap();
        return startStage(Number(st.dataset.stage));
      }
      const act = e.target.closest("[data-act]");
      if (!act) return;
      if (act.dataset.act === "hint") giveHint();
      if (act.dataset.act === "next") {
        sounds.tap();
        startStage(Number(act.dataset.next));
      }
      if (act.dataset.act === "list") {
        sounds.tap();
        showList();
      }
    });

    // side by side on a wide board, one above the other on a tall one; pictures keep their shape
    function layout() {
      if (play.hidden) return;
      const cs = getComputedStyle(board);
      const bw = board.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
      const bh = board.clientHeight - parseFloat(cs.paddingTop) - parseFloat(cs.paddingBottom);
      const gap = parseFloat(cs.columnGap || cs.gap) || 12;
      const across = Math.min((bw - gap) / 2, (bh * pw) / ph);
      const down = Math.min(bw, ((bh - gap) / 2) * (pw / ph));
      const sideBySide = across >= down;
      board.classList.toggle("stack", !sideBySide);
      const w = Math.max(0, sideBySide ? across : down);
      pics.forEach((p) => {
        p.style.width = Math.floor(w) + "px";
        p.style.height = Math.floor((w * ph) / pw) + "px";
      });
    }
    const ro = new ResizeObserver(layout);
    ro.observe(board);

    showList();
    (async () => {
      if (!data) data = await loadData();
      stages = await loadStages(data);
      if (alive) showList();
    })();

    window.DiffGame._debug = {
      state: () => ({ stage: current >= 0 && stages[current].id, found: [...found], done, hintsLeft, spots: puzzle && puzzle.spots, cleared: [...cleared] }),
      stages: () => stages,
      svgs,
    };

    return function unmount() {
      alive = false;
      ro.disconnect();
      timers.forEach(clearTimeout);
      timers.clear();
    };
  }

  // makePuzzle is exposed for the test page (tools/diff-test.html?all=1)
  window.DiffGame = { mount, makePuzzle, loadData, photoOf, KIND_LABEL };
})();
