# Which Pokémon Are You? 🔴⚪

A fun, lightweight personality quiz that reveals your inner Pokémon. Answer
8 quick questions and get matched to one of ten classic Pokémon, complete
with official artwork, type badges, a personality blurb, and a share button.

![Vanilla JS](https://img.shields.io/badge/vanilla-JS-f7df1e?style=flat-square&logo=javascript&logoColor=black)
![No build step](https://img.shields.io/badge/build-none-success?style=flat-square)

## ✨ Features

- **8-question personality quiz** with a weighted scoring system — answers
  award points across multiple Pokémon, so results feel nuanced rather than
  on-rails.
- **10 possible results**: Pikachu, Charizard, Bulbasaur, Squirtle, Eevee,
  Snorlax, Gengar, Jigglypuff, Mewtwo and Machamp.
- **Animated, responsive UI** — progress bar, pokéball logo, sprite reveal,
  type-coloured result card. Works on mobile and desktop.
- **Share your result** via the Web Share API (with a clipboard fallback).
- **Back button** so you can change an earlier answer.
- **Zero dependencies, no build step.** Just open the file.

## 🚀 Running it

It's a static site — no install required.

```bash
# Option 1: just open it
open index.html          # macOS
xdg-open index.html      # Linux

# Option 2: serve it locally (recommended so sprites load cleanly)
python3 -m http.server 8000
# then visit http://localhost:8000
```

> The Pokémon artwork is loaded on demand from the open-source
> [PokeAPI sprites](https://github.com/PokeAPI/sprites) repo, so an internet
> connection is needed to see the images. Everything else runs offline.

## 🗂️ Project structure

```
pokemon-quiz/
├── index.html   # markup & screens (start / quiz / result)
├── style.css    # all styling and animations
├── data.js      # quiz questions + Pokémon results (edit this to extend)
└── script.js    # quiz logic, scoring, sharing
```

## 🛠️ Customising

Everything content-related lives in **`data.js`**:

- **Add a result** — drop a new entry into `RESULTS` with its name, National
  Dex number (used to fetch the sprite), types and blurb.
- **Add a question** — push an object onto `QUESTIONS`. Each answer's
  `points` object maps result keys to the points that answer awards.

No changes to `script.js` are needed — it adapts to however many questions
and results you define.

## 📄 Licence / credits

Pokémon and all related names and sprites are © Nintendo / Game Freak /
The Pokémon Company. This is an unofficial, non-commercial fan project made
for fun and learning.
