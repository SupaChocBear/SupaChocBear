/* Quiz logic: render questions, tally points, reveal the winning Pokémon. */
(function () {
  "use strict";

  // ----- Type colours for the result badges -----
  const TYPE_COLORS = {
    Normal: "#9099a1", Fire: "#ff9d55", Water: "#5090d6", Electric: "#f4d23c",
    Grass: "#63bc5a", Ice: "#73cec0", Fighting: "#ce4069", Poison: "#ab6ac8",
    Ground: "#d97746", Flying: "#8fa8dd", Psychic: "#fa7179", Bug: "#91c12f",
    Rock: "#c5b78c", Ghost: "#5269ad", Dragon: "#0b6dc3", Dark: "#5a5366",
    Steel: "#5a8ea1", Fairy: "#ec8fe6",
  };

  // ----- Element references -----
  const screens = {
    start: document.getElementById("screen-start"),
    quiz: document.getElementById("screen-quiz"),
    result: document.getElementById("screen-result"),
  };
  const els = {
    startBtn: document.getElementById("start-btn"),
    backBtn: document.getElementById("back-btn"),
    retryBtn: document.getElementById("retry-btn"),
    shareBtn: document.getElementById("share-btn"),
    progressBar: document.getElementById("progress-bar"),
    progress: document.querySelector(".progress"),
    counter: document.getElementById("quiz-counter"),
    questionText: document.getElementById("question-text"),
    answers: document.getElementById("answers"),
    resultSprite: document.getElementById("result-sprite"),
    resultName: document.getElementById("result-name"),
    resultTypes: document.getElementById("result-types"),
    resultBlurb: document.getElementById("result-blurb"),
    resultMatches: document.getElementById("result-matches"),
    resultCard: document.getElementById("result-card"),
    shareStatus: document.getElementById("share-status"),
  };

  // ----- State -----
  let current = 0;             // index of the question being shown
  const choices = [];          // choices[i] = chosen answer index for question i

  // ----- Screen switching -----
  function show(name) {
    Object.entries(screens).forEach(([key, el]) => {
      const active = key === name;
      el.hidden = !active;
      el.classList.toggle("is-active", active);
    });
  }

  // ----- Render the current question -----
  function renderQuestion() {
    const total = QUESTIONS.length;
    const q = QUESTIONS[current];

    els.questionText.textContent = q.q;
    els.counter.textContent = `Question ${current + 1} of ${total}`;

    const pct = Math.round((current / total) * 100);
    els.progressBar.style.width = pct + "%";
    els.progress.setAttribute("aria-valuenow", String(pct));

    els.backBtn.disabled = current === 0;

    els.answers.innerHTML = "";
    q.answers.forEach((ans, i) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "answer";
      btn.textContent = ans.text;
      if (choices[current] === i) btn.classList.add("is-selected");
      btn.addEventListener("click", () => selectAnswer(i));
      els.answers.appendChild(btn);
    });
  }

  // ----- Handle an answer choice -----
  function selectAnswer(i) {
    choices[current] = i;

    // Briefly highlight the choice, then advance.
    Array.from(els.answers.children).forEach((b, idx) =>
      b.classList.toggle("is-selected", idx === i)
    );

    window.setTimeout(() => {
      if (current < QUESTIONS.length - 1) {
        current++;
        renderQuestion();
      } else {
        finish();
      }
    }, 220);
  }

  // ----- Tally points and find the winner -----
  function computeResult() {
    const scores = {};
    Object.keys(RESULTS).forEach((k) => (scores[k] = 0));

    choices.forEach((answerIdx, qIdx) => {
      const pts = QUESTIONS[qIdx].answers[answerIdx].points;
      Object.entries(pts).forEach(([key, val]) => {
        scores[key] = (scores[key] || 0) + val;
      });
    });

    // Rank results high → low. Ties broken by insertion order in RESULTS.
    const ranked = Object.keys(RESULTS).sort((a, b) => scores[b] - scores[a]);
    return { winner: ranked[0], runnersUp: ranked.slice(1, 3), scores };
  }

  // ----- Show the result screen -----
  function finish() {
    const { winner, runnersUp } = computeResult();
    const r = RESULTS[winner];

    els.progressBar.style.width = "100%";
    els.progress.setAttribute("aria-valuenow", "100");

    els.resultSprite.src = `${SPRITE_BASE}/${r.dex}.png`;
    els.resultSprite.alt = r.name;
    els.resultName.textContent = r.name;

    // Type badges
    els.resultTypes.innerHTML = "";
    r.types.forEach((t) => {
      const span = document.createElement("span");
      span.className = "type-badge";
      span.textContent = t;
      span.style.backgroundColor = TYPE_COLORS[t] || "#777";
      els.resultTypes.appendChild(span);
    });

    els.resultBlurb.textContent = r.blurb;

    // Tint the card with the primary type colour
    const tint = TYPE_COLORS[r.types[0]] || "#444";
    els.resultCard.style.setProperty("--tint", tint);

    // Runners-up
    els.resultMatches.innerHTML =
      "<span class='matches-label'>You also share traits with:</span> " +
      runnersUp.map((k) => RESULTS[k].name).join(" &amp; ");

    els.shareStatus.textContent = "";
    show("result");
  }

  // ----- Sharing -----
  async function share() {
    const { winner } = computeResult();
    const name = RESULTS[winner].name;
    const text = `I'm ${name}! Which Pokémon are you?`;
    const url = window.location.href;

    try {
      if (navigator.share) {
        await navigator.share({ title: "Which Pokémon Are You?", text, url });
        return;
      }
      await navigator.clipboard.writeText(`${text} ${url}`);
      els.shareStatus.textContent = "Result copied to clipboard!";
    } catch (err) {
      // User cancelled the share sheet, or clipboard was blocked — non-fatal.
      els.shareStatus.textContent = `You are ${name}!`;
    }
  }

  // ----- Reset for another go -----
  function restart() {
    current = 0;
    choices.length = 0;
    renderQuestion();
    show("quiz");
  }

  // ----- Wire up controls -----
  els.startBtn.addEventListener("click", () => {
    current = 0;
    choices.length = 0;
    renderQuestion();
    show("quiz");
  });
  els.backBtn.addEventListener("click", () => {
    if (current > 0) {
      current--;
      renderQuestion();
    }
  });
  els.retryBtn.addEventListener("click", restart);
  els.shareBtn.addEventListener("click", share);

  // Graceful fallback if a sprite fails to load.
  els.resultSprite.addEventListener("error", () => {
    els.resultSprite.style.display = "none";
  });
})();
