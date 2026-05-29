/*
 * Quiz data: results (the Pokémon you can get) and questions.
 *
 * Each answer awards points to one or more result keys. Whichever result
 * has the most points at the end wins. data is kept separate from logic so
 * the quiz is easy to extend — add a question or a result without touching
 * script.js.
 */

// Official artwork sprites served from the open-source PokeAPI sprites repo.
const SPRITE_BASE =
  "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork";

const RESULTS = {
  pikachu: {
    name: "Pikachu",
    dex: 25,
    types: ["Electric"],
    blurb:
      "Bright, energetic and impossible to ignore. You light up every room you walk into and your loyalty to your friends is electric. You'd rather stay your true self than change for anyone.",
  },
  charizard: {
    name: "Charizard",
    dex: 6,
    types: ["Fire", "Flying"],
    blurb:
      "Bold, ambitious and fiercely competitive. You aim high and you're not afraid of a challenge — in fact, you live for them. Underneath the fire, you're proud and protective of the people you care about.",
  },
  bulbasaur: {
    name: "Bulbasaur",
    dex: 1,
    types: ["Grass", "Poison"],
    blurb:
      "Calm, dependable and quietly nurturing. You're the friend everyone leans on. You grow steadily, think before you act, and there's hidden strength behind your easy-going nature.",
  },
  squirtle: {
    name: "Squirtle",
    dex: 7,
    types: ["Water"],
    blurb:
      "Cool, adaptable and quick-witted. You go with the flow but you've always got a clever plan up your sleeve. People are drawn to your laid-back confidence and sharp sense of humour.",
  },
  eevee: {
    name: "Eevee",
    dex: 133,
    types: ["Normal"],
    blurb:
      "Curious, adaptable and full of potential. You contain multitudes — your friends never quite know which side of you they'll get, and that's exactly what makes you special. The future is wide open.",
  },
  snorlax: {
    name: "Snorlax",
    dex: 143,
    types: ["Normal"],
    blurb:
      "Easy-going, unbothered and built for comfort. You know how to relax in a world that never stops, and you protect your peace. But cross your friends and you'll wake up fast — you're a gentle giant with serious power.",
  },
  gengar: {
    name: "Gengar",
    dex: 94,
    types: ["Ghost", "Poison"],
    blurb:
      "Mischievous, clever and a little bit chaotic. You've got a wicked sense of humour and love keeping people on their toes. Behind the pranks is a sharp mind that never misses a thing.",
  },
  jigglypuff: {
    name: "Jigglypuff",
    dex: 39,
    types: ["Normal", "Fairy"],
    blurb:
      "Creative, expressive and a born performer. You want to be seen and heard, and you put your whole heart into everything you do. You're sweet, but don't underestimate you — you can charm a whole crowd to sleep.",
  },
  mewtwo: {
    name: "Mewtwo",
    dex: 150,
    types: ["Psychic"],
    blurb:
      "Intense, independent and deeply thoughtful. You question everything and answer to no one. You feel things profoundly and value your solitude — but the right people earn a fierce, unshakeable loyalty.",
  },
  machamp: {
    name: "Machamp",
    dex: 68,
    types: ["Fighting"],
    blurb:
      "Driven, disciplined and all-in. When you commit to something you give it everything (all four arms, even). You're direct, dependable, and you'd happily carry your friends' loads as well as your own.",
  },
};

const QUESTIONS = [
  {
    q: "It's a free Saturday. What's the plan?",
    answers: [
      { text: "Out and about — somewhere new and exciting", points: { charizard: 2, pikachu: 1 } },
      { text: "A cosy day in, snacks and a screen", points: { snorlax: 2, squirtle: 1 } },
      { text: "Hanging with friends, the more the merrier", points: { pikachu: 2, jigglypuff: 1 } },
      { text: "Something creative or a project of my own", points: { mewtwo: 2, gengar: 1 } },
    ],
  },
  {
    q: "Pick a word that friends would use to describe you:",
    answers: [
      { text: "Loyal", points: { pikachu: 2, machamp: 1 } },
      { text: "Chill", points: { snorlax: 2, squirtle: 1 } },
      { text: "Mysterious", points: { mewtwo: 2, gengar: 1 } },
      { text: "Driven", points: { charizard: 2, machamp: 1 } },
    ],
  },
  {
    q: "How do you handle a tough challenge?",
    answers: [
      { text: "Charge straight at it head-on", points: { charizard: 2, machamp: 2 } },
      { text: "Step back and outsmart it", points: { mewtwo: 2, gengar: 1 } },
      { text: "Stay flexible and adapt as I go", points: { squirtle: 2, eevee: 1 } },
      { text: "Rally my friends to tackle it together", points: { pikachu: 2, bulbasaur: 1 } },
    ],
  },
  {
    q: "Choose an element that feels like you:",
    answers: [
      { text: "Fire — passion and energy", points: { charizard: 2 } },
      { text: "Water — calm and adaptable", points: { squirtle: 2 } },
      { text: "Grass — grounded and growing", points: { bulbasaur: 2 } },
      { text: "Electric — fast and lively", points: { pikachu: 2 } },
    ],
  },
  {
    q: "At a party, you're most likely…",
    answers: [
      { text: "The centre of attention", points: { jigglypuff: 2, pikachu: 1 } },
      { text: "Pulling a harmless prank", points: { gengar: 2 } },
      { text: "Deep in conversation in a quiet corner", points: { mewtwo: 2, bulbasaur: 1 } },
      { text: "Near the food, perfectly content", points: { snorlax: 2 } },
    ],
  },
  {
    q: "What's your ideal role in a team?",
    answers: [
      { text: "The leader setting the direction", points: { charizard: 2, mewtwo: 1 } },
      { text: "The reliable backbone", points: { machamp: 2, bulbasaur: 1 } },
      { text: "The one keeping spirits high", points: { pikachu: 2, jigglypuff: 1 } },
      { text: "The wildcard with surprising ideas", points: { eevee: 2, gengar: 1 } },
    ],
  },
  {
    q: "Which best describes how you grow and change?",
    answers: [
      { text: "I evolve constantly, always reinventing myself", points: { eevee: 2 } },
      { text: "I stay true to who I am, no matter what", points: { pikachu: 2 } },
      { text: "I level up steadily through hard work", points: { machamp: 2, bulbasaur: 1 } },
      { text: "I transform dramatically when it counts", points: { charizard: 2, gengar: 1 } },
    ],
  },
  {
    q: "Last one — what do you value most?",
    answers: [
      { text: "Friendship and belonging", points: { pikachu: 2, jigglypuff: 1 } },
      { text: "Freedom and independence", points: { mewtwo: 2, eevee: 1 } },
      { text: "Comfort and peace", points: { snorlax: 2, squirtle: 1 } },
      { text: "Achievement and respect", points: { charizard: 2, machamp: 1 } },
    ],
  },
];
