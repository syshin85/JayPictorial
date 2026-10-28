"use strict";

// 우주 퀴즈: 10 random questions from data/quiz.json (built from the encyclopedia), one point each.
// Same game as the train pictorial's quiz.js, on the night-sky theme.
// Exposes window.QuizGame.mount(container, { quiz }) → returns an unmount function.
(function () {
  const ROUND = 10;

  // ---------- sounds ----------
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
    tap: () => tone([600], { type: "triangle", dur: 0.06, vol: 0.1 }),
    right: () => {
      tone([660], { type: "triangle", dur: 0.12, vol: 0.14 });
      tone([880], { type: "triangle", dur: 0.18, vol: 0.14, delay: 0.1 });
    },
    wrong: () => tone([220], { type: "sine", dur: 0.25, vol: 0.12, glide: 0.8 }),
    fanfare: () => [523, 659, 784, 1047].forEach((f, i) => tone([f], { type: "triangle", dur: 0.22, vol: 0.13, delay: i * 0.13 })),
  };

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

  // A round: 10 questions, each with its choices shuffled and the answer index moved along.
  function newRound(bank) {
    return shuffle(bank)
      .slice(0, ROUND)
      .map((q) => {
        const order = shuffle(q.choices.map((_, i) => i));
        return { ...q, choices: order.map((i) => q.choices[i]), answer: order.indexOf(q.answer) };
      });
  }

  function mount(container, { quiz }) {
    const bank = quiz || [];
    let round = [];
    let index = 0;
    let score = 0;
    let picked = null; // index chosen for the current question, or null while waiting

    container.innerHTML = `
      <section class="quiz">
        <header class="topbar quiz-top">
          <button class="round-btn" data-go="#/" aria-label="처음으로">🏠</button>
          <h1>우주 퀴즈</h1>
          <div class="quiz-status"></div>
        </header>
        <div class="quiz-body"></div>
      </section>`;
    const root = container.querySelector(".quiz");
    const status = root.querySelector(".quiz-status");
    const body = root.querySelector(".quiz-body");

    function showStart() {
      status.innerHTML = "";
      body.innerHTML = `
        <div class="quiz-start">
          <div class="quiz-big-emoji" aria-hidden="true">❓🚀</div>
          <h2>우주 퀴즈</h2>
          <p>우주 도감에서 본 행성과 우주선, 얼마나 기억하나요?<br>문제는 모두 <b>${ROUND}개</b>예요!</p>
          <button class="quiz-btn quiz-go" data-act="start">시작! ▶</button>
        </div>`;
    }

    function showQuestion() {
      const q = round[index];
      picked = null;
      status.innerHTML = `<span class="quiz-pill">${index + 1} / ${ROUND}</span><span class="quiz-pill score">⭐ ${score}</span>`;
      const withImages = q.choices.some((c) => c.image);
      body.innerHTML = `
        <div class="quiz-q">
          ${q.image ? `<img class="quiz-photo" src="${esc(q.image)}" alt="">` : ""}
          <h2 class="quiz-question">${esc(q.question)}</h2>
        </div>
        <div class="quiz-choices ${withImages ? "pics" : ""}">
          ${q.choices
            .map(
              (c, i) => `<button class="quiz-choice" data-choice="${i}">
                ${c.image ? `<img src="${esc(c.image)}" alt="">` : ""}
                <span>${esc(c.text)}</span>
                <i class="quiz-mark" aria-hidden="true"></i>
              </button>`
            )
            .join("")}
        </div>
        <div class="quiz-feedback" hidden></div>`;
    }

    function answer(i) {
      if (picked !== null) return; // already answered: wait for 다음
      picked = i;
      const q = round[index];
      const right = i === q.answer;
      if (right) score++;
      const buttons = [...body.querySelectorAll(".quiz-choice")];
      buttons.forEach((b, j) => {
        b.disabled = true;
        if (j === q.answer) {
          b.classList.add("right");
          b.querySelector(".quiz-mark").textContent = "⭕";
        } else if (j === i) {
          b.classList.add("wrong");
          b.querySelector(".quiz-mark").textContent = "✖";
        } else {
          b.classList.add("dim");
        }
      });
      right ? sounds.right() : sounds.wrong();
      status.querySelector(".score").textContent = `⭐ ${score}`;
      const fb = body.querySelector(".quiz-feedback");
      fb.hidden = false;
      fb.innerHTML = `
        <p class="${right ? "yes" : "no"}">${right ? "딩동댕! 맞았어요 🎉" : "아쉬워요! 정답은 초록색이에요"}</p>
        <p class="quiz-explain">${esc(q.explain)}</p>
        <button class="quiz-btn quiz-next" data-act="next">${index + 1 < ROUND ? "다음 ▶" : "결과 보기 ▶"}</button>`;
    }

    function showEnd() {
      const [emoji, msg] =
        score === ROUND ? ["🏆", "완벽해요! 우주 박사님!"]
        : score >= 7 ? ["🌟", "정말 잘했어요!"]
        : score >= 4 ? ["👍", "잘했어요!"]
        : ["💪", "다시 해 볼까요?"];
      status.innerHTML = "";
      body.innerHTML = `
        <div class="quiz-end">
          <div class="quiz-big-emoji" aria-hidden="true">${emoji}</div>
          <h2>${msg}</h2>
          <p class="quiz-score"><b>${score}</b> / ${ROUND}점</p>
          <p class="quiz-stars" aria-hidden="true">${"⭐".repeat(score)}${"☆".repeat(ROUND - score)}</p>
          <div class="quiz-end-buttons">
            <button class="quiz-btn quiz-go" data-act="start">다시 하기 🔄</button>
            <button class="quiz-btn" data-go="#/">🏠 처음으로</button>
          </div>
        </div>`;
      if (score >= 4) sounds.fanfare();
    }

    function onClick(e) {
      const el = e.target.closest("[data-act], [data-choice]");
      if (!el || el.disabled) return;
      if (el.dataset.choice !== undefined) {
        answer(Number(el.dataset.choice));
      } else if (el.dataset.act === "start") {
        sounds.tap();
        round = newRound(bank);
        index = 0;
        score = 0;
        showQuestion();
      } else if (el.dataset.act === "next") {
        sounds.tap();
        index++;
        index < round.length ? showQuestion() : showEnd();
      }
    }

    root.addEventListener("click", onClick);
    showStart();

    return function unmount() {
      root.removeEventListener("click", onClick);
    };
  }

  window.QuizGame = { mount, _newRound: newRound };
})();
